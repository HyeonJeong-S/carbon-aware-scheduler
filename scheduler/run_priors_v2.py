# -*- coding: utf-8 -*-
"""v2 선행 정책 재현 — t=0 부터 전 작업을 돌리고 day 8+ 제출 작업만 채점. 물리 상한(기본 17)으로 센다.

v1 표 4 와 다른 점(정리.txt [80], 2026-10-16 감사):
  · 시뮬레이션 전 구간, 채점 창 day 8+ (동시 실행은 전체 스케줄로)
  · 채점 상한 = 물리 설비 cap_r. 12 로도 같이 세어 둔다(연속성)
  · "Sukprasert temporal" 두 행: 홈 고정(원문 그대로) / CAST 공간 배정 위(v1 의 행)
  · Sukprasert 시작 규약 정정(제출 전 시작 없음)
  · 각 행에 필요 용량(피크), 시간가중 p99.9 동시 실행, 초과시간 ≤0.1% 가 되는 최소 상한, 초과 시간, 마감 위반

    ./.venv/bin/python -m scheduler.run_priors_v2 --policies baseline,suk_home,suk_lb,suk_st,cics,casper
    ./.venv/bin/python -m scheduler.run_priors_v2 --policies caspian --caspian-omega1 1.0 --caspian-fractional
"""
import argparse
import csv
import gzip
import json
import math
import os
import time

import numpy as np

from interface import carbon_2025
from interface.regions import REGIONS
from load_balancer.framework.config import JOBS_CSV, load_latency_matrix
from . import capacity, data_loader, joint, prior_harness as H

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "data", "v2", "priors")
SCORE_FROM = 168


def _occupancy_quantile(out, regions, q, t_lo, t_hi):
    """시간가중 동시 실행 분위수(리전별) — 폭 0 순간은 기여 0."""
    res = {}
    for r in regions:
        ev = []
        for v in out.values():
            if v["region"] == r:
                ev.append((v["scheduled_start"], 1)); ev.append((v["scheduled_start"] + v["duration"], -1))
        ev.sort()
        cur, prev, segs = 0, t_lo, []
        for t, d in ev:
            if t > prev and t > t_lo:
                segs.append((cur, min(t, t_hi) - max(prev, t_lo)))
            cur += d; prev = t
            if prev >= t_hi:
                break
        segs = [(c, w) for c, w in segs if w > 0]
        segs.sort()
        tot = sum(w for _, w in segs); acc = 0; val = 0
        for c, w in segs:
            acc += w
            if acc >= q * tot:
                val = c; break
        res[r] = val
    return res


def _min_cap_for(out, regions, frac, t_lo, t_hi):
    """초과 시간 비율이 frac 이하가 되는 최소 상한(전 리전 최악)."""
    best = 0
    for r in regions:
        for c in range(1, 2000):
            led = capacity.CapacityLedger([r], c)
            for v in out.values():
                if v["region"] == r:
                    led.reserve(r, v["scheduled_start"], v["duration"])
            if led.hours_over(r) <= frac * (t_hi - t_lo):
                best = max(best, c); break
    return best


