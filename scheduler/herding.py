# -*- coding: utf-8 -*-
"""쏠림(herding) 지표 — 작업별 결과(out dict 또는 DataFrame)와 실측 탄소에서 계산.

주 지표   dip_occ_mean / dip_occ_p90 : 리전-일마다 실측 탄소가 가장 낮은 1시간의 최대 동시 실행
          dip_full_share             : 그 시각에 동시 실행이 상한 이상인 리전-일 비율
보조 지표 bottom3_start_share        : 미룬 작업 중 그날 탄소 하위 3시각에 시작한 비율
          hours_at_or_over_cap       : 동시 실행이 상한 이상인 리전-시각 수
용량이 켜진 실행은 상한에서 잘리므로 용량 ∞ 실행에서 재야 쏠림 자체가 보인다(통계 감사 2026-10-16).
"""
import math

import numpy as np


def concurrency_per_hour(recs, region, n_hours):
    """시각별 최대 동시 실행(정수 슬롯 안의 최댓값). 동시각이면 종료 먼저."""
    ev = []
    for v in recs:
        if v["region"] != region:
            continue
        ev.append((v["scheduled_start"], 1))
        ev.append((v["scheduled_start"] + v["duration"], -1))
    ev.sort(key=lambda x: (x[0], x[1]))
    mx = np.zeros(n_hours, dtype=int)
    cur = 0
    for t, d in ev:
        cur += d
        h = int(math.floor(t))
        if 0 <= h < n_hours and cur > mx[h]:
            mx[h] = cur
    # 슬롯 안에 이벤트가 없는 구간은 직전 값이 이어진다
    cur = 0
    i = 0
    ev_h = [(int(math.floor(t)), d) for t, d in ev]
    carried = np.zeros(n_hours, dtype=int)
    j = 0
    for h in range(n_hours):
        while j < len(ev_h) and ev_h[j][0] < h:
            cur += ev_h[j][1]; j += 1
        carried[h] = cur
    return np.maximum(mx, carried)


def herding(recs, actual, regions, cap, t_lo, t_hi):
    """cap 은 정수 또는 {리전: 정수}."""
    recs = list(recs)
    cap_d = cap if isinstance(cap, dict) else {r: cap for r in regions}
    n_hours = int(math.ceil(max(v["scheduled_start"] + v["duration"] for v in recs))) + 1
    delayed = [v for v in recs if v["delay"] > 1e-9]
    cnt = {}
    for v in delayed:
        key = (v["region"], int(math.floor(v["scheduled_start"])))
        cnt[key] = cnt.get(key, 0) + 1
    dip_occ, dip_full, b3_num, b3_den, hours_cap = [], 0, 0, 0, 0
    for r in regions:
        cap = cap_d[r]
        mx = concurrency_per_hour(recs, r, n_hours)
        hours_cap += int((mx[t_lo:t_hi] >= cap).sum())
        a = actual[r]
        for d0 in range(t_lo, min(t_hi, len(a)) - 23, 24):
            day = a[d0:d0 + 24]
            h_min = d0 + int(np.argmin(day))
            dip_occ.append(int(mx[h_min]) if h_min < n_hours else 0)
            dip_full += int(h_min < n_hours and mx[h_min] >= cap)
            order = d0 + np.argsort(day)[:3]
            b3_num += sum(cnt.get((r, int(h)), 0) for h in order)
            b3_den += sum(cnt.get((r, h), 0) for h in range(d0, d0 + 24))
    return dict(
        n=len(recs), n_delayed=len(delayed),
        dip_occ_mean=float(np.mean(dip_occ)) if dip_occ else 0.0,
        dip_occ_p90=float(np.percentile(dip_occ, 90)) if dip_occ else 0.0,
        dip_full_share=dip_full / len(dip_occ) if dip_occ else 0.0,
        bottom3_start_share=(b3_num / b3_den) if b3_den else float("nan"),
        hours_at_or_over_cap=hours_cap,
    )
