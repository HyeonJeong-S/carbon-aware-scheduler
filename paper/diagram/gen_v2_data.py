# -*- coding: utf-8 -*-
"""v2 그림 자료 — 실험 결과(scheduler/data/v2/**)에서 v1 그림 스크립트가 읽던 꼴의 JSON 을 만든다.
v1 그림(gen_routing·gen_concurrency·gen_figs_data.fig_scheduler·gen_comparison)의 서식을 그대로 쓰기 위함.

    ./.venv/bin/python paper/diagram/gen_v2_data.py [--main main/joint] [--counter main/ignore] [--alt main/decoupled]

출력(paper/diagram/):
  v2_routing_matrix.json      8×8 출발→실행 리전 건수 (main 실행, 채점 창)         ← gen_routing 의 routing_matrix 자리
  v2_cal_concurrency.json     c5_cal_concurrency.json 꼴: A=counter(용량 무시), B=main, 캘리포니아 피크 주
  v2_fig4_slot_data.json      피크 날의 시각별 실측 탄소·동시 실행(main)·상한            ← fig4_slot_data.json 꼴
  v2_fig4_gantt_data.json     그날 창이 가장 넓은 캘리포니아 작업 9건: main 의 시작 vs counter 의 시작  ← fig4_gantt_data.json 꼴
  v2_comparison_rows.json     막대 그림 행 (이름, kg, 절감률, 종류)
"""
import argparse
import gzip
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from interface import carbon_2025                      # noqa: E402
from interface.regions import REGIONS                  # noqa: E402

V2 = os.path.join(ROOT, "scheduler", "data", "v2")
CAL = "US-CAL-CISO"
SCORE_FROM = 168


def load(name):
    df = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
    st = json.load(open(os.path.join(V2, name, "stats.json")))
    return df, st


def _slot_mean(arr, start, dur):
    """capacity._Windows.actual_mean 과 같은 규약: floor(start) 부터 ceil(dur) 슬롯의 평균."""
    n = len(arr); a = min(max(int(math.floor(start)), 0), n - 1); b = min(a + max(1, int(math.ceil(dur))), n)
    return float(sum(arr[a:b]) / (b - a))


def _pick_highlight(jobs):
    """강조할 작업 하나: 원하던 자리(용량 무시 시작)가 그날 액자 안(0~24h)에 있고, 실제 시작의 탄소가 원하던 자리보다
    가장 많이 높은 작업 — 자료 규칙으로 고른다(손으로 고르지 않음). 없으면 첫 작업."""
    def disjoint(j):   # 원하던 자리와 실제 자리가 겹치지 않아야 점선 상자와 막대가 따로 보인다(첫 판 j_100613 은 0.6h 짜리라 안 보였음)
        a0, a1 = j["tau_unconstrained"], j["tau_unconstrained"] + j["dur"]; b0, b1 = j["tau"], j["tau"] + j["dur"]
        return a1 <= b0 or b1 <= a0
    ok = [j for j in jobs if j["tau_unconstrained"] is not None and 0 <= j["tau_unconstrained"] < 24 and disjoint(j)]
    if not ok:
        return jobs[0]["id"] if jobs else None
    # 10-18(1회차 점검): 본문 회계(실행 시간 동안의 슬롯 평균)로 재면 이날 밀린 작업들의 배출 차는 −10~+4% 로 작아서
    # "추가 배출이 가장 큰 작업" 은 0.6시간짜리 끝자락 작업이 뽑혀 보이지 않았다. 그림의 뜻(상한이 작업을 원하던 자리에서
    # 밀어낸다)에 맞게 "밀린 시간 × 실행 시간" 이 가장 큰 작업을 고른다. 배출 차는 그림에 적지 않는다.
    return max(ok, key=lambda j: j["dur"] * abs(j["tau"] - j["tau_unconstrained"]))["id"]


def events(df, region, lo, hi):
    """[lo, hi) 창의 동시 실행 계단. 같은 순간이면 끝을 먼저 뺀다(τ_j ≤ t < τ_j+d_j; 4.1 위반 정의·summarize 와 같은 규약).
    10-16: '시작 먼저'로 두었더니 CAST 주간 최대가 18 로 찍혀(실제 위반 0) 고쳤다."""
    sub = df[df.region == region]
    ev = sorted([(s, 1) for s in sub.scheduled_start] + [(s + d, -1) for s, d in zip(sub.scheduled_start, sub.duration)],
                key=lambda x: (x[0], x[1]))
    cur, out = 0, []
    for t, d in ev:
        if t >= hi:
            break
        cur += d
        if t >= lo:
            out.append([t - lo, cur])
    # 창 시작 시점 값
    pre = sum(d for t, d in ev if t < lo)
    return [[0.0, pre]] + out


