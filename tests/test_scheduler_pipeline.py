"""data_loader → simulator → metrics 파이프라인을 작은 합성 데이터로 끝까지 돌린다."""

import math

import pytest

from scheduler import data_loader, metrics, simulator, timeshift
from scheduler.config import FORECAST_HORIZON, MODES


def test_load_jobs_csv_converts_seconds_to_hours_and_regions(jobs_csv):
    jobs = data_loader.load_jobs_csv(jobs_csv)
    assert [j["id"] for j in jobs] == ["j_000001", "j_000002", "j_000003"]
    j = jobs[0]
    assert j["submit_time"] == 1.0 and j["duration"] == 0.5 and j["L_max"] == 12.0
    assert j["region"] == "KR"                     # Korea → 표준 코드
    assert j["carbon_region"] is None
    assert j["deadline"] == pytest.approx(1.0 + 12.0 + 0.5)


def test_load_jobs_with_assignment_attaches_carbon_region(jobs_csv, tmp_path):
    assign = tmp_path / "assign_alpha_auto.csv"
    assign.write_text("job_name,origin,assigned\nj_000001,Korea,France\nj_000003,France,France\n")
    jobs = data_loader.load_jobs_with_assignment(jobs_csv, assign)
    by_id = {j["id"]: j for j in jobs}
    assert by_id["j_000001"]["carbon_region"] == "FR"
    assert by_id["j_000002"]["carbon_region"] is None      # 배정 없는 job 은 그대로
    assert by_id["j_000003"]["carbon_region"] == "FR"


@pytest.fixture
def perfect_forecast(monkeypatch):
    def _window(carbon_series, t_now, horizon=FORECAST_HORIZON):
        h = math.floor(t_now)
        return {r: s[h:h + horizon] for r, s in carbon_series.items()}
    monkeypatch.setattr(timeshift, "get_forecast_window", _window)


def test_simulation_runs_all_modes_and_never_violates_slo(jobs_csv, perfect_forecast):
    jobs = data_loader.load_jobs_csv(jobs_csv)
    for j in jobs:
        j["carbon_region"] = "FR"
    hours = int(max(j["deadline"] for j in jobs)) + 48
    series = {"KR": [400.0] * hours, "US-CAL-CISO": [200.0] * hours,
              "FR": [(20.0 if h % 24 == 4 else 80.0) for h in range(hours)]}

    results = simulator.run_all_modes(jobs, series)
    assert set(results) == set(MODES)
    for mode, rows in results.items():
        assert len(rows) == len(jobs), mode
        assert all(r["slo_satisfied"] for r in rows), mode
        assert all(r["finish_time"] == pytest.approx(r["scheduled_start"] + r["duration"]) for r in rows)

    comp = metrics.compare_modes(results)
    assert comp["carbon_lb_immediate"]["total_carbon"] <= comp["simple_lb_immediate"]["total_carbon"]
    assert comp["carbon_lb_timeshift"]["total_carbon"] <= comp["carbon_lb_immediate"]["total_carbon"]
    assert comp["carbon_lb_timeshift"]["slo_violation_rate"] == 0.0


def test_metrics_aggregate():
    rows = [{"carbon_emitted": 10.0, "delay": 2.0, "slo_satisfied": True},
            {"carbon_emitted": 30.0, "delay": 0.0, "slo_satisfied": False}]
    m = metrics.aggregate(rows)
    assert m == {"n_jobs": 2, "total_carbon": 40.0, "avg_delay": 1.0, "slo_violation_rate": 0.5}
    assert metrics.aggregate([]) == {"n_jobs": 0, "total_carbon": 0, "avg_delay": 0.0, "slo_violation_rate": 0.0}
