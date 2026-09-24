# -*- coding: utf-8 -*-
"""선행 연구 정책을 **원문 수식·코드 그대로** 구현해 비교하기 위한 공용 하네스.

왜 이 파일이 따로 있나
---------------------
비교표의 모든 행이 **같은 회계** 위에 있어야 한다. 2026-09-24에 실제로 사고가
났다: load_balancer/framework/results/summary.json 의 metrics(그리고 assign_*.csv
의 carbon_g 열)는 baseline 29,182.6 kg 인데, 논문 표1은 29,225.6 kg 이다. 후자는
배정 결과 위에 실측 탄소집약도를 다시 적분한 값이고 전자는 옛 회계다. 선행 정책
구현이 저마다 자기 회계를 들고 오면 이런 불일치가 조용히 표 안으로 들어간다.

그래서 규약은 하나다:
    **구현은 "누가 어느 리전에서 언제 시작하는가"만 결정한다.
      배출량은 전부 이 파일의 score() 가 계산한다.**

score() 는 capacity.py 의 _Windows.actual_mean 을 그대로 쓴다 — 즉 Algorithm 1,
표1, 그리고 모든 선행 정책 재현이 문자 그대로 같은 함수로 채점된다.
"""
import math

import numpy as np

from interface import carbon_2025
from interface.regions import REGIONS, LB_TO_REGION
from load_balancer.framework.config import JOBS_CSV, RESULTS_DIR, load_latency_matrix

from . import capacity, data_loader

CAP = 12          # 유효 상한 K_r = floor(0.8 * cap_r)
ASSIGN_CSV = RESULTS_DIR / "assign_alpha_auto.csv"


# ───────────────────────── 입력 ─────────────────────────
def load_all():
    """(jobs, actual, pred24, W, latency) — 모든 구현이 똑같이 이걸로 시작한다."""
    jobs = data_loader.load_jobs_with_assignment(JOBS_CSV, ASSIGN_CSV)
    data = carbon_2025.load_2025()
    actual, pred24 = data["actual"], data["pred24"]
    W = capacity._Windows(actual, pred24)
    latency = load_latency_matrix()          # 8x8, ms, 행=출발 열=도착
    return jobs, actual, pred24, W, latency


def region_index():
    return {r: i for i, r in enumerate(REGIONS)}


# ───────────────────────── 채점 ─────────────────────────
def score(decisions, jobs, W, latency, cap=CAP, label=""):
    """선행 정책이든 CAST든 **같은 잣대로** 채점한다.

    decisions : {job_id: (region_code, start_hour)}
                region_code 는 interface.regions.REGIONS 의 표준 코드.
    반환       : dict — 총배출(kg), 평균 네트워크 지연(ms), 마감 위반, 용량 위반
    """
    ri = region_index()
    by_id = {j["id"]: j for j in jobs}
    missing = [i for i in by_id if i not in decisions]
    if missing:
        raise ValueError(f"{label}: 결정이 빠진 작업 {len(missing)}건 (예: {missing[:3]})")

    recs, tot_g, lat_sum, miss = {}, 0.0, 0.0, 0
    for jid, (r, start) in decisions.items():
        j = by_id[jid]
        d = j["duration"]
        g = W.actual_mean(r, start, d) * d      # ← 논문 §5.7 식(16) 과 같은 회계
        tot_g += g
        home = j["region"]
        lat_sum += float(latency[ri[home]][ri[r]])
        if start + d > j["deadline"] + 1e-9:
            miss += 1
        recs[jid] = dict(region=r, scheduled_start=start, duration=d)

    return dict(
        label=label,
        n=len(decisions),
        total_carbon_kg=tot_g / 1000.0,
        avg_latency_ms=lat_sum / len(decisions),
        deadline_misses=miss,
        capacity_violations=_over_cap(recs, cap),
    )


def _over_cap(recs, cap):
    """'상한 위반 배정' 건수 — **정의를 새로 만들지 않는다.**

    §6.4 와 표1 이 쓰는 정의는 capacity._over_cap_admissions 하나뿐이다. 여기서
    같은 걸 다시 구현하면 두 번째 정의가 생기고, 그게 곧 표가 갈라지는 경로다
    (실제로 자체 스윕으로 세어보니 같은 스케줄에서 127 vs 227 로 갈렸다 — 같은
    시각에 시작한 배치가 서로를 '이미 실행 중'으로 보는지에서 갈린다). 그래서
    그 함수를 그대로 호출한다.
    """
    out = {}
    for jid, v in recs.items():
        out[jid] = dict(v)
        out[jid].setdefault("forced", False)
        out[jid].setdefault("immediate", False)
    regions = sorted({v["region"] for v in out.values()})
    return sum(capacity._over_cap_admissions(out, regions, cap))


def baseline_decisions(jobs):
    """① 홈 리전 즉시 실행 — 표1 ①의 정의 그대로. 재현 확인용 기준선."""
    return {j["id"]: (j["region"], j["submit_time"]) for j in jobs}


if __name__ == "__main__":
    jobs, actual, pred24, W, latency = load_all()
    print(f"작업 {len(jobs):,}건, 리전 {len(REGIONS)}개")
    s = score(baseline_decisions(jobs), jobs, W, latency, label="① baseline")
    print(f"{s['label']}: {s['total_carbon_kg']:,.1f} kg, "
          f"지연 {s['avg_latency_ms']:.1f} ms, 마감위반 {s['deadline_misses']}, "
          f"용량위반 {s['capacity_violations']}")
    print("→ 논문 표1 ① = 29,225.6 kg 과 대조할 것")
