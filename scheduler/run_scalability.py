"""작업 수 확장성 — 공간 이동 ILP의 슬롯당 계산시간을 0.5x/1x/2x 에서 잰다.

2026-10-12 교수님 지적 6("온라인 정책을 주장하려면 슬롯당 평균·최대 계산시간과
작업 수 증가에 따른 확장성 결과가 필요합니다")에 답하기 위한 측정이다.
새 실험 설계가 아니라 이미 있는 파이프라인을 세 규모로 다시 돌리며 시간을 잰다.

** 설계에서 조심한 것 두 가지 **
 1. 용량을 고정한다. SimConfig.capacity 가 None 이면 auto_capacity() 가 그 작업
    집합의 baseline 최대 동시실행에서 용량을 다시 뽑는다 — 그러면 규모를 바꿀 때
    작업 수와 용량이 **함께** 변해 "작업 수가 늘면 어떻게 되는가"를 못 잰다.
    세 규모 모두 capacity=16(여유율 0.8 → 유효 상한 12)으로 박는다. 논문 값이다.
 2. 측정 창을 90일로 둔다. 1년 전체를 세 번 돌리면 몇 시간이 걸리는데, 슬롯당
    시간은 그 슬롯의 배치 크기에서 나오는 양이라 창 길이와 무관하다. 앞 7일은
    용량 점유가 정상 상태에 이르기 전이라 통계에서 뺀다. 연간 합계는 외삽이며
    (원래 보고된 "연 25분"도 외삽이었다) 그렇게 밝힌다.

정본 코드는 건드리지 않는다 — knee_slot_alpha 와 assign_slot 을 감싸 시간만 센다.

출력: scheduler/data/scalability/summary.json
사용법: python -m scheduler.run_scalability
"""
import json
import os
import random
import time

import numpy as np
import pandas as pd

from load_balancer.framework import simulator as sim
from load_balancer.framework.config import JOBS_CSV, load_latency_matrix
from load_balancer.framework.simulator import CarbonSeries, SimConfig, run_sim
from scheduler import capacity, reproduce as R

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "scalability")
FACTORS = [("0.5x", 0.5), ("1x", 1.0), ("2x", 2.0)]
SEED = 42
WINDOW_D = 90          # 측정 창(일)
WARMUP_D = 7           # 통계에서 빼는 앞 구간(일)
NOMINAL_CAP = 16       # 여유율 0.8 → 유효 상한 12 (논문 값), 전 규모 공통
SLOTS_PER_YEAR = 8760


