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

    # 정규화 분모: 창 전체의 최대 실측 강도 (슬롯별이 아닌 전역 — 오프라인이므로)
    cmax = max(float(np.max(actual[r][t0:t1 + 48])) for r in REGIONS)

    var_cost, var_carb, var_lat, cover = [], [], [], {}
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
                var_lat.append(lat[o][r])
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
    A_ub = coo_matrix((vals, (rows, cols)), shape=(nA, nx + nA)).tocsr()
    b_ub = np.full(nA, float(args.cap))
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
    out = dict(start_h=t0, days=args.days, cap=args.cap, alpha=args.alpha, n_jobs=len(jobs), baseline_kg=base,
               lp_kg=lp_kg, lp_savings_pct=100 * (1 - lp_kg / base), lp_overflow=float(o.sum()), lp_latency_ms=lp_lat, lp_objective=float(res.fun),
               lp_fractional_vars=frac, lp_wall_s=time.perf_counter() - t_start, n_vars=nx)
    print(f"LP 하한: {lp_kg:,.1f} kg ({out['lp_savings_pct']:.2f}%)  초과 {o.sum():.2f}  분수변수 {frac}  {out['lp_wall_s']:.1f}s", flush=True)
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
    p = os.path.join(OUT_DIR, f"bound_{t0}_{args.days}d_cap{args.cap}_a{args.alpha}{'_relaxed' if args.relaxed else ''}.json")
    json.dump(out, open(p, "w"), indent=1)
    print("저장:", p)


if __name__ == "__main__":
    main()