def peak_and_hours(df, region, cap):
    sub = df[df.region == region]
    ev = sorted([(s, 1) for s in sub.scheduled_start] + [(s + d, -1) for s, d in zip(sub.scheduled_start, sub.duration)],
                key=lambda x: (x[0], x[1]))
    cur = mx = 0; over = 0.0; prev = None
    for t, d in ev:
        if prev is not None and cur > cap:
            over += t - prev
        cur += d; mx = max(mx, cur); prev = t
    return mx, over


def concurrency_by_hour(df, region, n):
    sub = df[df.region == region]
    occ = np.zeros(n, dtype=int)
    ev = sorted([(s, 1) for s in sub.scheduled_start] + [(s + d, -1) for s, d in zip(sub.scheduled_start, sub.duration)], key=lambda x: (x[0], x[1]))
    cur = 0; j = 0
    for h in range(n):
        while j < len(ev) and ev[j][0] < h + 1:
            if ev[j][0] >= h:
                cur += ev[j][1]; occ[h] = max(occ[h], cur)
            else:
                cur += ev[j][1]
            j += 1
        occ[h] = max(occ[h], cur if h == 0 else occ[h])
    # 간단·보수적: 슬롯 안 최대값
    return occ


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="main/joint")
    ap.add_argument("--counter", default="main/ignore")
    ap.add_argument("--alt", default="main/decoupled")
    args = ap.parse_args(argv)
    actual = carbon_2025.load_2025()["actual"]
    dm, sm = load(args.main)
    cap = sm["scored_cap"][CAL] if isinstance(sm["scored_cap"], dict) else sm["scored_cap"]
    counter_name = args.counter if os.path.exists(os.path.join(V2, args.counter, "stats.json")) else args.alt
    dc, sc = load(counter_name)
    win = dm[dm.submit_time >= SCORE_FROM]

    # 1) 라우팅 행렬
    M = pd.crosstab(win.origin, win.region).reindex(index=REGIONS, columns=REGIONS, fill_value=0).values.tolist()
    json.dump(dict(regions=REGIONS, routing_matrix=M, n=int(win.shape[0]), run=args.main),
              open(os.path.join(HERE, "v2_routing_matrix.json"), "w"), indent=1)

    # 2) 캘리포니아 피크 주 (main 기준 피크가 난 시각이 든 주)
    n_h = 8760
    occ_m = concurrency_by_hour(dm, CAL, n_h + 48)
    # 피크 날 선택: 용량 무시(counter) 실행에서 캘리포니아 동시 실행이 가장 높은 시각 — 결합 실행은 상한에서 잘려 argmax 가 뜻이 없다.
    occ_c = concurrency_by_hour(dc, CAL, n_h + 48)
    h_peak = int(np.argmax(occ_c[SCORE_FROM:n_h]) + SCORE_FROM)
    if occ_c[h_peak] <= cap:          # counter 도 상한에 잘려 있으면(분리형 대역) 강제 편입이 가장 많은 날로
        f = dm[(dm.region == CAL) & dm.forced]
        day_f = (f.scheduled_start // 24).astype(int).value_counts()
        h_peak = int(day_f.idxmax() * 24 + 12) if len(day_f) else h_peak
    week_lo = max(SCORE_FROM, (h_peak // 24 - 3) * 24); week_hi = week_lo + 168
    pa, _ = peak_and_hours(dc, CAL, cap); pb, hb = peak_and_hours(dm, CAL, cap)
    json.dump(dict(peak_a=int(pa), peak_b=int(pb), cap=int(cap), win_lo=week_lo, win_hi=week_hi,
                   win_events_a=events(dc, CAL, week_lo, week_hi), win_events_b=events(dm, CAL, week_lo, week_hi),
                   stats_b=dict(n=int(sm["n"]), total_carbon_kg=sm["total_carbon_kg"], slo_violations=sm["slo_violations"],
                                capacity_violations=sm["capacity_violations"], capacity=int(cap)),
                   stats_b_peak=int(pb), stats_b_hours_over=hb, run_a=counter_name, run_b=args.main, peak_hour=h_peak),
              open(os.path.join(HERE, "v2_cal_concurrency.json"), "w"), indent=1)

    # 3) 피크 날 슬롯 자료 + 간트
    day = h_peak // 24
    d0 = day * 24
    carbon = [float(actual[CAL][h]) for h in range(d0, d0 + 24)]
    occ = [int(occ_m[h]) for h in range(d0, d0 + 24)]
    json.dump(dict(day=day, carbon=carbon, occ=occ, cap=int(cap), run=args.main),
              open(os.path.join(HERE, "v2_fig4_slot_data.json"), "w"), indent=1)
    # 그날 캘리포니아에서 시작했고 창이 넓은 작업 9건 (main), counter 에서 같은 작업의 시작
    dc_idx = dc.set_index("job_id")
    cand = dm[(dm.region == CAL) & (dm.scheduled_start >= d0) & (dm.scheduled_start < d0 + 24) & (dm.delay > 0)].copy()
    cand["window"] = cand.apply(lambda r: (r.submit_time + 0) , axis=1)
    # 창 = 마감 − 실행시간 − 제출 = L_max ; 작업 파일에 L_max 가 없으므로 jobs.csv 에서 가져온다
    jobs_csv = sm["jobs_csv"]
    lm = pd.read_csv(jobs_csv, usecols=["job_name", "L_max"]).set_index("job_name")["L_max"] / 3600.0
    cand["window"] = cand.job_id.map(lm)
    cand = cand.sort_values("window", ascending=False).head(9)
    jobs = []
    for r in cand.itertuples():
        tau_c = float(dc_idx.loc[r.job_id, "scheduled_start"]) if r.job_id in dc_idx.index else None
        jobs.append(dict(id=r.job_id, s=round(r.submit_time - d0, 4), tau=round(r.scheduled_start - d0, 4), dur=round(r.duration, 4),
                         D=round(r.submit_time + r.window + r.duration - d0, 4), window=round(r.window, 4), forced=bool(r.forced), k=int(r.k),
                         tau_unconstrained=(round(tau_c - d0, 4) if tau_c is not None else None),
                         # 10-18(1회차 점검): 시작 한 시간의 강도가 아니라 본문 회계(식 (14), capacity._Windows.actual_mean)와 같은
                         # "실행 시간 동안의 슬롯 평균" 으로 — 시작 시각 강도로 잰 +7.5% 는 회계로는 0% 였다.
                         rate_actual=_slot_mean(actual[CAL], r.scheduled_start, r.duration),
                         rate_unconstrained=(_slot_mean(actual[CAL], tau_c, r.duration) if tau_c is not None else None)))
    json.dump(dict(day=day, region=CAL, window_threshold_h=float(cand.window.min()) if len(cand) else 0.0, frame_x_lo=-0.8,
                   highlight_id=_pick_highlight(jobs), jobs=jobs, run=args.main, counter=counter_name),
              open(os.path.join(HERE, "v2_fig4_gantt_data.json"), "w"), indent=1)

    # 4) 막대 그림 행
    rows = []
    def add(name, label, kind):
        p = os.path.join(V2, name, "stats.json")
        if os.path.exists(p):
            s = json.load(open(p)); rows.append([label, round(s["total_carbon_kg"], 1), round(s["savings_pct"], 2), kind])
    rows.append(["Baseline", round(sm["baseline_kg"], 1), None, "ok"])
    add("main/time_only", "Temporal-only", "ok"); add("main/spatial_only", "Spatial-only", "ok")
    add("main/decoupled", "Decoupled", "ok"); add("main/joint", "CAST (knee)", "ours"); add("main/joint_a1", "CAST (α=1)", "ours")
    add("main/ignore", "Capacity ignored", "unreach")
    json.dump(rows, open(os.path.join(HERE, "v2_comparison_rows.json"), "w"), indent=1)
    print(f"피크 시각 h={h_peak} (day {day}), CAL 피크 main {pb} / counter({counter_name}) {pa}, 주 {week_lo}~{week_hi}; 간트 {len(jobs)}건; 막대 {len(rows)}행")


if __name__ == "__main__":
    main()
