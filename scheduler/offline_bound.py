"""M3 — 1주 창의 오프라인 최적해(하한). 완전예지·물리 상한·초과 변수 포함으로 식 (7)~(10)을
그 주의 모든 작업에 대해 **한 번에** 푼다. 후보 시작 슬롯은 각 작업의 전체 창 [s_j, D_j − d_j]
(지평 24h 제한 없음). LP 완화가 곧 하한이고, 가능하면 MILP 로 정수해도 구한다.

    ./.venv/bin/python -m scheduler.offline_bound --start-h 5544 --days 7 --cap 17 [--alpha 1.0] [--milp]

같은 창·같은 작업·같은 상한으로 돌린 결합 롤링(run_v2 --warmup-h 5544 --days 7 --forecast oracle)
의 배출과 비교하면 최적성 격차가 된다.
"""
import argparse
import json
import math
import os
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

from interface import carbon_2025
from interface.regions import REGIONS
from load_balancer.framework.config import JOBS_CSV

from . import capacity, data_loader, joint

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "data", "v2", "offline")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-h", type=int, required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--cap", type=int, default=17)
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--jobs", default=str(JOBS_CSV))
    ap.add_argument("--milp", action="store_true")
    ap.add_argument("--relaxed", action="store_true", help="용량 행에 슬롯을 통째로 덮는 실행만 넣는다(참 하한)")
    ap.add_argument("--time-limit", type=float, default=1800)
    ap.add_argument("--carry-run", default=None, help="10-19 B[3c]: 이 실행에서 창 전에 시작해 창 안까지 도는 작업을 그 실행의 자리에 고정 점유로 넣고,"
                    " 같은 셈법의 그 실행 초과량(창 안 슬롯)을 함께 낸다 — 높은 부하의 초과가 완전예지로도 피할 수 없었는지")
    ap.add_argument("--match-run", default=None, help="3회차 B[6]: 이 연간 실행에서 그 주에 제출된 작업의 실행 시간 가중 지연 Λ̄ 를 예산으로 두고"
                    " 배출만 최소화(지연 합 ≤ Λ̄ 행 추가) — 같은 지연에서의 하한. 격차 = 그 실행의 그 주 작업 배출 − 하한")
    args = ap.parse_args(argv)

    data = carbon_2025.load_2025()
    actual = data["actual"]
    orc = joint.sn24_pred24(actual)        # 자리만; 회계는 actual_mean 만 쓴다
    W = capacity._Windows(actual, orc)
    lat = joint.latency_dict(REGIONS)
    t0, t1 = args.start_h, args.start_h + 24 * args.days
    jobs = [j for j in data_loader.load_jobs_csv(args.jobs) if t0 <= j["submit_time"] < t1]
    base = sum(W.actual_mean(j["region"], j["submit_time"], j["duration"]) * j["duration"] for j in jobs) / 1000
    print(f"창 {t0}~{t1}h 작업 {len(jobs):,} 기준 {base:,.1f} kg", flush=True)
    run_kg = lat_budget = None
    if args.match_run:
        import pandas as pd
        rdf = pd.read_csv(os.path.join(_HERE, "data", "v2", args.match_run, "jobs.csv.gz"))
        rdf = rdf[(rdf.submit_time >= t0) & (rdf.submit_time < t1)]
        assert len(rdf) == len(jobs), (len(rdf), len(jobs))
        run_kg = float(rdf.carbon_emitted.sum()) / 1000
        lat_budget = float((rdf.latency_ms * rdf.duration).sum() / rdf.duration.sum())
        args.alpha = 1.0
        print(f"{args.match_run}: 그 주 작업 {run_kg:,.1f} kg, d가중 지연 {lat_budget:.2f} ms → 예산", flush=True)

    # 정규화 분모: 창 전체의 최대 실측 강도 (슬롯별이 아닌 전역 — 오프라인이므로)
    cmax = max(float(np.max(actual[r][t0:t1 + 48])) for r in REGIONS)

    var_cost, var_carb, var_lat, var_d, cover = [], [], [], [], {}
    row_eq = []
    tau_max = t1 + 48
    for jj, j in enumerate(jobs):
        d = j["duration"]; o = j["region"]
        late = j["deadline"] - d
        nondef = math.floor(late) <= math.floor(j["submit_time"])
        starts = [j["submit_time"]] if nondef else [j["submit_time"]] + list(range(int(math.ceil(j["submit_time"])), int(math.floor(late)) + 1))
        for r in REGIONS:
            lt = lat[o][r] / joint.L_NET_MAX_MS
            for st in starts:
                ch = W.actual_mean(r, st, d)
                v = len(var_cost)
                var_cost.append(d * (args.alpha * ch / cmax + (1 - args.alpha) * lt))
                var_carb.append(ch * d)
                var_lat.append(lat[o][r]); var_d.append(d)
                row_eq.append(jj)
                # 10-17: 엄밀한 하한이 되려면 용량을 '덜' 세야 한다 — 슬롯 단위 덮음(부분 겹침도 한 자리)은 롤링의
                # 시작 순간 단위보다 보수적이라 롤링이 '하한'보다 낮게 나왔다(98.12 vs 98.05). --relaxed 면 실행 구간이
                # 슬롯을 통째로 덮을 때만 센다(완화 → 참 하한). 기본(슬롯 덮음)은 참고용으로 남긴다.
                slots = [tau for tau in joint.covered_slots(st, d) if (not args.relaxed) or (st <= tau and st + d >= tau + 1)]
                for tau in slots:
                    if tau <= tau_max:
                        cover.setdefault((r, tau), []).append(v)
    nx = len(var_cost)
    keys = list(cover)
    nA = len(keys)
    rows, cols, vals = [], [], []
    for k, key in enumerate(keys):
        for v in cover[key]:
            rows.append(k); cols.append(v); vals.append(1.0)
        rows.append(k); cols.append(nx + k); vals.append(-1.0)
    carry = {}
    run_over = None
    if args.carry_run:
        import pandas as pd
        cdf = pd.read_csv(os.path.join(_HERE, "data", "v2", args.carry_run, "jobs.csv.gz"))
        pre = cdf[(cdf.submit_time < t0) & (cdf.scheduled_start + cdf.duration > t0)]
        for r, st, d in zip(pre.region, pre.scheduled_start, pre.duration):
            for tau in joint.covered_slots(st, d):
                if t0 <= tau <= tau_max and ((not args.relaxed) or (st <= tau and st + d >= tau + 1)):
                    carry[(r, tau)] = carry.get((r, tau), 0) + 1
        # 그 실행의 같은 셈법 초과량: 창 안 슬롯에서 (덮는 작업 수 − 상한)+ 의 합
        occ = {}
        live = cdf[(cdf.scheduled_start + cdf.duration > t0) & (cdf.submit_time < t1)]
        for r, st, d in zip(live.region, live.scheduled_start, live.duration):
            for tau in joint.covered_slots(st, d):
                if t0 <= tau <= tau_max and ((not args.relaxed) or (st <= tau and st + d >= tau + 1)):
                    occ[(r, tau)] = occ.get((r, tau), 0) + 1
        run_over = float(sum(max(0, n - args.cap) for n in occ.values()))
        print(f"{args.carry_run}: 창 앞에서 넘어온 작업 {len(pre)}건, 그 실행의 같은 셈법 초과량 {run_over:.0f}", flush=True)
        for key, n in carry.items():
            if key not in cover:
                cover[key] = []
        keys = list(cover)
        nA = len(keys)
        rows, cols, vals = [], [], []
        for k, key in enumerate(keys):
            for v in cover[key]:
                rows.append(k); cols.append(v); vals.append(1.0)
            rows.append(k); cols.append(nx + k); vals.append(-1.0)
    b_list = [float(args.cap) - carry.get(key, 0) for key in keys]
    if lat_budget is not None:      # Σ x·d·(ℓ − Λ̄) ≤ 0
        for v in range(nx):
            rows.append(nA); cols.append(v); vals.append(var_d[v] * (var_lat[v] - lat_budget))
        b_list.append(0.0)
    A_ub = coo_matrix((vals, (rows, cols)), shape=(len(b_list), nx + nA)).tocsr()
    b_ub = np.asarray(b_list)
    A_eq = coo_matrix((np.ones(nx), (row_eq, np.arange(nx))), shape=(len(jobs), nx + nA)).tocsr()
    b_eq = np.ones(len(jobs))
    # 벌점은 run_joint 와 같은 규칙(감사 뒤): M_B = max(10, 2·max d_j), M_A = 100·M_B — 옛 상수 joint.M_A 는 없어졌다(10-17)
    M_A = 100.0 * max(10.0, 2.0 * max(j["duration"] for j in jobs))
    c = np.concatenate([np.asarray(var_cost), np.full(nA, M_A)])
    lb = np.zeros(nx + nA); ub = np.concatenate([np.ones(nx), np.full(nA, np.inf)])
    print(f"변수 {nx:,} + 초과 {nA:,}, 제약 {nA + len(jobs):,}", flush=True)

    t_start = time.perf_counter()
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=list(zip(lb, ub)), method="highs")
    assert res.status == 0, res.message
    x = res.x[:nx]; o = res.x[nx:]
    lp_kg = float(np.dot(x, var_carb)) / 1000
    frac = int(np.sum((x > 1e-6) & (x < 1 - 1e-6)))
    lp_lat = float(np.dot(x, var_lat)) / len(jobs)   # 10-17: α<1 비교용 작업당 평균 지연(ms)
    lp_dw = float(np.dot(x, np.asarray(var_lat) * np.asarray(var_d)) / np.dot(x, var_d))
    out = dict(start_h=t0, days=args.days, cap=args.cap, alpha=args.alpha, n_jobs=len(jobs), baseline_kg=base,
               lp_kg=lp_kg, lp_savings_pct=100 * (1 - lp_kg / base), lp_overflow=float(o.sum()), lp_latency_ms=lp_lat, lp_dw_latency_ms=lp_dw, lp_objective=float(res.fun),
               lp_fractional_vars=frac, lp_wall_s=time.perf_counter() - t_start, n_vars=nx)
    print(f"LP 하한: {lp_kg:,.1f} kg ({out['lp_savings_pct']:.2f}%)  초과 {o.sum():.2f}  분수변수 {frac}  d가중 지연 {lp_dw:.2f} ms  {out['lp_wall_s']:.1f}s", flush=True)
    if run_over is not None:
        out.update(carry_run=args.carry_run, carry_slots=len(carry), run_overflow=run_over)
    if run_kg is not None:
        out.update(match_run=args.match_run, run_kg=run_kg, lat_budget_dw_ms=lat_budget,
                   gap_pp=100 * (run_kg - lp_kg) / base, gap_of_remaining_pct=100 * (run_kg - lp_kg) / run_kg)
        print(f"격차: {run_kg - lp_kg:,.1f} kg = {out['gap_pp']:.2f}%p (그 실행의 남은 배출의 {out['gap_of_remaining_pct']:.1f}%)", flush=True)
    if args.milp and frac:
        t_m = time.perf_counter()
        resm = milp(c, constraints=[LinearConstraint(A_ub, -np.inf, b_ub), LinearConstraint(A_eq, b_eq, b_eq)],
                    integrality=np.concatenate([np.ones(nx), np.zeros(nA)]), bounds=Bounds(lb, ub),
                    options=dict(time_limit=args.time_limit))
        if resm.x is not None:
            xm = resm.x[:nx]; om = resm.x[nx:]
            out.update(milp_kg=float(np.dot(xm, var_carb)) / 1000, milp_overflow=float(om.sum()), milp_latency_ms=float(np.dot(xm, var_lat)) / len(jobs), milp_objective=float(resm.fun),
                       milp_status=int(resm.status), milp_gap=float(getattr(resm, "mip_gap", float("nan"))),
                       milp_wall_s=time.perf_counter() - t_m)
            print(f"MILP: {out['milp_kg']:,.1f} kg  초과 {om.sum():.2f}  status {resm.status}  {out['milp_wall_s']:.1f}s", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    tag = f"_lat_{args.match_run.replace('/', '_')}" if args.match_run else ""
    if args.carry_run:
        tag += f"_carry_{args.carry_run.replace('/', '_')}"
    p = os.path.join(OUT_DIR, f"bound_{t0}_{args.days}d_cap{args.cap}_a{args.alpha}{'_relaxed' if args.relaxed else ''}{tag}.json")
    json.dump(out, open(p, "w"), indent=1)
    print("저장:", p)


if __name__ == "__main__":
    main()
