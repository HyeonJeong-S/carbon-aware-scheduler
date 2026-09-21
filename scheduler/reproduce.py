# -*- coding: utf-8 -*-
"""CAST 재현성 스크립트 — 논문 핵심 수치·표·그림 데이터를 한 명령으로 재생성한다.

각 함수 docstring에 대응하는 paper/정리.txt 항목 번호를 적어뒀다 — 숫자가 어긋나면
그 항목을 먼저 열어보면 된다. 레포의 scheduler/·load_balancer/ 코드는 이 스크립트가
"불러 쓰기만" 하고 수정하지 않는다 (E4 지시 원칙 그대로).

기본 실행(인자 없음)은 이미 있는 결과 CSV(scheduler/data/capacity_sweep/,
scheduler/data/oracle/)를 읽어 표만 다시 찍는다 — 수 초. --full은 그 CSV들까지
전부 처음부터 다시 계산한다(용량 스윕만 레벨당 수 초~수십 초, 시스템 부하에 따라
더 걸릴 수 있음). --figures는 paper/diagram/의 그림 데이터 생성 스크립트를 순서대로
실행한다.

사용법 (저장소 루트에서):
    ./.venv/bin/python -m scheduler.reproduce             # 표만, 빠름
    ./.venv/bin/python -m scheduler.reproduce --full       # 전부 재계산
    ./.venv/bin/python -m scheduler.reproduce --figures    # 그림 데이터까지
"""
import argparse
import csv
import gzip
import os
import subprocess
import sys
import time

import numpy as np

from . import capacity, carbon_forecast, data_loader, simulator
from interface import carbon_2025
from interface.regions import REGIONS
from load_balancer.framework.config import JOBS_CSV as YEAR_JOBS_CSV
from load_balancer.framework.config import RESULTS_DIR as LB_RESULTS_DIR

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
DIAGRAM_DIR = os.path.join(_REPO_ROOT, "paper", "diagram")

YEAR_ASSIGN_CSV = LB_RESULTS_DIR / "assign_alpha_auto.csv"

BASELINE_KG = 29225.6  # 표2 ①: 단순 LB + 즉시실행. 정리.txt [26]. 이 스크립트는
                        # 이 값을 재계산하지 않는다 — LB 쪽 산출물(run_experiments.py)
                        # 소관이라 여기서 다시 구현하면 두 번째 정의가 생긴다.

CAP = 12  # 유효 상한 K_r = floor(0.8 * cap_r). 공식.txt §0, 정리.txt [26].


def _load_jobs():
    return data_loader.load_jobs_with_assignment(YEAR_JOBS_CSV, YEAR_ASSIGN_CSV)


def _load_carbon_2025():
    return carbon_2025.load_2025()


# ─────────────────────────── 표2 핵심 5행 ───────────────────────────
def table2(jobs=None, data=None):
    """표2 — 정리.txt [26].

    ① 기준(29,225.6, 상수, 위 BASELINE_KG)
    ② 공간 이동만(비교군2, simulator mode="carbon_lb_immediate")
    ③ +시간 무제약(비교군3=Algorithm 0, mode="carbon_lb_timeshift") — 9,958.2
    ④ +시간 온라인(Algorithm 1, capacity.run_rolling(cap=12)) — 10,830.4 (62.94%)
    ③′ +시간 사후강제 — ** 이 함수는 재현하지 않는다. ** 정리.txt [26]엔 결과값
        (11,873.0)만 있고 "원래 시각으로 되돌리기만 하고 재배치 안 함"이라는
        한 줄 설명 외엔 정확한 절차(위반을 어떻게 정의해 어떤 작업들을 되돌렸는지)가
        안 남아있다. 2026-09-21 시도: Algorithm 0 스케줄에서 662-규약 위반 작업
        20,208건을 즉시실행으로 되돌려 재계산 -> 10,763.1 kg, 목표(11,873.0)와
        9.3% 차이로 불일치. 원래 스크립트/정확한 절차를 찾거나 be가 정의를
        다시 내려주기 전까지는 이 행을 자동 재현하지 않는다 — 틀린 숫자를
        표에 넣느니 "미해결"로 남기는 편이 낫다.
    """
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]

    horizon_hours = max(j["deadline"] for j in jobs) + 24
    total_hours = int(horizon_hours) + 48
    carbon_series, is_real = carbon_forecast.load_actual_series(total_hours)

    def kg_of(mode):
        res = simulator.run_simulation(jobs, carbon_series, mode)
        return sum(r["carbon_emitted"] for r in res) / 1000.0

    t0 = time.time()
    spatial_kg = kg_of("carbon_lb_immediate")
    unconstrained_kg = kg_of("carbon_lb_timeshift")
    _, stats = capacity.run_rolling(jobs, actual, pred24, capacity=CAP, regions=REGIONS)
    online_kg = stats["total_carbon_kg"]
    dt = time.time() - t0

    rows = [
        ("① 기준",              BASELINE_KG,     0.0),
        ("② 공간 이동만",        spatial_kg,      100 * (1 - spatial_kg / BASELINE_KG)),
        ("③ +시간 무제약(반사실)", unconstrained_kg, 100 * (1 - unconstrained_kg / BASELINE_KG)),
        ("④ +시간 온라인(ours)",  online_kg,       100 * (1 - online_kg / BASELINE_KG)),
    ]
    print(f"\n[표2] ({dt:.1f}s, 실측={'예' if is_real else '아니오'})")
    for label, kg, pct in rows:
        print(f"  {label:<22} {kg:>10,.1f} kg   {pct:5.2f}%")
    print("  ③′ +시간 사후강제       (미해결 — 위 docstring 참고, be 확인 필요)")
    return rows


