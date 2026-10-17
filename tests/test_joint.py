# -*- coding: utf-8 -*-
"""결합 롤링 스케줄러(scheduler.joint) 단위 시험 — 데이터 파일 없이 작은 합성 사례로."""
import numpy as np
import pytest

from scheduler import capacity, joint

REG = ["A", "B"]
LAT = {"A": {"A": 0.0, "B": 100.0}, "B": {"A": 100.0, "B": 0.0}}
N_H = 96


def _oracle(actual, horizon=24):
    out = {}
    for r, arr in actual.items():
        n = len(arr)
        p = np.zeros((n, horizon))
        for h in range(n):
            idx = np.clip(np.arange(h + 1, h + 1 + horizon), 0, n - 1)
            p[h] = arr[idx]
        out[r] = p
    return out


def _series():
    h = np.arange(N_H)
    a = 300 + 200 * np.sin(2 * np.pi * (h - 6) / 24)      # A: 낮에 낮음(태양광꼴), 최저 h≡18
    b = np.full(N_H, 100.0)                                # B: 항상 낮고 평탄
    actual = {"A": a.astype(float), "B": b}
    return actual, _oracle(actual)


def _job(i, s, d, L, origin="A", k=1):
    return dict(id=f"j{i}", submit_time=float(s), duration=float(d), k=k, L_max=float(L),
                region=origin, carbon_region=None, deadline=float(s + L + d))


def _run(jobs, **kw):
    actual, pred = _series()
    base = dict(cap=2, regions=REG, latency_ms=LAT, rho=0, n_hours=N_H - 30, alpha="knee")
    base.update(kw)
    return joint.run_joint(jobs, actual, pred, **base)


def test_deadline_guarantee_and_all_placed():
    jobs = [_job(i, 10 + i * 0.3, 1.5, 6) for i in range(12)]      # 2자리에 12건 — 마감 보장이 강제 편입을 만든다
    out, st = _run(jobs, cap=2)
    assert st["n"] == 12 and st["unplaced"] == 0
    assert st["slo_violations"] == 0
    assert all(v["slo_satisfied"] for v in out.values())


def test_nondeferrable_runs_immediately():
    jobs = [_job(0, 10.25, 0.01, 0.002, k=5), _job(1, 10.5, 0.01, 0.003, k=5)]   # 정수 슬롯 후보가 제출 슬롯뿐
    out, st = _run(jobs)
    assert st["immediate"] == 2
    for v in out.values():
        assert v["immediate"] and abs(v["delay"]) < 1e-9


def test_alpha1_unbounded_goes_to_cleanest_region():
    jobs = [_job(i, 10 + i, 1.0, 20) for i in range(5)]
    out, st = _run(jobs, cap=10 ** 6, alpha=1.0)
    assert st["capacity_violations"] == 0
    assert all(v["region"] == "B" for v in out.values())            # B 가 항상 100 < A 최저 100? A 최저=100 동률 가능


def test_home_region_keeps_origin():
    jobs = [_job(i, 10 + i, 1.0, 20, origin="A") for i in range(4)]
    out, st = _run(jobs, home_region=True)
    assert all(v["region"] == "A" for v in out.values())
    assert st["avg_latency_ms"] == 0.0


def test_spatial_only_has_zero_delay():
    jobs = [_job(i, 10 + i * 0.5, 1.0, 20) for i in range(4)]
    out, st = _run(jobs, spatial_only=True, cap=10 ** 6)
    assert all(abs(v["delay"]) < 1e-9 for v in out.values())


def test_no_overflow_when_feasible_and_peak_convention():
    jobs = [_job(i, 10 + i * 0.1, 2.0, 30) for i in range(6)]      # 창이 넓어 2자리로 다 소화 가능
    out, st = _run(jobs, cap=2, rho=0)
    assert st["capacity_violations"] == 0
    assert max(st["peak_by_region"].values()) <= 2
    # 위반 정의와 같은 규약으로 센 피크는 상한을 넘지 않는다
    ocf, oci, ocn = capacity._over_cap_admissions(out, REG, 2)
    assert ocf + oci + ocn == 0


