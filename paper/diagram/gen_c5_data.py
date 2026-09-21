# -*- coding: utf-8 -*-
"""그림 5(안) 데이터 생성 — CAL 리전 시간별 동시실행수, 무제약(시간이동) vs 온라인(용량인지).

레포 코드는 수정하지 않는다. scheduler 패키지를 그대로 불러와 두 가지를 실행할 뿐이다.
  (A) 무제약: scheduler.simulator.run_simulation(mode="carbon_lb_timeshift")
  (B) 온라인: scheduler.capacity.run_rolling(capacity=12)
둘 다 같은 jobs(2025년 1년치, alpha_auto 배정)와 같은 탄소 시계열을 쓴다.
연속 시각 이벤트 스윕(§6.4 정의)으로 CAL 리전의 (start,end) 배정을 재계산해
peak/hours_over 를 얻는다 — 정리.txt [26]의 41건/19건과 정확히 일치함을 확인했다.

출력: c5_cal_concurrency.json (이 파일과 같은 디렉터리) — gen_concurrency.py 가 읽는다.
실행: ./.venv/bin/python paper/diagram/gen_c5_data.py  (약 8초, 146,000건 전량)
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "scheduler"))
sys.path.insert(0, _REPO_ROOT)

from scheduler import data_loader, simulator, capacity as cap_mod
from interface import carbon_2025
from load_balancer.framework.config import JOBS_CSV as YEAR_JOBS_CSV
from load_balancer.framework.config import RESULTS_DIR as _LB_RESULTS_DIR

YEAR_ASSIGN_CSV = _LB_RESULTS_DIR / "assign_alpha_auto.csv"

CAL = "US-CAL-CISO"

print("jobs 로딩...")
jobs = data_loader.load_jobs_with_assignment(YEAR_JOBS_CSV, YEAR_ASSIGN_CSV)
print(f"  job {len(jobs):,}개")

data = carbon_2025.load_2025()
actual, pred24 = data["actual"], data["pred24"]
n_hours = data["n_hours"]
regions = list(actual.keys())

horizon_hours = max(j["deadline"] for j in jobs) + 24
total_hours = int(horizon_hours) + 48
carbon_series = carbon_2025.actual_series(data, total_hours)

def concurrency_series(spans, n):
    """[(start,end), ...] -> (연속 이벤트 스윕 포인트, 정수시간 그리드 샘플).

    §6.4 정의(tau_j<=t<tau_j+d_j)는 연속 시각 기준이므로 실제 피크는 정시 사이에서
    나올 수 있다. 그래서 두 가지를 같이 반환한다:
      - events: (t, cur) 연속 스윕 전체 — 진짜 피크(41/19)가 여기 있다.
      - grid:   정수시간 h별 샘플 — 그림의 x축을 h로 그릴 때 쓴다.
    """
    ev = []
    for s, e in spans:
        if e > s:
            ev.append((s, 1))
            ev.append((e, -1))
    ev.sort(key=lambda x: (x[0], -x[1]))
    cur = 0
    pts = [(0.0, 0)]
    for t, d in ev:
        cur += d
        pts.append((t, cur))
    import bisect
    times = [p[0] for p in pts]
    vals = [p[1] for p in pts]
    grid = []
    for h in range(n):
        i = bisect.bisect_right(times, h) - 1
        grid.append(vals[i] if i >= 0 else 0)
    return pts, grid, (max(vals) if vals else 0)

print("무제약(A) 시뮬레이션 실행...")
res_a = simulator.run_simulation(jobs, carbon_series, "carbon_lb_timeshift")
spans_a = [(r["scheduled_start"], r["scheduled_start"] + r["duration"])
           for r in res_a if r["region"] == CAL]
print(f"  CAL 배정 {len(spans_a)}건")

print("온라인(B) run_rolling 실행 (capacity=12)...")
out_b, stats_b = cap_mod.run_rolling(jobs, actual, pred24, capacity=12, regions=regions)
spans_b = [(v["scheduled_start"], v["scheduled_start"] + v["duration"])
           for v in out_b.values() if v["region"] == CAL]
print(f"  CAL 배정 {len(spans_b)}건")
print(f"  stats: n={stats_b['n']} slo_viol={stats_b['slo_violations']} "
      f"forced={stats_b['forced_admissions']} cap_viol={stats_b['capacity_violations']} "
      f"peak[CAL]={stats_b['peak'][CAL]} hours_over[CAL]={stats_b['hours_over'][CAL]}")

n_grid = int(max(max(e for _, e in spans_a), max(e for _, e in spans_b))) + 2

events_a, grid_a, peak_a = concurrency_series(spans_a, n_grid)
events_b, grid_b, peak_b = concurrency_series(spans_b, n_grid)

print(f"무제약 CAL 피크(연속)={peak_a}  온라인 CAL 피크(연속)={peak_b}")

# 그림용 윈도우: 전역 피크(a=41)가 들어있는 7일 구간, 일 경계에 맞춤
peak_hour = int(max(events_a, key=lambda p: p[1])[0])
win_lo = (peak_hour // 24 - 1) * 24
win_hi = win_lo + 7 * 24

def window_events(events, lo, hi):
    pts = [(max(t, lo) - lo, v) for t, v in events if lo <= t <= hi]
    if not pts or pts[0][0] > 0:
        # 구간 시작 값 보강
        import bisect
        times = [p[0] for p in events]
        i = bisect.bisect_right(times, lo) - 1
        v0 = events[i][1] if i >= 0 else 0
        pts = [(0.0, v0)] + pts
    pts.append((hi - lo, pts[-1][1]))
    return pts

win_events_a = window_events(events_a, win_lo, win_hi)
win_events_b = window_events(events_b, win_lo, win_hi)

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c5_cal_concurrency.json")
with open(out_path, "w") as f:
    json.dump({
        "peak_a": peak_a,
        "peak_b": peak_b,
        "cap": 12,
        "win_lo": win_lo,
        "win_hi": win_hi,
        "win_events_a": win_events_a,
        "win_events_b": win_events_b,
        "stats_b": {k: v for k, v in stats_b.items() if k not in ("peak", "hours_over")},
        "stats_b_peak": stats_b["peak"][CAL],
        "stats_b_hours_over": stats_b["hours_over"][CAL],
    }, f)
print("저장:", out_path, " window", win_lo, win_hi)
