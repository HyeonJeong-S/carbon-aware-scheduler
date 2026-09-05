"""time-shift 알고리즘 — 설계 문서(scheduler/README.md 3절)의 성질을 그대로 검증한다."""

import math

import pytest

from scheduler import timeshift
from scheduler.config import FORECAST_HORIZON
from tests.conftest import make_job


# ── α ───────────────────────────────────────────────────────
@pytest.mark.parametrize("k, alpha", [(5, 0.2), (4, 0.4), (3, 0.6), (2, 0.8), (1, 1.0)])
def test_alpha_table(k, alpha):
    assert timeshift.compute_alpha(k) == pytest.approx(alpha)


# ── mean_carbon: 시각 → 인덱스는 floor, 길이는 ceil ─────────────
def test_mean_carbon_uses_floor_for_start_and_ceil_for_duration():
    series = [100.0, 200.0, 300.0, 400.0]
    # 1.9h 시작, 1.2h 실행 → 인덱스 1 부터 2칸(1,2) 평균
    assert timeshift.mean_carbon(series, 1.9, 1.2, len(series)) == pytest.approx(250.0)


def test_mean_carbon_clamps_past_series_end():
    series = [100.0, 200.0]
    assert timeshift.mean_carbon(series, 5.0, 1.0, len(series)) == 200.0


# ── compute_time_shift ─────────────────────────────────────────
def test_relaxed_job_moves_to_cleanest_slot(valley_forecast):
    job = make_job(k=1, L_max=12.0, duration=1.0)
    start = timeshift.compute_time_shift(job, valley_forecast, t_now=0.0)
    assert start == 6.0


def test_urgent_job_runs_immediately(valley_forecast):
    job = make_job(k=5, L_max=1 / 3600, duration=0.01)   # 1초 여유
    assert timeshift.compute_time_shift(job, valley_forecast, t_now=0.0) == job["submit_time"]


def test_no_slack_falls_back_to_immediate(valley_forecast):
    job = make_job(k=1, L_max=0.0, duration=1.0)
    assert timeshift.compute_time_shift(job, valley_forecast, t_now=0.0) == job["submit_time"]


def test_flat_forecast_never_delays(flat_forecast):
    """탄소 차이가 없으면 지연 비용만 남아 즉시 실행이 최적."""
    job = make_job(k=1, L_max=20.0, duration=1.0)
    assert timeshift.compute_time_shift(job, flat_forecast, t_now=0.0) == 0.0


def test_start_always_within_deadline(valley_forecast, rng):
    """어떤 job 이든 scheduled_start + duration <= deadline (SLO 위반 0 의 구조적 근거)."""
    for _ in range(300):
        job = make_job(k=int(rng.integers(1, 6)), submit_time=float(rng.uniform(0, 5)),
                       duration=float(rng.uniform(0.01, 6)), L_max=float(rng.uniform(0, 30)))
        t_now = math.floor(job["submit_time"])
        start = timeshift.compute_time_shift(job, valley_forecast, t_now=t_now)
        assert job["submit_time"] <= start
        assert start + job["duration"] <= job["deadline"] + 1e-9


def test_search_is_capped_by_forecast_horizon(rng):
    """L_max 가 24h 를 넘어도 예측 범위(24h) 밖 슬롯은 후보가 아니다."""
    fw = {"KR": [500.0] * 24}
    job = make_job(k=1, L_max=100.0, duration=1.0)
    start = timeshift.compute_time_shift(job, fw, t_now=0.0)
    assert start <= FORECAST_HORIZON


def test_fractional_submit_time_searches_from_next_whole_hour(valley_forecast):
    job = make_job(k=1, submit_time=0.5, L_max=12.0, duration=1.0)
    start = timeshift.compute_time_shift(job, valley_forecast, t_now=0.0)
    assert start == 6.0
    assert start >= job["submit_time"]


# ── schedule_job (비교군 3종) ────────────────────────────────────
@pytest.fixture
def perfect_forecast(monkeypatch):
    """시뮬레이션에서 예측 = 실측 (perfect forecast) 로 고정해 외부 데이터 의존을 끊는다."""
    def _window(carbon_series, t_now, horizon=FORECAST_HORIZON):
        h = math.floor(t_now)
        return {r: s[h:h + horizon] for r, s in carbon_series.items()}
    monkeypatch.setattr(timeshift, "get_forecast_window", _window)


def test_modes_pick_region_from_load_balancer_data(perfect_forecast):
    series = {"KR": [500.0] * 48, "FR": [10.0] * 48}
    job = make_job(k=5, region="KR", carbon_region="FR", L_max=0.0, duration=1.0)

    simple = timeshift.schedule_job(job, series, "simple_lb_immediate")
    carbon = timeshift.schedule_job(job, series, "carbon_lb_immediate")
    assert simple["region"] == "KR" and carbon["region"] == "FR"
    assert carbon["carbon_emitted"] < simple["carbon_emitted"]


def test_timeshift_mode_saves_carbon_and_keeps_slo(perfect_forecast):
    series = {"KR": [500.0] * 6 + [50.0] + [500.0] * 41}
    job = make_job(k=1, region="KR", L_max=12.0, duration=1.0)
    imm = timeshift.schedule_job(job, series, "carbon_lb_immediate")
    shifted = timeshift.schedule_job(job, series, "carbon_lb_timeshift")
    assert shifted["scheduled_start"] == 6.0
    assert shifted["delay"] == 6.0
    assert shifted["carbon_emitted"] == pytest.approx(50.0)
    assert shifted["carbon_emitted"] < imm["carbon_emitted"]
    assert shifted["slo_satisfied"]


def test_unknown_mode_raises(perfect_forecast):
    with pytest.raises(ValueError):
        timeshift.schedule_job(make_job(), {"KR": [1.0] * 48}, "nope")
