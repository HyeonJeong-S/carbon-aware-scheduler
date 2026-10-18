"""CASPER 리전 동시 실행 상한(선택 사항, 10-18) — 작은 합성 사례로."""
import numpy as np

from scheduler import joint, prior_casper

REG = ["A", "B"]
LAT = [[0.0, 100.0], [100.0, 0.0]]


def _instance(seed=0, n_h=60, per_h=4):
    rng = np.random.default_rng(seed)
    jobs, k = [], 0
    for h in range(n_h):
        for _ in range(rng.integers(0, per_h + 1)):
            s = h + float(rng.uniform(0, 1))
            d = float(rng.uniform(0.2, 1.5))
            jobs.append(dict(id=f"j{k}", submit_time=s, duration=d, deadline=s + d + 1.0, region=REG[k % 2], k=1))
            k += 1
    actual = {"A": np.full(n_h + 5, 400.0), "B": np.full(n_h + 5, 100.0)}   # B 가 늘 깨끗 — 상한 없으면 B 로 몰린다
    return jobs, actual


def _peaks(dec, jobs):
    by = {j["id"]: j for j in jobs}
    recs = {k: dict(region=r, scheduled_start=s, duration=by[k]["duration"]) for k, (r, s) in dec.items()}
    return joint.peak_ends_first(recs, REG)


def test_capped_casper_never_exceeds_cap_when_feasible():
    jobs, actual = _instance()
    dec0 = prior_casper.run_casper(jobs, actual, LAT, prior_casper.ALPHA_CAP, regions=REG, verbose_every=0)
    assert _peaks(dec0, jobs)["B"] > 4, "상한 없는 CASPER 가 B 에 몰려야 시험이 의미 있다"
    info = {}
    dec = prior_casper.run_casper(jobs, actual, LAT, prior_casper.ALPHA_CAP, regions=REG, verbose_every=0,
                                  cap=4, info=info)
    assert len(dec) == len(jobs) and info["n_slack"] == 0
    assert max(_peaks(dec, jobs).values()) <= 4
    assert all(s == j["submit_time"] for j in jobs for s in [dec[j["id"]][1]])   # 시간 이동 없음


def test_capped_casper_slack_goes_home():
    jobs = [dict(id=f"j{i}", submit_time=0.1 * (i + 1), duration=3.0, deadline=10.0, region="A", k=1) for i in range(5)]
    actual = {"A": np.full(10, 400.0), "B": np.full(10, 100.0)}
    info = {}
    dec = prior_casper.run_casper(jobs, actual, LAT, prior_casper.ALPHA_CAP, regions=REG, verbose_every=0,
                                  cap=2, info=info)
    assert info["n_slack"] == 1 and info["slack_hours"] == 1
    assert sorted(r for r, _ in dec.values()) == ["A", "A", "A", "B", "B"]
