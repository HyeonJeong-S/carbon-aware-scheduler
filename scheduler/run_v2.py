"""v2 실험 러너 — 한 실행 = 한 프로세스. 결과: scheduler/data/v2/<name>/{jobs.csv.gz, stats.json, alpha.csv}

    ./.venv/bin/python -m scheduler.run_v2 --name main/knee --engine joint --alpha knee
    ./.venv/bin/python -m scheduler.run_v2 --name main/decoupled --engine decoupled
    ./.venv/bin/python -m scheduler.run_v2 --name main/2stage_eta1 --engine 2stage --eta 1.0
    ./.venv/bin/python -m scheduler.run_v2 --name cap/clean_small --cap-json scheduler/data/v2/scenarios.json:synthetic.cap_clean_small

규약(2026-10-16 감사 반영):
  · 시뮬레이션은 t=0(전 작업)부터, 채점은 --score-from(기본 168h = day 8) 이후 제출 작업만. 동시 실행은 전체 스케줄로 센다.
  · 상한은 물리 설비 cap_r. 기본 --cap 1.25 --cap-mode x-peak → ⌈1.25 × 자기 기준 피크⌉ (합성 17, Azure 43).
  · 예약 ρ 기본 warmup = 준비 구간(0~score-from) 미룰 수 없는 작업의 리전 최대 동시 실행(전 리전 최악) — 사후 지식 아님.
  · 2단계(v1) 는 내부 상한 ⌊η·cap⌋(기본 η=0.8) 으로 돌고 채점은 물리 cap 으로. --eta 1.0 이면 같은 상한.
  · 용량 무시(ignore) 는 cap=∞·ρ=0 으로 돌고 명목 cap 으로 채점(위반·초과시간 모두).
"""
import argparse
import csv
import gzip
import json
import math
import os
import time

from interface import carbon_2025
from interface.regions import REGIONS
from load_balancer.framework.config import JOBS_CSV

from . import capacity, data_loader, forecasters, herding, joint, reproduce

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ROOT = os.path.join(_HERE, "data", "v2")
SCORE_FROM = 168
JOB_COLS = ["job_id", "k", "origin", "region", "submit_time", "duration", "scheduled_start", "delay",
            "carbon_emitted", "latency_ms", "slo_satisfied", "forced", "immediate", "alpha", "over_cap"]


def baseline_out(jobs):
    return {j["id"]: dict(job_id=j["id"], region=j["region"], origin=j["region"], scheduled_start=j["submit_time"],
                          duration=j["duration"], submit_time=j["submit_time"], forced=False, immediate=False)
            for j in jobs}


def nondeferrable_peak(jobs):
    nd = {j["id"]: dict(region=j["region"], scheduled_start=j["submit_time"], duration=j["duration"])
          for j in jobs if math.floor(j["deadline"] - j["duration"]) <= math.floor(j["submit_time"])}
    return joint.peak_ends_first(nd, REGIONS) if nd else dict.fromkeys(REGIONS, 0)