def test_reservation_leaves_room_in_future_slots():
    # 예약 ρ 는 "이전 슬롯에 시작해 아직 도는 미룰 수 있는 작업" 을 cap−ρ 로 묶는다.
    # 1시간짜리는 미래 슬롯을 안 덮으므로 2.5시간짜리로 시험한다.
    jobs = [_job(i, 10 + i * 0.1, 2.5, 40) for i in range(6)]
    out, st = _run(jobs, cap=2, rho=1)
    assert st["forced_admissions"] == 0, "창이 넓어 강제 편입 없이 다 들어가야 한다"
    for tau in range(10, 60):
        for r in REG:
            carried = sum(1 for v in out.values()
                          if v["region"] == r and not v["immediate"]
                          and v["scheduled_start"] < tau <= v["scheduled_start"] + v["duration"] - 1e-9
                          and int(v["scheduled_start"]) < tau)
            assert carried <= 2 - 1, (tau, r, carried)


def test_knee_logs_alpha_from_grid():
    jobs = [_job(i, 10 + i, 1.0, 20) for i in range(6)]
    out, st = _run(jobs, alpha="knee")
    assert st["alpha_log"], "슬롯별 α 기록이 비어 있다"
    assert all(a in joint.ALPHA_GRID for _, a, _ in st["alpha_log"])
    assert 0.0 <= st["alpha_mean"] <= 1.0


def test_sn24_shape_and_lag():
    actual, _ = _series()
    p = joint.sn24_pred24(actual, 24)
    assert p["A"].shape == (N_H, 24)
    h = 40
    assert p["A"][h][0] == actual["A"][h + 1 - 24]
    assert p["A"][h][5] == actual["A"][h + 6 - 24]


# ── 2026-10-16 감사 반영 시험 ──────────────────────────────────────────────
def test_tiny_nondeferrable_jobs_do_not_saturate_a_slot():
    # 코드 감사 C3: 1초짜리 미룰 수 없는 작업 4개가 같은 슬롯에 와도 연속 피크는 1 — 전부 A 에 남아야 한다
    jobs = [_job(i, 10.1 + 0.1 * i, 1 / 3600, 0.0005, origin="A", k=5) for i in range(4)]
    out, st = _run(jobs, cap=2, alpha=0.0)      # α=0: 지연만 보므로 용량이 막지 않는 한 홈(A)에 남는다
    assert all(v["region"] == "A" for v in out.values()), [v["region"] for v in out.values()]
    assert st["capacity_violations"] == 0


def test_per_region_cap_scoring():
    # 코드 감사 C2: 리전별 상한 — A 는 1, B 는 5. A 에 2h 작업 3개를 억지로 넣으면 A 의 위반이 잡혀야 한다
    jobs = [_job(i, 10.0, 2.0, 0.0001, origin="A", k=5) for i in range(3)]   # 미룰 수 없음, 홈 고정
    out, st = _run(jobs, cap={"A": 1, "B": 5}, home_region=True)
    assert st["capacity_violations"] == 3
    assert st["hours_over_by_region"]["A"] > 1.9
    assert st["scored_cap"] == {"A": 1, "B": 5}


def test_degenerate_knee_falls_back_to_alpha_1():
    # 통계 감사 E3: 홈 고정이면 지연 축이 전부 0 → α 는 잡음이 아니라 1 이어야 한다
    jobs = [_job(i, 10 + i, 1.0, 20, origin="A") for i in range(6)]
    out, st = _run(jobs, home_region=True, alpha="knee")
    assert all(a == 1.0 for _, a, _ in st["alpha_log"])


def test_decoupled_fixes_region_after_arrival():
    jobs = [_job(i, 10 + i, 2.0, 30, origin="A") for i in range(6)]
    out, st = _run(jobs, mode="decoupled", cap=10 ** 6, alpha=1.0)
    assert st["mode"] == "decoupled" and st["n"] == 6 and st["slo_violations"] == 0


def test_greedy_mode_runs_and_respects_deadlines():
    jobs = [_job(i, 10 + i * 0.3, 1.5, 6) for i in range(12)]
    out, st = _run(jobs, mode="greedy", cap=2)
    assert st["n"] == 12 and st["slo_violations"] == 0 and st["mode"] == "greedy"


def test_window_scoring_counts_only_jobs_after_score_from():
    jobs = [_job(i, 5 + i, 1.0, 20) for i in range(10)]
    out, st = _run(jobs, score_from=10.0, cap=10 ** 6)
    assert st["n"] == 5 and st["n_all"] == 10