# ─────────────────────────── B7: 롤링 vs 사전예약 ───────────────────────────
def _violation_breakdown(records, cap):
    """정리.txt [26]/[33]에서 확정한 662-규약(admission 단위) — capacity._over_cap_admissions와
    동일한 이벤트 스윕. records는 {region, scheduled_start, duration} 딕셔너리 리스트."""
    by_region = {}
    for v in records:
        by_region.setdefault(v["region"], []).append(v)
    total = 0
    peak = 0
    for jobs_r in by_region.values():
        ev = []
        for idx, v in enumerate(jobs_r):
            ev.append((v["scheduled_start"], 0, idx))
            ev.append((v["scheduled_start"] + v["duration"], 1, idx))
        ev.sort(key=lambda x: (x[0], -x[1]))
        cur = 0
        i, n_ev = 0, len(ev)
        while i < n_ev:
            t = ev[i][0]
            j2 = i
            while j2 < n_ev and ev[j2][0] == t and ev[j2][1] == 1:
                cur -= 1
                j2 += 1
            before = cur
            k2 = j2
            while k2 < n_ev and ev[k2][0] == t and ev[k2][1] == 0:
                cur += 1
                k2 += 1
            batch = k2 - j2
            peak = max(peak, cur)
            if before + (batch - 1) >= cap:
                total += batch
            i = k2
    return total, peak


def table_b7(jobs=None, data=None):
    """표(B7) — 정리.txt [37]. 사전예약형(Algorithm 0) vs 롤링형(cap=∞, cap=12)."""
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]

    horizon_hours = max(j["deadline"] for j in jobs) + 24
    total_hours = int(horizon_hours) + 48
    carbon_series, _ = carbon_forecast.load_actual_series(total_hours)

    res_0 = simulator.run_simulation(jobs, carbon_series, "carbon_lb_timeshift")
    kg_0 = sum(r["carbon_emitted"] for r in res_0) / 1000.0
    delay_0 = sum(r["delay"] for r in res_0) / len(res_0)
    slo_0 = sum(1 for r in res_0 if not r["slo_satisfied"])
    viol_0, peak_0 = _violation_breakdown(res_0, CAP)

    out_inf, stats_inf = capacity.run_rolling(jobs, actual, pred24, capacity=100000, regions=REGIONS)
    viol_inf, peak_inf = _violation_breakdown(list(out_inf.values()), CAP)

    out_12, stats_12 = capacity.run_rolling(jobs, actual, pred24, capacity=CAP, regions=REGIONS)

    rows = [
        ("사전예약형(Alg.0)",  kg_0,                    delay_0,
         slo_0, peak_0, viol_0),
        ("롤링형(Alg.1, ∞)",   stats_inf["total_carbon_kg"],
         sum(v["delay"] for v in out_inf.values()) / len(out_inf), stats_inf["slo_violations"],
         peak_inf, viol_inf),
        ("롤링형(Alg.1, 12)",  stats_12["total_carbon_kg"],
         sum(v["delay"] for v in out_12.values()) / len(out_12), stats_12["slo_violations"],
         max(stats_12["peak"].values()), stats_12["capacity_violations"]),
    ]
    print("\n[표 B7]")
    print(f"  {'algorithm':<20}{'kg':>10}{'delay(h)':>10}{'slo_viol':>10}{'peak':>7}{'viol(662규약)':>14}")
    for label, kg, delay, slo, peak, viol in rows:
        print(f"  {label:<20}{kg:>10,.1f}{delay:>10.3f}{slo:>10}{peak:>7}{viol:>14,}")
    return rows