def scale_df(jobs: pd.DataFrame, factor: float) -> pd.DataFrame:
    """reproduce._scale_jobs 와 같은 규약 — 0.5x 는 무작위 다운샘플, 2x 는 통짜 복제."""
    if factor == 1.0:
        out = jobs.copy()
    elif factor < 1.0:
        out = jobs.sample(n=round(len(jobs) * factor), random_state=SEED)
    else:
        parts = []
        for i in range(int(factor)):
            c = jobs.copy()
            c["job_name"] = c["job_name"] + f"_x{i}"
            parts.append(c)
        out = pd.concat(parts, ignore_index=True)
    return out.sort_values("submit_time").reset_index(drop=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    jobs_df = pd.read_csv(JOBS_CSV)
    latency = load_latency_matrix()
    carbon = CarbonSeries()
    jobs_sched = R._load_jobs()
    data = R._load_carbon_2025()
    actual, pred24 = data["actual"], data["pred24"]
    rng = random.Random(SEED)

    rows = []
    for label, factor in FACTORS:
        print(f"\n{'='*66}\n[{label}] 규모 {factor}배 · 용량 고정 {NOMINAL_CAP}(유효 12) · 창 {WINDOW_D}일\n{'='*66}",
              flush=True)

        sj = scale_df(jobs_df, factor)
        sj = sj[sj.submit_time < WINDOW_D * 86400.0].reset_index(drop=True)
        print(f"  창 안 작업 {len(sj):,}건 ({len(sj)/(WINDOW_D*24):.1f}건/슬롯) · ILP 시작…", flush=True)

        times, sizes, shortcuts, ilps = [], [], [0], [0]
        knee0, assign0 = sim.knee_slot_alpha, sim.assign_slot

        def timed_knee(batch, *a, **k):
            t0 = time.perf_counter()
            r = knee0(batch, *a, **k)
            times.append(time.perf_counter() - t0)
            sizes.append(len(batch))
            return r

        def timed_assign(batch, m_t, l_t, avail, cfg, blocked, alpha=None):
            if len(batch) <= int(np.min(avail)):
                shortcuts[0] += 1
            else:
                ilps[0] += 1
            return assign0(batch, m_t, l_t, avail, cfg, blocked, alpha)

        sim.knee_slot_alpha, sim.assign_slot = timed_knee, timed_assign
        t0 = time.time()
        try:
            out = run_sim(sj, carbon, latency,
                          SimConfig(adaptive_alpha=True, capacity=NOMINAL_CAP, label="α=auto"),
                          mode="ilp")
        finally:
            sim.knee_slot_alpha, sim.assign_slot = knee0, assign0
        wall = time.time() - t0

        ms = np.array(times) * 1000.0
        keep = ms[WARMUP_D * 24:]              # 앞 7일 제외
        tot = shortcuts[0] + ilps[0]
        print(f"  슬롯 {len(ms):,}개(통계 {len(keep):,}개) · 평균 {keep.mean():.1f} ms · "
              f"중앙 {np.median(keep):.1f} · p95 {np.percentile(keep,95):.1f} · 최악 {keep.max():.1f}",
              flush=True)
        print(f"  배치 평균 {np.mean(sizes):.1f}건 · 그리디 지름길 {100*shortcuts[0]/tot:.1f}% "
              f"· ILP 호출 {ilps[0]:,}회 · 벽시계 {wall/60:.1f}분", flush=True)

        sjs = R._scale_jobs(jobs_sched, factor, rng)
        t0 = time.time()
        _, st = capacity.run_rolling(sjs, actual, pred24, capacity=R.CAP, regions=R.REGIONS)
        shift = time.time() - t0
        print(f"  시간 이동: {len(sjs):,}건 전체 {shift:.1f}초", flush=True)

        rows.append(dict(
            label=label, factor=factor, window_days=WINDOW_D, warmup_days=WARMUP_D,
            n_jobs_window=int(len(sj)), jobs_per_slot=len(sj)/(WINDOW_D*24),
            n_slots=int(len(ms)), n_slots_stat=int(len(keep)),
            slot_mean_ms=float(keep.mean()), slot_median_ms=float(np.median(keep)),
            slot_p95_ms=float(np.percentile(keep, 95)), slot_max_ms=float(keep.max()),
            batch_mean=float(np.mean(sizes)),
            shortcut_pct=100*shortcuts[0]/tot, ilp_calls=ilps[0],
            wall_min=wall/60.0,
            year_extrap_min=float(keep.mean())*SLOTS_PER_YEAR/1000.0/60.0,
            timeshift_n=len(sjs), timeshift_s=shift,
            carbon_kg=float(out["metrics"]["total_carbon_kg"]),
        ))
        json.dump(rows, open(os.path.join(OUT_DIR, "summary.json"), "w"),
                  ensure_ascii=False, indent=1)

    print(f"\n{'='*66}\n확장성 요약 (용량 고정, 창 {WINDOW_D}일, 앞 {WARMUP_D}일 제외)\n{'='*66}")
    print(f"{'규모':<6}{'건/슬롯':>9}{'평균ms':>9}{'p95':>8}{'최악':>9}{'지름길%':>9}{'연외삽분':>10}{'시간이동초':>11}")
    for r in rows:
        print(f"{r['label']:<6}{r['jobs_per_slot']:>9.1f}{r['slot_mean_ms']:>9.1f}"
              f"{r['slot_p95_ms']:>8.1f}{r['slot_max_ms']:>9.1f}{r['shortcut_pct']:>9.1f}"
              f"{r['year_extrap_min']:>10.1f}{r['timeshift_s']:>11.1f}")
    print(f"\n저장: {OUT_DIR}/summary.json")


if __name__ == "__main__":
    main()