def score_policy(decisions, jobs, W, lat_d, cap_d, score_from, label, t_hi):
    by_id = {j["id"]: j for j in jobs}
    out = {}
    for jid, (r, start) in decisions.items():
        j = by_id[jid]
        out[jid] = dict(job_id=jid, k=j["k"], region=r, origin=j["region"], submit_time=j["submit_time"],
                        duration=j["duration"], scheduled_start=start, delay=start - j["submit_time"],
                        carbon_emitted=W.actual_mean(r, start, j["duration"]) * j["duration"],
                        latency_ms=lat_d[j["region"]][r],
                        slo_satisfied=(start + j["duration"]) <= j["deadline"] + 1e-9, forced=False, immediate=False)
    st = joint.summarize(out, REGIONS, cap_d, score_from=score_from)
    win = {k: v for k, v in out.items() if v["submit_time"] >= score_from}
    st["required_capacity"] = max(st["peak_by_region"].values())
    st["p999_by_region"] = _occupancy_quantile(out, REGIONS, 0.999, score_from, t_hi)
    st["p999"] = max(st["p999_by_region"].values())
    st["min_cap_0.1pct_hours_over"] = _min_cap_for(out, REGIONS, 0.001, score_from, t_hi)
    st["label"] = label
    return st, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policies", default="baseline,suk_home,suk_lb,suk_st,cics,casper")
    ap.add_argument("--cap", type=int, default=17)
    ap.add_argument("--score-from", type=int, default=SCORE_FROM)
    ap.add_argument("--caspian-omega1", type=float, default=None)
    ap.add_argument("--caspian-fractional", action="store_true")
    ap.add_argument("--assign", default=str(H.ASSIGN_CSV))
    ap.add_argument("--tag-suffix", default="", help="출력 파일 이름 뒤에 붙일 꼬리(예: _v2knee — 다른 배정으로 돌릴 때 기존 결과를 덮지 않기 위해)")
    args = ap.parse_args(argv)

    jobs = data_loader.load_jobs_with_assignment(JOBS_CSV, args.assign)
    data = carbon_2025.load_2025()
    actual, pred24 = data["actual"], data["pred24"]
    W = capacity._Windows(actual, pred24)
    latency = load_latency_matrix()
    lat_d = joint.latency_dict(REGIONS)
    cap_d = {r: args.cap for r in REGIONS}
    cap12 = {r: 12 for r in REGIONS}
    t_hi = len(next(iter(actual.values())))
    print(f"시뮬 {len(jobs):,}건, 채점 day {args.score_from // 24}+, 상한 {args.cap}", flush=True)

    base_dec = H.baseline_decisions(jobs)
    s16, _ = score_policy(base_dec, jobs, W, lat_d, cap_d, args.score_from, "baseline", t_hi)
    base_kg = s16["total_carbon_kg"]

    def report(name, s):
        print(f"  {name:10s} {s['total_carbon_kg']:10,.1f} kg  {100*(1-s['total_carbon_kg']/base_kg):6.2f}%  "
              f"위반@{args.cap} {s['capacity_violations']:7,}  초과 {sum(s['hours_over_by_region'].values()):7.1f}h  "
              f"필요용량 {s['required_capacity']:4d}  p99.9 {s['p999']:3d}  최소상한(0.1%) {s['min_cap_0.1pct_hours_over']:3d}  "
              f"마감위반 {s['slo_violations']:6,}  지연 {s['avg_latency_ms']:6.1f} ms", flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    for name in args.policies.split(","):
        t0 = time.perf_counter()
        if name == "baseline":
            dec = base_dec
        elif name == "suk_home":
            from . import prior_sukprasert as S; dec = S.temporal_home_decisions(jobs, actual)
        elif name == "suk_lb":
            from . import prior_sukprasert as S; dec = S.temporal_decisions(jobs, actual)
        elif name == "suk_st":
            from . import prior_sukprasert as S; dec = S.spatiotemporal_decisions(jobs, actual)
        elif name == "cics":
            from . import prior_cics as C; _, dec = C.run(lam_ratio=0.0, delta_max=1.0, verbose=False, jobs=jobs, actual=actual)
        elif name == "casper":
            from . import prior_casper as P; dec = P.run_casper(jobs, actual, latency, P.ALPHA_CAP, policy="carbon")
        elif name == "caspian":
            from . import prior_caspian as Q
            assert args.caspian_omega1 is not None
            dec, _ = Q.run_caspian(jobs, W, omega1=args.caspian_omega1, omega2=1.0, omega3=1.0,
                                   cap=args.cap, fractional=args.caspian_fractional, verbose=True)
        else:
            raise SystemExit(f"모르는 정책: {name}")
        s, out = score_policy(dec, jobs, W, lat_d, cap_d, args.score_from, name, t_hi)
        s12 = joint.summarize(out, REGIONS, cap12, score_from=args.score_from)
        s["violations_at_cap12"] = s12["capacity_violations"]
        s["wall_s"] = time.perf_counter() - t0; s["baseline_kg"] = base_kg
        s["savings_pct"] = 100 * (1 - s["total_carbon_kg"] / base_kg)
        if name == "caspian":
            s["omega1"] = args.caspian_omega1; s["fractional"] = args.caspian_fractional
        tag = (name if name != "caspian" else f"caspian_w{args.caspian_omega1}{'_frac' if args.caspian_fractional else ''}") + args.tag_suffix
        with open(os.path.join(OUT_DIR, f"{tag}.json"), "w") as f:
            json.dump(dict(name=tag, at_cap=s), f, ensure_ascii=False, indent=1, default=float)
        with gzip.open(os.path.join(OUT_DIR, f"{tag}.decisions.csv.gz"), "wt", newline="") as f:
            w = csv.writer(f); w.writerow(["job_id", "region", "start"])
            for jid, (r, st_) in dec.items():
                w.writerow([jid, r, st_])
        report(name, s)


if __name__ == "__main__":
    main()