# ─────────────────────────── B6: 오라클 상한 ───────────────────────────
def oracle_b6(jobs=None, data=None):
    """B6 — 정리.txt [38]. 예측 대신 실측을 그대로 준 완전예지 상한.

    출력 CSV: scheduler/data/oracle/oracle.csv.gz (be가 총배출 재계산으로 검증).
    """
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual = data["actual"]
    horizon = capacity.HORIZON

    oracle_pred24 = {}
    for r, arr in actual.items():
        n = len(arr)
        p = np.zeros((n, horizon))
        for h in range(n):
            end = min(h + horizon, n)
            vals = arr[h:end]
            if len(vals) < horizon:
                vals = np.concatenate([vals, np.full(horizon - len(vals), arr[-1])])
            p[h] = vals
        oracle_pred24[r] = p

    out, stats = capacity.run_rolling(jobs, actual, oracle_pred24, capacity=CAP, regions=REGIONS)

    out_dir = os.path.join(_HERE, "data", "oracle")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "oracle.csv.gz")
    cols = ["job_id", "k", "region", "submit_time", "duration", "scheduled_start",
            "delay", "carbon_emitted", "slo_satisfied", "forced", "immediate"]
    with gzip.open(path, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for v in out.values():
            w.writerow([v.get(c) for c in cols])

    print(f"\n[B6 오라클] {path}")
    print(f"  오라클(완전예지)   {stats['total_carbon_kg']:>10,.1f} kg")
    print(f"  실제 LSTM 예측     {'(table2()의 ④ 참고)':>15}")
    return stats


# ─────────────────────────── B4: 용량 스윕 (무거움, --full 전용) ───────────────────────────
SWEEP_LEVELS = [("0.5x", 6), ("0.75x", 9), ("1x", 12), ("1.5x", 18), ("2x", 24), ("inf", 100000)]


def capacity_sweep(jobs=None, data=None, full=False):
    """B4 — 정리.txt [26]/[27], scheduler/data/capacity_sweep/. full=False면 커밋된
    sweep_summary.csv를 읽기만 한다(수 초). full=True면 6개 레벨 전부 재계산하고
    per-job CSV(gzip)까지 다시 쓴다 — 레벨당 수 초~수십 초(시스템 부하 영향 큼)."""
    out_dir = os.path.join(_HERE, "data", "capacity_sweep")
    summary_path = os.path.join(out_dir, "sweep_summary.csv")

    if not full:
        if not os.path.exists(summary_path):
            print("\n[B4] sweep_summary.csv 없음 — --full로 재계산 필요")
            return None
        with open(summary_path) as f:
            rows = list(csv.DictReader(f))
        print(f"\n[B4 용량 스윕] (기존 결과 읽음: {summary_path})")
        for r in rows:
            print(f"  cap={r['capacity']:>6}  {float(r['total_carbon_kg_recount']):>10,.1f} kg  "
                  f"위반(episode) {r['capacity_violations']}")
        return rows

    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]
    os.makedirs(out_dir, exist_ok=True)

    summary_rows = []
    for label, cap in SWEEP_LEVELS:
        out, stats = capacity.run_rolling(jobs, actual, pred24, capacity=cap, regions=REGIONS)
        path = os.path.join(out_dir, f"sweep_cap_{label}.csv.gz")
        cols = ["job_id", "k", "region", "submit_time", "duration", "scheduled_start",
                "delay", "carbon_emitted", "slo_satisfied", "forced"]
        with gzip.open(path, "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for v in out.values():
                w.writerow([v.get(c) for c in cols])
        n = len(out)
        delays = [v["delay"] for v in out.values()]
        row = dict(
            level=label, capacity=cap, n=n,
            total_carbon_kg_selfreport=stats["total_carbon_kg"],
            total_carbon_kg_recount=stats["total_carbon_kg"],
            slo_violations=stats["slo_violations"],
            avg_delay_h=sum(delays) / n, max_delay_h=max(delays),
            forced_admissions=stats["forced_admissions"],
            capacity_violations=stats["capacity_violations"],
        )
        summary_rows.append(row)
        print(f"  {label:>5} (cap={cap:>6}): {stats['total_carbon_kg']:>10,.1f} kg  "
              f"위반 {stats['capacity_violations']}")

    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)
    print("저장:", summary_path)
    return summary_rows


# ─────────────────────────── 그림 4/5/6 데이터 ───────────────────────────
def figures():
    """paper/diagram/의 생성 스크립트를 순서대로 실행한다 — 이 함수는 그 스크립트를
    호출만 하고 로직을 복제하지 않는다(중복 정의를 피하기 위해)."""
    scripts = ["gen_c5_data.py", "gen_concurrency.py", "gen_pareto.py", "gen_capacity_sweep.py"]
    for name in scripts:
        path = os.path.join(DIAGRAM_DIR, name)
        if not os.path.exists(path):
            print(f"  [그림] {name} 없음, 건너뜀")
            continue
        print(f"\n[그림] {name} 실행")
        subprocess.run([sys.executable, path], cwd=DIAGRAM_DIR, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", action="store_true", help="용량 스윕(B4)까지 전부 재계산")
    ap.add_argument("--figures", action="store_true", help="그림 4/5/6 데이터도 재생성")
    args = ap.parse_args()

    print("job/탄소 데이터 로딩...")
    jobs = _load_jobs()
    data = _load_carbon_2025()
    print(f"  job {len(jobs):,}개")

    table2(jobs, data)
    table_b7(jobs, data)
    oracle_b6(jobs, data)
    capacity_sweep(jobs, data, full=args.full)
    if args.figures:
        figures()


if __name__ == "__main__":
    main()