def dump(out, stats, name, extra):
    d = os.path.join(OUT_ROOT, name)
    os.makedirs(d, exist_ok=True)
    with gzip.open(os.path.join(d, "jobs.csv.gz"), "wt", newline="") as f:
        w = csv.writer(f); w.writerow(JOB_COLS)
        for v in out.values():
            w.writerow([v.get(c) for c in JOB_COLS])
    alog = stats.pop("alpha_log", None)
    if alog:
        with open(os.path.join(d, "alpha.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["t", "alpha", "n_plan"]); w.writerows(alog)
    stats.update(extra)
    with open(os.path.join(d, "stats.json"), "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1, default=float)
    return d


def load_cap_json(spec):
    path, _, key = spec.partition(":")
    obj = json.load(open(path))
    for k in key.split(".") if key else []:
        obj = obj[k]
    return {r: int(obj[r]) for r in REGIONS}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--engine", choices=["joint", "decoupled", "greedy", "2stage", "ignore", "ignore_decoupled", "arrival_fixed"], default="joint",
                    help="ignore = 결합 엔진을 cap=∞ 로, ignore_decoupled = 분리형을 cap=∞ 로 (둘 다 명목 cap 으로 채점)")
    ap.add_argument("--alpha", default="knee")
    ap.add_argument("--forecast", default="lstm", help="lstm | oracle | sn24 | lstm_daily | noisy_oracle[:seed] | mix<λ>")
    ap.add_argument("--cap", type=float, default=1.25)
    ap.add_argument("--cap-mode", choices=["abs", "x-peak", "x-own-peak"], default="x-peak")
    ap.add_argument("--cap-json", default=None, help="파일경로:키.경로 — 리전별 상한 dict")
    ap.add_argument("--rho", default="warmup", help="정수 | warmup | auto(사후, day8+ 최악)")
    ap.add_argument("--eta", type=float, default=0.8, help="2stage 내부 상한 비율 ⌊η·cap⌋")
    ap.add_argument("--l-net-max", type=float, default=None)
    ap.add_argument("--horizon", type=int, default=24)
    ap.add_argument("--home-region", action="store_true")
    ap.add_argument("--spatial-only", action="store_true")
    ap.add_argument("--jobs", default=str(JOBS_CSV))
    ap.add_argument("--assign", default=str(reproduce.YEAR_ASSIGN_CSV), help="2stage 용 공간 배정 CSV")
    ap.add_argument("--score-from", type=int, default=SCORE_FROM)
    ap.add_argument("--days", type=int, default=None, help="채점 일수 (제출 < score_from + days·24 인 작업까지만 포함)")
    ap.add_argument("--alpha-grid", default=None)
    ap.add_argument("--seed", type=int, default=0, help="noisy_oracle 잡음 시드")
    args = ap.parse_args(argv)

    data = carbon_2025.load_2025()
    actual, lstm = data["actual"], data["pred24"]
    pred24 = forecasters.build(args.forecast, actual, lstm, seed=args.seed)

    jobs_all = data_loader.load_jobs_with_assignment(args.jobs, args.assign) if args.engine == "2stage" \
        else data_loader.load_jobs_csv(args.jobs)
    if args.engine == "2stage":
        # 배정 CSV 가 이 워크로드의 것인지 — 이름만 같고 제출시각이 다르면 다른 워크로드다 (감사 M3)
        import pandas as pd
        a = pd.read_csv(args.assign, usecols=["job_name", "submit_time"]).set_index("job_name")["submit_time"]
        sample = jobs_all[:2000]
        mism = sum(1 for j in sample if abs(a.get(j["id"], -1) / 3600.0 - j["submit_time"]) > 1e-6)
        assert mism == 0, f"공간 배정 CSV 가 이 워크로드의 것이 아니다 (표본 {len(sample)} 중 {mism} 불일치)"
    hi = args.score_from + args.days * 24 if args.days else float("inf")
    jobs = [j for j in jobs_all if j["submit_time"] < hi]
    win = [j for j in jobs if j["submit_time"] >= args.score_from]
    n_hours = int(max(j["deadline"] for j in jobs)) + 2
    W = capacity._Windows(actual, pred24)
    base = sum(W.actual_mean(j["region"], j["submit_time"], j["duration"]) * j["duration"] for j in win) / 1000.0
    bpeak = joint.peak_ends_first(baseline_out(win), REGIONS)

    if args.cap_json:
        cap = load_cap_json(args.cap_json)
    elif args.cap_mode == "abs":
        cap = int(args.cap)
    elif args.cap_mode == "x-peak":
        cap = int(math.ceil(max(bpeak.values()) * args.cap))
    else:
        cap = {r: int(math.ceil(bpeak[r] * args.cap)) for r in REGIONS}
    cap_d = joint._as_region_dict(cap, REGIONS)

    if args.rho == "warmup":
        rho = max(nondeferrable_peak([j for j in jobs if j["submit_time"] < args.score_from]).values())
    elif args.rho == "auto":
        rho = max(nondeferrable_peak(win).values())
    else:
        rho = int(args.rho)

    lat = joint.latency_dict(REGIONS)
    t0 = time.perf_counter()
    if args.engine == "2stage":
        cap_eff = int(math.floor(args.eta * max(cap_d.values())))
        out, st0 = capacity.run_rolling(jobs, actual, pred24, capacity=cap_eff, regions=REGIONS,
                                        n_hours=n_hours, home_region=args.home_region)
        by_id = {j["id"]: j for j in jobs}
        for k, v in out.items():
            j = by_id[k]
            v["origin"] = j["region"]; v["latency_ms"] = lat[j["region"]][v["region"]]; v["alpha"] = None
        st = joint.summarize(out, REGIONS, cap_d, score_from=args.score_from,
                             extra=dict(cap_eff=cap_eff, eta=args.eta, v1_capacity_violations_at_eff=st0.get("capacity_violations")))
    else:
        grid = tuple(float(x) for x in args.alpha_grid.split(",")) if args.alpha_grid else joint.ALPHA_GRID
        if args.alpha == "knee":
            alpha = "knee"
        elif args.alpha.startswith("path:"):          # path:<alpha.csv> — 다른 실행의 슬롯별 α 경로를 그대로 씀
            with open(args.alpha[5:]) as f:
                rd = csv.DictReader(f); alpha = {int(r["t"]): float(r["alpha"]) for r in rd}
        else:
            alpha = float(args.alpha)
        ignore = args.engine.startswith("ignore")
        mode = {"ignore": "joint", "ignore_decoupled": "decoupled"}.get(args.engine, args.engine)
        run_cap, run_rho = (10 ** 6, 0) if ignore else (cap, rho)
        out, st = joint.run_joint(jobs, actual, pred24, cap=run_cap, regions=REGIONS, latency_ms=lat, rho=run_rho,
                                  horizon=args.horizon, alpha=alpha, alpha_grid=grid, n_hours=n_hours,
                                  l_net_max=args.l_net_max, home_region=args.home_region,
                                  spatial_only=args.spatial_only, score_from=args.score_from, mode=mode)
        if ignore:
            keep = {k: st[k] for k in ("unplaced", "solve_ms_mean", "solve_ms_p95", "solve_ms_max", "n_slots",
                                       "n_lp", "n_mip", "max_vars", "penalties", "mode")}
            st = joint.summarize(out, REGIONS, cap_d, score_from=args.score_from,
                                 alpha_log=st.get("alpha_log"), extra=keep)
    wall = time.perf_counter() - t0

    hm = herding.herding(list(out.values()), actual, REGIONS, cap_d, args.score_from,
                         min(n_hours, len(next(iter(actual.values())))))
    extra = dict(name=args.name, engine=args.engine, alpha_setting=args.alpha, forecast=args.forecast,
                 cap=cap, cap_mode=args.cap_mode, cap_json=args.cap_json, rho=rho, rho_setting=args.rho,
                 l_net_max=args.l_net_max, horizon=args.horizon, home_region=args.home_region,
                 spatial_only=args.spatial_only, jobs_csv=args.jobs, score_from=args.score_from, days=args.days,
                 n_jobs=len(win), n_jobs_simulated=len(jobs), baseline_kg=base, baseline_peak=bpeak,
                 savings_pct=100 * (1 - st["total_carbon_kg"] / base), wall_s=wall, herding=hm)
    d = dump(out, st, args.name, extra)
    print(f"[{args.name}] 채점 {len(win):,}건(시뮬 {len(jobs):,})  기준 {base:,.1f} kg  결과 {st['total_carbon_kg']:,.1f} kg  "
          f"절감 {extra['savings_pct']:.2f}%  위반 {st['capacity_violations']}  초과 {sum(st['hours_over_by_region'].values()):.1f}h  "
          f"마감위반 {st['slo_violations']}  지연 {st['avg_latency_ms']:.1f}/{st['dw_latency_ms']:.1f}ms  "
          f"cap {cap} ρ {rho}  벽시계 {wall/60:.1f}분  → {d}")


if __name__ == "__main__":
    main()
