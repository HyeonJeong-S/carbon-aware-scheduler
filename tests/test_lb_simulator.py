"""로드밸런서 ILP 라우팅 — 배정·무릎점·시뮬레이션의 핵심 성질을 합성 데이터로 검증한다."""

import numpy as np
import pandas as pd
import pytest

from load_balancer.framework import simulator as sim
from load_balancer.framework.config import REGIONS

FR = REGIONS.index("France")
KR = REGIONS.index("Korea")


class FakeCarbon:
    """CarbonSeries 와 같은 인터페이스. France 만 깨끗(10), 나머지는 500 g/kWh 로 고정."""

    def __init__(self, n_hours=48):
        self.n_hours = n_hours
        self.actual = {r: np.full(n_hours, 10.0 if r == "France" else 500.0) for r in REGIONS}
        self.pred = self.actual
        self.use_lstm_pred = True

    def at(self, region, t):
        return float(self.actual[region][min(int(t / 3600), self.n_hours - 1)])

    def forecast(self, t):
        return np.array([self.at(r, t) for r in REGIONS])

    def integrate_gco2(self, region, t0, t1, power_kw=1.0):
        return self.at(region, t0) * (t1 - t0) / 3600.0 * power_kw


@pytest.fixture
def latency():
    m = np.full((8, 8), 100.0)
    np.fill_diagonal(m, 0.0)
    m[FR, KR] = m[KR, FR] = 240.0
    return m


@pytest.fixture
def jobs():
    return pd.DataFrame({
        "job_name": [f"j_{i}" for i in range(6)],
        "submit_time": [0.0, 10.0, 20.0, 3600.0, 3610.0, 7200.0],
        "duration": [600.0] * 6,
        "region": ["Korea", "Korea", "Japan", "India", "Korea", "France"],
        "k": [1, 5, 3, 2, 4, 1],
    })


def _slot_inputs(latency, n_avail):
    carbon = FakeCarbon()
    m_hat = carbon.forecast(0)
    return m_hat, m_hat / m_hat.max(), latency / 244.0, np.full(8, n_avail), np.zeros((8, 8), bool)


def test_alpha_one_sends_everything_to_cleanest_region(latency):
    _, m_tilde, l_tilde, avail, blocked = _slot_inputs(latency, 10)
    batch = [{"origin_idx": KR}, {"origin_idx": KR}]
    picks = sim.assign_slot(batch, m_tilde, l_tilde, avail, sim.SimConfig(), blocked, alpha=1.0)
    assert picks == [FR, FR]


def test_alpha_zero_keeps_jobs_home(latency):
    _, m_tilde, l_tilde, avail, blocked = _slot_inputs(latency, 10)
    batch = [{"origin_idx": KR}]
    assert sim.assign_slot(batch, m_tilde, l_tilde, avail, sim.SimConfig(), blocked, alpha=0.0) == [KR]


def test_capacity_forces_ilp_path_and_spreads_load(latency):
    """가용량 1 인 리전에 job 3개 → greedy 지름길 대신 ILP 가 돌고, 드롭 없이 분산된다."""
    _, m_tilde, l_tilde, avail, blocked = _slot_inputs(latency, 1)
    batch = [{"origin_idx": KR}] * 3
    picks = sim.assign_slot(batch, m_tilde, l_tilde, avail, sim.SimConfig(), blocked, alpha=1.0)
    assert None not in picks
    assert len(set(picks)) == 3


def test_blocked_routes_are_never_used(latency):
    _, m_tilde, l_tilde, avail, blocked = _slot_inputs(latency, 10)
    blocked = blocked.copy()
    blocked[KR, FR] = True
    picks = sim.assign_slot([{"origin_idx": KR}], m_tilde, l_tilde, avail, sim.SimConfig(), blocked, alpha=1.0)
    assert picks[0] != FR


def test_knee_alpha_is_on_grid_and_returns_full_assignment(latency):
    m_hat, m_tilde, l_tilde, avail, blocked = _slot_inputs(latency, 10)
    batch = [{"origin_idx": KR}, {"origin_idx": FR}]
    alpha, picks = sim.knee_slot_alpha(batch, np.array([600.0, 600.0]), m_hat, m_tilde, l_tilde,
                                       latency, avail, sim.SimConfig(), blocked)
    assert alpha in sim.ALPHA_GRID
    assert len(picks) == 2 and None not in picks


def test_auto_capacity_scales_baseline_peak(jobs):
    # Korea 에서 t=0,10 두 job 이 겹침 → 피크 2 × 1.2 = 2.4 → ceil 3, 최소 4
    assert sim.auto_capacity(jobs, cap_factor=1.2) == 4
    assert sim.auto_capacity(jobs, cap_factor=5.0) == 10


def test_run_sim_baseline_keeps_home_and_accounts_carbon(jobs, latency):
    out = sim.run_sim(jobs, FakeCarbon(), latency, sim.SimConfig(), mode="baseline")
    m = out["metrics"]
    assert m["home_ratio"] == 1.0 and m["dropped"] == 0 and m["n_jobs"] == len(jobs)
    # 600초 × 1kW: France 1개(10g) + 나머지 5개(500g) → (10 + 5×500) × 600/3600 g (metrics 는 kg 소수 2자리)
    assert m["total_carbon_kg"] == pytest.approx((10 + 5 * 500) * 600 / 3600 / 1000, abs=0.005)
    assert np.trace(np.array(out["routing_matrix"])) == len(jobs)


def test_run_sim_ilp_alpha_one_reduces_carbon_at_latency_cost(jobs, latency):
    base = sim.run_sim(jobs, FakeCarbon(), latency, sim.SimConfig(), mode="baseline")["metrics"]
    ilp = sim.run_sim(jobs, FakeCarbon(), latency, sim.SimConfig(alpha=1.0, capacity=10), mode="ilp")["metrics"]
    assert ilp["total_carbon_kg"] < base["total_carbon_kg"]
    assert ilp["avg_latency_ms"] > base["avg_latency_ms"]
    assert ilp["region_load"]["France"] == len(jobs)
    assert ilp["dropped"] == 0


def test_run_sim_adaptive_alpha_records_slot_alpha(jobs, latency):
    out = sim.run_sim(jobs, FakeCarbon(), latency, sim.SimConfig(adaptive_alpha=True, capacity=10), mode="ilp")
    slots = out["slot_series"]
    assert out["metrics"]["alpha_mode"] == "auto"
    assert slots.alpha.dropna().between(0, 1).all()
    assert slots.alpha.notna().sum() == jobs.submit_time.floordiv(3600).nunique()
