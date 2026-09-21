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
    ./.venv/bin/python -m scheduler.reproduce                # 표만, 빠름
    ./.venv/bin/python -m scheduler.reproduce --full          # B4 스윕까지 전부 재계산
    ./.venv/bin/python -m scheduler.reproduce --figures       # 그림 데이터까지
    ./.venv/bin/python -m scheduler.reproduce --sensitivity   # E5 민감도 실험 3종까지 (수 분)
"""
import argparse
import csv
import gzip
import os
import subprocess
import sys
import time

import numpy as np

from . import capacity, carbon_forecast, data_loader, simulator, timeshift
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
def _overlap_violating(jobs, cap, start_key):
    """구간 스윕으로 concurrency > cap 인 시각 구간(over span)을 구하고, 실행구간이
    그 구간과 조금이라도 겹치는 작업 전부를 위반으로 반환한다 — 662-규약(admission,
    "자기 시작 순간에 n>=cap")보다 넓은 정의다: 시작할 때는 안 걸려도 실행 도중에
    남이 상한을 넘기면 같이 걸린다. posthoc_enforce()가 쓰는 정의이며, 위반 시작
    시점만 보는 admission 정의로는 사후강제(11,873.0kg/31,250건)가 재현되지
    않는다(2026-09-21 확인, 10,763.1kg/21,341건으로 불일치)."""
    ev = []
    for j in jobs:
        s = j[start_key]
        e = s + j["duration"]
        if e > s:
            ev.append((s, 1))
            ev.append((e, -1))
    ev.sort(key=lambda x: (x[0], -x[1]))
    cur = 0
    pts = []
    for t, d in ev:
        cur += d
        pts.append((t, cur))
    over_spans = [(t0, t1) for (t0, c0), (t1, _) in zip(pts, pts[1:])
                  if c0 > cap and t1 > t0]
    viol = set()
    for idx, j in enumerate(jobs):
        s = j[start_key]
        e = s + j["duration"]
        for a, b in over_spans:
            if s < b and a < e:
                viol.add(idx)
                break
    return viol


def posthoc_enforce(res_0, carbon_series, cap):
    """표2 ③′ +시간 사후강제 — 정리.txt [26], 절차는 원고 문단680/682에서 복원.

    "일부러 멍청한" 순진한 하한: Algorithm 0(무제약) 스케줄에서 출발해, 리전별로
    독립적으로 다음을 상한 초과가 사라질 때까지 반복한다.
      1. 그 리전 작업들의 **현재** (start,end)로 연속시각 스윕 -> concurrency>cap
         인 구간을 찾는다.
      2. 아직 안 되돌린 작업 중 그 구간과 실행 구간이 겹치는 것 전부를 즉시실행
         (start=submit_time)으로 되돌린다. 새로 되돌릴 게 없으면 멈춘다(이
         "더 없음을 확인한" 마지막 패스도 반복 횟수에 들어간다 — 아래 검증 참고).
    재배치는 하지 않는다(되돌린 작업은 그 자리에 고정) — 그래서 "일부러 멍청하다".

    2026-09-21 검증: 이 절차로 총 되돌림 31,250건(문단682와 일치), FR 5회·
    US-CAL-CISO 3회 수렴(문단680과 일치), 총배출 11,873.0kg(정리.txt [26]과
    소수점까지 일치) — 세 기준 전부 맞아 원래 절차로 확정.
    """
    schedule = {r["job_id"]: dict(r, cur_start=r["scheduled_start"], reverted=False)
                for r in res_0}
    by_region = {}
    for r in res_0:
        by_region.setdefault(r["region"], []).append(schedule[r["job_id"]])

    reverted_total = set()
    rounds_by_region = {}
    for region, jobs in by_region.items():
        rnd = 0
        while True:
            viol_idx = _overlap_violating(jobs, cap, "cur_start")
            new_reverts = [idx for idx in viol_idx if not jobs[idx]["reverted"]]
            rnd += 1   # 되돌린 라운드든, "더 없음"을 확인한 마지막 라운드든 1회로 센다
            if not new_reverts:
                break
            for idx in new_reverts:
                jobs[idx]["reverted"] = True
                jobs[idx]["cur_start"] = jobs[idx]["submit_time"]
                reverted_total.add(jobs[idx]["job_id"])
        rounds_by_region[region] = rnd

    total_kg = 0.0
    for r in res_0:
        st = schedule[r["job_id"]]
        if st["reverted"]:
            series = carbon_series[r["region"]]
            rate = timeshift.mean_carbon(series, st["cur_start"], r["duration"], len(series))
            total_kg += rate * r["duration"]
        else:
            total_kg += r["carbon_emitted"]
    total_kg /= 1000.0

    return dict(total_carbon_kg=total_kg, reverted=len(reverted_total),
                rounds_by_region=rounds_by_region)


def table2(jobs=None, data=None):
    """표2 — 정리.txt [26].

    ① 기준(29,225.6, 상수, 위 BASELINE_KG)
    ② 공간 이동만(비교군2, simulator mode="carbon_lb_immediate")
    ③ +시간 무제약(비교군3=Algorithm 0, mode="carbon_lb_timeshift") — 9,958.2
    ④ +시간 온라인(Algorithm 1, capacity.run_rolling(cap=12)) — 10,830.4 (62.94%)
    ③′ +시간 사후강제(posthoc_enforce, ③의 스케줄에 반복 되돌리기 적용) — 11,873.0
    """
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]

    horizon_hours = max(j["deadline"] for j in jobs) + 24
    total_hours = int(horizon_hours) + 48
    carbon_series, is_real = carbon_forecast.load_actual_series(total_hours)

    t0 = time.time()
    res_spatial = simulator.run_simulation(jobs, carbon_series, "carbon_lb_immediate")
    spatial_kg = sum(r["carbon_emitted"] for r in res_spatial) / 1000.0

    res_0 = simulator.run_simulation(jobs, carbon_series, "carbon_lb_timeshift")
    unconstrained_kg = sum(r["carbon_emitted"] for r in res_0) / 1000.0

    posthoc = posthoc_enforce(res_0, carbon_series, CAP)

    _, stats = capacity.run_rolling(jobs, actual, pred24, capacity=CAP, regions=REGIONS)
    online_kg = stats["total_carbon_kg"]
    dt = time.time() - t0

    rows = [
        ("① 기준",                BASELINE_KG,       0.0),
        ("② 공간 이동만",          spatial_kg,        100 * (1 - spatial_kg / BASELINE_KG)),
        ("③ +시간 무제약(반사실)",   unconstrained_kg,  100 * (1 - unconstrained_kg / BASELINE_KG)),
        ("④ +시간 온라인(ours)",    online_kg,         100 * (1 - online_kg / BASELINE_KG)),
        ("③′ +시간 사후강제(하한)",  posthoc["total_carbon_kg"],
         100 * (1 - posthoc["total_carbon_kg"] / BASELINE_KG)),
    ]
    print(f"\n[표2] ({dt:.1f}s, 실측={'예' if is_real else '아니오'})")
    for label, kg, pct in rows:
        print(f"  {label:<22} {kg:>10,.1f} kg   {pct:5.2f}%")
    print(f"  (사후강제 되돌림 {posthoc['reverted']:,}건, FR {posthoc['rounds_by_region'].get('FR')}회 / "
          f"US-CAL-CISO {posthoc['rounds_by_region'].get('US-CAL-CISO')}회 수렴)")
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


# ─────────────────────────── E5: 민감도 실험 ───────────────────────────
def _scale_jobs(jobs, factor, rng):
    """factor배로 job 수를 늘리거나 줄인다 — 0.5x는 무작위 다운샘플(제출시각·리전
    분포는 원본 그대로 유지), 2x는 정수배만큼 통짜 복제(id만 분리) + 소수부는
    추가 다운샘플. 둘 다 시드 고정(rng)이라 재현 가능하다."""
    if factor == 1.0:
        return list(jobs)
    if factor < 1.0:
        n = int(round(len(jobs) * factor))
        return rng.sample(jobs, n)
    whole, frac = int(factor), factor - int(factor)
    out = []
    for copy_i in range(whole):
        for j in jobs:
            out.append(dict(j, id=f"{j['id']}_x{copy_i}"))
    if frac > 0:
        extra_n = int(round(len(jobs) * frac))
        out += [dict(j, id=f"{j['id']}_xf") for j in rng.sample(jobs, extra_n)]
    return out


def _oracle_pred24(actual, horizon):
    out = {}
    for r, arr in actual.items():
        n = len(arr)
        p = np.zeros((n, horizon))
        for h in range(n):
            end = min(h + horizon, n)
            vals = arr[h:end]
            if len(vals) < horizon:
                vals = np.concatenate([vals, np.full(horizon - len(vals), arr[-1])])
            p[h] = vals
        out[r] = p
    return out


def _dump_gz(out, path, cols):
    with gzip.open(path, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for v in out.values():
            w.writerow([v.get(c) for c in cols])


def sensitivity(jobs=None, data=None):
    """E5 민감도 실험 3종 — 정리.txt (be가 기록하는 번호, reproduce.py 기준 2026-09-21
    작성 시점 최신 항목은 [39]). 전부 롤링(Algorithm 1, cap=12) 기준.

    1. 작업량 스케일 0.5x/1x/2x — 절감률·위반·지연이 부하에 어떻게 반응하는지.
       기준(baseline)은 그 스케일된 job 집합 자체로 다시 잰다(simple_lb_immediate).
    2. 예측오차 주입 σ=0(오라클)/10/20/30% — 오라클(B6, 정리.txt [38])에 상대적
       가우시안 노이즈(승법, 음수 클리핑)를 얹어 절감률-오차 곡선을 얻는다.
    3. 예측지평 H=12/24/48h — capacity.run_rolling(horizon=H)만 바꾼다.
       ** H=48은 데이터 한계로 H=24와 완전히 같은 결과가 나온다 ** — 원본
       eval_records가 애초에 24h 앞까지만 예측을 담고 있어서(carbon_2025.HORIZON),
       _Windows.pred_mean이 offset을 23으로 clip한다. 즉 이 스크립트가 48h 앞
       예측을 "가짜로 정확하게" 만들어내지 않는 한 H=48은 시험 불가능하다 —
       그래서 안 만들었고, 대신 이 사실 자체를 결과로 보고한다.

    출력: scheduler/data/sensitivity/*.csv.gz (레벨별 per-job), 반환값은 세
    딕셔너리의 튜플(scale_rows, noise_rows, horizon_rows).
    """
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]
    out_dir = os.path.join(_HERE, "data", "sensitivity")
    os.makedirs(out_dir, exist_ok=True)
    job_cols = ["job_id", "k", "region", "submit_time", "duration", "scheduled_start",
                "delay", "carbon_emitted", "slo_satisfied", "forced"]

    # 1) 작업량 스케일
    print("\n[E5-1] 작업량 스케일")
    rng = __import__("random").Random(42)
    scale_rows = []
    for label, factor in [("0.5x", 0.5), ("1x", 1.0), ("2x", 2.0)]:
        scaled = _scale_jobs(jobs, factor, rng)
        horizon_hours = max(j["deadline"] for j in scaled) + 24
        total_hours = int(horizon_hours) + 48
        carbon_series, _ = carbon_forecast.load_actual_series(total_hours)
        res_base = simulator.run_simulation(scaled, carbon_series, "simple_lb_immediate")
        baseline_kg = sum(r["carbon_emitted"] for r in res_base) / 1000.0

        out, stats = capacity.run_rolling(scaled, actual, pred24, capacity=CAP, regions=REGIONS)
        n = len(out)
        delays = [v["delay"] for v in out.values()]
        red_pct = 100 * (1 - stats["total_carbon_kg"] / baseline_kg)
        row = dict(label=label, n=n, baseline_kg=baseline_kg,
                   online_kg=stats["total_carbon_kg"], reduction_pct=red_pct,
                   slo_violations=stats["slo_violations"], forced=stats["forced_admissions"],
                   capacity_violations=stats["capacity_violations"],
                   avg_delay_h=sum(delays) / n)
        scale_rows.append(row)
        print(f"  {label:<5} n={n:>7,}  기준 {baseline_kg:>10,.1f}kg  온라인 {stats['total_carbon_kg']:>10,.1f}kg"
              f"  절감률 {red_pct:5.2f}%  위반 {stats['capacity_violations']:>6,}  지연 {sum(delays)/n:.3f}h")
        _dump_gz(out, os.path.join(out_dir, f"scale_{label}.csv.gz"), job_cols)

    # 2) 예측오차 주입
    print("\n[E5-2] 예측오차 주입 (오라클 + 가우시안 노이즈)")
    oracle = _oracle_pred24(actual, capacity.HORIZON)
    noise_rng = np.random.default_rng(42)
    noise_rows = []
    for sigma in (0.0, 0.10, 0.20, 0.30):
        if sigma == 0.0:
            pred = oracle
        else:
            pred = {}
            for r, p in oracle.items():
                noisy = p * (1.0 + noise_rng.normal(0.0, sigma, size=p.shape))
                np.clip(noisy, 0.0, None, out=noisy)
                pred[r] = noisy
        out, stats = capacity.run_rolling(jobs, actual, pred, capacity=CAP, regions=REGIONS)
        red_pct = 100 * (1 - stats["total_carbon_kg"] / BASELINE_KG)
        row = dict(sigma=sigma, total_carbon_kg=stats["total_carbon_kg"], reduction_pct=red_pct,
                   slo_violations=stats["slo_violations"],
                   capacity_violations=stats["capacity_violations"])
        noise_rows.append(row)
        print(f"  σ={int(sigma*100):>3}%  {stats['total_carbon_kg']:>10,.1f}kg  절감률 {red_pct:5.2f}%"
              f"  위반 {stats['capacity_violations']:>4,}")
        _dump_gz(out, os.path.join(out_dir, f"noise_sigma{int(sigma*100)}.csv.gz"), job_cols)

    # 3) 예측 지평
    print("\n[E5-3] 예측 지평 H")
    horizon_rows = []
    for H in (12, 24, 48):
        out, stats = capacity.run_rolling(jobs, actual, pred24, capacity=CAP, regions=REGIONS, horizon=H)
        red_pct = 100 * (1 - stats["total_carbon_kg"] / BASELINE_KG)
        row = dict(H=H, total_carbon_kg=stats["total_carbon_kg"], reduction_pct=red_pct,
                   slo_violations=stats["slo_violations"],
                   capacity_violations=stats["capacity_violations"])
        horizon_rows.append(row)
        print(f"  H={H:>2}h  {stats['total_carbon_kg']:>10,.1f}kg  절감률 {red_pct:5.2f}%"
              f"  위반 {stats['capacity_violations']:>4,}"
              + ("  (데이터 상한 24h로 H=24와 동일 — 진짜 48h 예측 없음)" if H == 48 else ""))
        _dump_gz(out, os.path.join(out_dir, f"horizon_H{H}.csv.gz"), job_cols)

    return scale_rows, noise_rows, horizon_rows


# ─────────────────────────── §6.5 재구성 (표3~6 대체) ───────────────────────────
# 정리.txt [46]. 처음엔 cap 절대값(8/16/32/64)을 새로 돌렸으나, 그림6이 이미
# B4 그리드(6/9/12/18/24/∞ = 기준 12의 0.5x~2x·무제약)로 들어가 있어 표와
# 그림이 어긋나는 문제가 있어 be 지시로 B4 그리드로 통일했다. B4의 per-job
# CSV(scheduler/data/capacity_sweep/, 이미 커밋됨)를 그대로 읽어 계산하므로
# run_rolling을 다시 돌리지 않는다 — 전부 "이미 있는 산출물에서 재계산"이다.
SWEEP_DIR = os.path.join(_HERE, "data", "capacity_sweep")
SWEEP_LEVELS_B4 = ["0.5x", "0.75x", "1x", "1.5x", "2x", "inf"]
SWEEP_LEVEL_CAP = {"0.5x": 6, "0.75x": 9, "1x": 12, "1.5x": 18, "2x": 24, "inf": 100000}
SPATIAL_ONLY_PCT = 56.85  # 표2 ②. 시간이동 기여(%p)의 기준선.


def _load_sweep_level(level):
    path = os.path.join(SWEEP_DIR, f"sweep_cap_{level}.csv.gz")
    rows = []
    with gzip.open(path, "rt", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(dict(
                job_id=row["job_id"], k=int(row["k"]), region=row["region"],
                scheduled_start=float(row["scheduled_start"]), duration=float(row["duration"]),
                delay=float(row["delay"]), carbon_emitted=float(row["carbon_emitted"]),
                forced=(row["forced"] == "True"),
            ))
    return rows


def _region_group(r):
    if r == "FR":
        return "France"
    if r == "US-CAL-CISO":
        return "California"
    return "나머지 6개"


def _over_cap_count(records, cap):
    """662-규약(admission 단위) 위반 배정 개수 — capacity._over_cap_admissions와
    동일한 이벤트 스윕이되, 이 CSV엔 immediate 플래그가 없어 forced/비-forced
    두 갈래로만 집계한다(비-forced에는 정상 P경로와 즉시실행 우회가 섞여 있음)."""
    by_region = {}
    for v in records:
        by_region.setdefault(v["region"], []).append(v)
    forced_ct = other_ct = 0
    for jobs_r in by_region.values():
        ev = []
        for idx, v in enumerate(jobs_r):
            ev.append((v["scheduled_start"], 0, idx))
            ev.append((v["scheduled_start"] + v["duration"], 1, idx))
        ev.sort(key=lambda x: (x[0], -x[1]))
        cur, i, n_ev = 0, 0, len(ev)
        while i < n_ev:
            t = ev[i][0]
            j2 = i
            while j2 < n_ev and ev[j2][0] == t and ev[j2][1] == 1:
                cur -= 1; j2 += 1
            before = cur
            k2 = j2
            while k2 < n_ev and ev[k2][0] == t and ev[k2][1] == 0:
                cur += 1; k2 += 1
            batch = k2 - j2
            if before + (batch - 1) >= cap:
                for _, _, idx in ev[j2:k2]:
                    if jobs_r[idx]["forced"]:
                        forced_ct += 1
                    else:
                        other_ct += 1
            i = k2
    return forced_ct + other_ct, forced_ct, other_ct


def _region_sweep(records, region, cap):
    """한 리전의 (peak, hours_over) — capacity.CapacityLedger._sweep과 동일 알고리즘."""
    spans = [(v["scheduled_start"], v["scheduled_start"] + v["duration"])
             for v in records if v["region"] == region]
    ev = []
    for s, e in spans:
        if e > s:
            ev.append((s, 1)); ev.append((e, -1))
    ev.sort(key=lambda x: (x[0], -x[1]))
    cur = mx = 0
    spans_pts = []
    for t, d in ev:
        cur += d
        mx = max(mx, cur)
        spans_pts.append((t, cur))
    over = 0.0
    over_spans = []
    for (t0, c0), (t1, _) in zip(spans_pts, spans_pts[1:]):
        if c0 > cap and t1 > t0:
            over += t1 - t0
            over_spans.append((t0, t1))
    return mx, over, over_spans


def capacity_sweep_abs(jobs=None, data=None):
    """§6.5 재구성 — 정리.txt [46]. B4 그리드(scheduler/data/capacity_sweep/)를
    그대로 읽어 표3~6을 대체할 수치를 낸다 — run_rolling 재실행 없음.

    표3~4 대체: 레벨별 총배출·절감률·시간이동 기여(%p, 표2②=56.85% 기준)·
    강제편입·위반(662규약)·평균지연.
    표5~6 대체: 레벨별 프랑스/캘리포니아/나머지 6개 리전 배정 작업 수·배출량 —
    "부하가 저탄소 리전부터 순서대로 포화한다"는 서사가 롤링에서도 성립하는지
    California 배정 수가 cap에 대해 단조증가(=cap이 클수록 더 많이 배정)하는지로
    판정한다.
    """
    with open(os.path.join(SWEEP_DIR, "sweep_summary.csv")) as f:
        summary_by_level = {r["level"]: r for r in csv.DictReader(f)}

    main_rows, region_rows = [], []
    ca_n_by_level = {}

    print("\n[§6.5 재구성 — B4 그리드 표3~4 대체]")
    for level in SWEEP_LEVELS_B4:
        cap = SWEEP_LEVEL_CAP[level]
        records = _load_sweep_level(level)
        n = len(records)
        total_kg = sum(v["carbon_emitted"] for v in records) / 1000.0
        red_pct = 100 * (1 - total_kg / BASELINE_KG)
        temporal_pp = red_pct - SPATIAL_ONLY_PCT
        avg_delay = sum(v["delay"] for v in records) / n
        forced_n = sum(1 for v in records if v["forced"])
        viol_total, viol_forced, viol_other = _over_cap_count(records, cap)

        row = dict(level=level, capacity=cap, total_carbon_kg=total_kg, reduction_pct=red_pct,
                   temporal_contribution_pp=temporal_pp, forced_admissions=forced_n,
                   capacity_violations_662=viol_total, avg_delay_h=avg_delay)
        main_rows.append(row)
        print(f"  {level:>5}(cap={cap:>6}) {total_kg:>10,.1f}kg  절감 {red_pct:6.2f}%  "
              f"시간이동기여 {temporal_pp:+6.2f}%p  강제 {forced_n:>6,}  "
              f"위반662 {viol_total:>6,}(강제{viol_forced:,}/기타{viol_other:,})  지연 {avg_delay:.3f}h")

        grp_n = {"France": 0, "California": 0, "나머지 6개": 0}
        grp_kg = {"France": 0.0, "California": 0.0, "나머지 6개": 0.0}
        for v in records:
            g = _region_group(v["region"])
            grp_n[g] += 1
            grp_kg[g] += v["carbon_emitted"] / 1000.0
        for g in ("France", "California", "나머지 6개"):
            region_rows.append(dict(level=level, capacity=cap, group=g,
                                    n_jobs=grp_n[g], carbon_kg=grp_kg[g]))
        ca_n_by_level[level] = grp_n["California"]
        print(f"         France n={grp_n['France']:>6,} {grp_kg['France']:>9,.1f}kg | "
              f"California n={grp_n['California']:>6,} {grp_kg['California']:>9,.1f}kg | "
              f"나머지6개 n={grp_n['나머지 6개']:>6,} {grp_kg['나머지 6개']:>9,.1f}kg")

    out_dir = os.path.join(_HERE, "data", "capacity_sweep_abs")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "sweep_b4_recompute_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(main_rows[0].keys()))
        w.writeheader()
        for r in main_rows:
            w.writerow(r)
    with open(os.path.join(out_dir, "sweep_b4_region_breakdown.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(region_rows[0].keys()))
        w.writeheader()
        for r in region_rows:
            w.writerow(r)

    # cap 오름차순(0.5x -> inf)으로 California 배정 수가 단조증가하는가
    order = sorted(SWEEP_LEVELS_B4, key=lambda lv: SWEEP_LEVEL_CAP[lv])
    ca_series = [ca_n_by_level[lv] for lv in order]
    monotone = all(ca_series[i] <= ca_series[i + 1] for i in range(len(ca_series) - 1))
    print(f"\n  포화 순서 서사 검증: cap 오름차순({order}) California 배정 수 = {ca_series}")
    print(f"  단조증가(=용량이 늘수록 California로 더 몰림)? {monotone}")
    print(f"  저장: {out_dir}/sweep_b4_recompute_summary.csv, sweep_b4_region_breakdown.csv")

    return main_rows, region_rows


def k1_savings_share(jobs=None, data=None):
    """문단594 검증 — k=1 등급이 시간 이동이 만든 절감의 95.85%를 차지하는지.
    savings_j = 공간이동만(비교군②, mode=carbon_lb_immediate) 배출 − 온라인(cap=12,
    B4의 1x 레벨) 배출. job_id로 매칭해 k별로 합산한다."""
    jobs = jobs or _load_jobs()
    data = data or _load_carbon_2025()

    horizon_hours = max(j["deadline"] for j in jobs) + 24
    total_hours = int(horizon_hours) + 48
    carbon_series, _ = carbon_forecast.load_actual_series(total_hours)

    res_spatial = simulator.run_simulation(jobs, carbon_series, "carbon_lb_immediate")
    spatial_by_id = {r["job_id"]: r["carbon_emitted"] for r in res_spatial}

    records = _load_sweep_level("1x")
    savings_by_k, total_savings = {}, 0.0
    for v in records:
        s = spatial_by_id[v["job_id"]] - v["carbon_emitted"]
        savings_by_k[v["k"]] = savings_by_k.get(v["k"], 0.0) + s
        total_savings += s

    print("\n[문단594 검증] k별 절감 기여 (공간이동만 대비, cap=12/B4 1x)")
    for k in sorted(savings_by_k):
        pct = 100 * savings_by_k[k] / total_savings if total_savings else 0.0
        print(f"  k={k}: {savings_by_k[k]/1000:>10,.1f} kg  ({pct:6.2f}%)")
    k1_pct = 100 * savings_by_k.get(1, 0.0) / total_savings if total_savings else 0.0
    print(f"  총 절감: {total_savings/1000:,.1f} kg")
    print(f"  k=1 비중: {k1_pct:.2f}%  (문단594 주장: 95.85%) -> "
          f"{'일치' if abs(k1_pct - 95.85) < 1 else '불일치'}")
    return savings_by_k, total_savings


def capacity_check_598_600(jobs=None, data=None):
    """문단598·600 검증 — cap=12(B4 1x) 기준.
    598: 프랑스·캘리포니아를 뺀 나머지 리전의 초과시간이 31시간 이하인지.
    600: 캘리포니아 초과 구간(concurrency>cap인 연속시각 구간)의 시간을
    hour-of-day(UTC, 0~23)로 쪼개, 19~21시대 비중이 77.7%에 맞는지."""
    records = _load_sweep_level("1x")
    regions = sorted(set(v["region"] for v in records))

    print("\n[문단598 검증] 리전별 초과시간(hours_over), cap=12")
    hours_over = {}
    for r in regions:
        peak, over, _ = _region_sweep(records, r, CAP)
        hours_over[r] = over
        flag = "  <- FR/CAL 제외 대상" if r not in ("FR", "US-CAL-CISO") else ""
        print(f"  {r:15} peak={peak:>3}  초과 {over:>8.2f}h{flag}")
    others = {r: h for r, h in hours_over.items() if r not in ("FR", "US-CAL-CISO")}
    others_max = max(others.values()) if others else 0.0
    print(f"  FR/CAL 제외 최댓값: {others_max:.2f}h  (문단598 주장: 31시간 이하) -> "
          f"{'통과' if others_max <= 31 else '실패'}")

    _, _, cal_over_spans = _region_sweep(records, "US-CAL-CISO", CAP)
    hour_bins = {h: 0.0 for h in range(24)}
    for t0, t1 in cal_over_spans:
        t = t0
        while t < t1:
            h = int(t) % 24
            seg_end = min(t1, int(t) + 1)
            hour_bins[h] += seg_end - t
            t = seg_end
    total_over_h = sum(hour_bins.values())

    print("\n[문단600 검증] 캘리포니아 초과시간 hour-of-day 분포 (UTC)")
    for h in range(24):
        if hour_bins[h] > 0.01:
            print(f"  {h:>2}시: {hour_bins[h]:>7.2f}h")
    for label, hs in [("19~20시(2시간)", (19, 20)), ("19~21시(3시간)", (19, 20, 21))]:
        s = sum(hour_bins[h] for h in hs)
        pct = 100 * s / total_over_h if total_over_h else 0.0
        print(f"  {label} 비중: {pct:.2f}%  (문단600 주장: 77.7%) -> "
              f"{'일치' if abs(pct - 77.7) < 2 else '불일치'}")

    return hours_over, hour_bins


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
    ap.add_argument("--sensitivity", action="store_true", help="E5 민감도 실험 3종도 재생성 (수 분)")
    args = ap.parse_args()

    print("job/탄소 데이터 로딩...")
    jobs = _load_jobs()
    data = _load_carbon_2025()
    print(f"  job {len(jobs):,}개")

    table2(jobs, data)
    table_b7(jobs, data)
    oracle_b6(jobs, data)
    capacity_sweep(jobs, data, full=args.full)
    if args.sensitivity:
        sensitivity(jobs, data)
    if args.figures:
        figures()


if __name__ == "__main__":
    main()
