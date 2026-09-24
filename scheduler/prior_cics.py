# -*- coding: utf-8 -*-
"""CICS (Google) 의 Virtual Capacity Curve 를 **원문 식 그대로** 우리 데이터에 적용.

출처: Radovanovic et al., "Carbon-Aware Computing for Datacenters," IEEE TPS.
      paper/참고/carbon-aware-computing.pdf, §III-C 식 (4) 및 그 뒤 제약식.

원문에서 그대로 옮긴 것
----------------------
목적함수 (4):
    min_{δ,y}  λe · Σ_{c,h} η(c,h)·( Pow(c)(Û_nom(h)) + π(c)(Û_nom(h))·δ(c,h)·τ_U(d)/24 )
               + λp · Σ_c y(c,d)
  · η(c,h)   : 클러스터 c 의 h 시각 탄소집약도
  · δ(c,h)   : 시간별 유연 부하의 **평균 대비 편차** (결정변수, n×24 행렬)
  · τ_U(d)/24: 그 날 유연 컴퓨트 총량의 시간 평균
  · y(c,d)   : 클러스터 c 의 일일 첨두 전력 상한 (결정변수)
  · λe, λp   : 탄소 비용($/kg), 첨두 전력 비용($/MW/day)

일일 보존 제약:
    Σ_h δ(c,h) = 0,  ∀c
  → "VCCs impose hourly limits ... **while preserving overall daily capacity**,
     enabling all such workloads to complete within a day." (원문 초록)
  즉 하루 총량은 그대로 두고 **시간별로 모양만 바꾼다**. 이게 CICS의 핵심이고,
  CAST 의 Algorithm 1(작업별 마감 기한까지 슬롯 단위 롤링)과 구조가 다른 지점이다.

전력 상한(확률 제약):
    P[ U_IF(c,h) + (1+δ(c,h))·τ_U(d)/24 ≥ Ū_pow(c) ] ≤ γ

우리 데이터로 옮기며 내린 판단 (전부 명시)
--------------------------------------
1. Pow(c)(Û_nom(h)) 항은 δ 와 무관하므로 최적화에서 상수다 — 제거해도 해가 같다.
   π(c)(·) 는 전력 민감도 계수인데 우리 회계는 작업당 고정 전력(§5.7)이라
   리전·시각에 무관한 상수다. 따라서 탄소 항은 Σ_h η(c,h)·δ(c,h) 에 비례한다.
2. CICS 는 CPU 사용량(CPU-hour)을 다루고 우리는 개별 배치 작업을 다룬다.
   그 날 그 리전의 유연 작업 **건수**를 τ_U 로 놓고, VCC(c,h) 를 "h 시각에
   시작을 허용하는 작업 수 상한"으로 읽는다. Σ_h δ=0 이 곧 "하루 총 허용량 =
   그 날 도착한 작업 수"가 되어 원문의 일일 보존과 정확히 같은 뜻이 된다.
3. 첨두 항 λp·y 는 y ≥ (1+δ(c,h))·τ_U/24 로 선형화한다(원문 y 정의 그대로).
   λp/λe 비를 모르므로 **스윕**한다 — 하나를 임의로 고르면 재현 충실도를 공격받는다.
4. CICS 는 리전 간 이동을 하지 않는다(§II-C 확인). 그래서 배정은 **홈 리전 고정**이다.
5. CICS 에는 작업별 마감이 없고 "하루 안에 끝난다"만 있다. 우리 작업에는 마감이
   있으므로, 대기열에서 **마감 임박 순(EDF)** 으로 뽑되 마감을 넘기게 되는 작업은
   VCC 상한을 무시하고 내보낸다. 이 예외를 몇 건 썼는지 따로 보고한다.
"""
import argparse
import math
from collections import defaultdict

import numpy as np
import pulp as plp

from interface.regions import REGIONS

from . import prior_harness as H

HOURS_PER_DAY = 24


def solve_vcc(eta_day, n_flex, lam_ratio, delta_max=1.0):
    """하루치 VCC 를 원문 식 (4)로 푼다.

    eta_day   : (24,) 그 날 그 리전의 시간별 탄소집약도 η(c,h)
    n_flex    : 그 날 그 리전에 도착한 유연 작업 수 (= τ_U(d))
    lam_ratio : λp/λe. 0 이면 첨두 무시(탄소만), 크면 평탄화.
    반환       : (24,) 시간별 허용 작업 수 VCC(c,h) = (1+δ(c,h))·τ_U/24
    """
    avg = n_flex / HOURS_PER_DAY
    if n_flex <= 0:
        return np.zeros(HOURS_PER_DAY)

    m = plp.LpProblem("vcc", plp.LpMinimize)
    d = {h: plp.LpVariable(f"d_{h}", lowBound=-1.0, upBound=delta_max) for h in range(24)}
    y = plp.LpVariable("y", lowBound=0)

    # 일일 보존 제약: Σ_h δ(c,h) = 0
    m += plp.lpSum(d[h] for h in range(24)) == 0, "daily_conservation"

    # 첨두 정의: y ≥ (1+δ(h))·τ_U/24  ∀h
    for h in range(24):
        m += y >= (1 + d[h]) * avg, f"peak_{h}"

    # 목적함수 (4): 탄소항 Σ η(h)·δ(h)·τ/24  +  (λp/λe)·y
    m += plp.lpSum(eta_day[h] * d[h] * avg for h in range(24)) + lam_ratio * y
    m.solve(plp.PULP_CBC_CMD(msg=0))

    return np.array([(1 + d[h].value()) * avg for h in range(24)])


def run(lam_ratio=0.0, delta_max=1.0, verbose=True):
    """CICS 정책을 우리 데이터에 적용하고 harness 규약대로 결정만 반환한다."""
    jobs, actual, pred24, W, lat = H.load_all()

    # 홈 리전 고정 (CICS 는 공간 이동을 하지 않는다)
    by_rd = defaultdict(list)          # (region, day) -> jobs
    for j in jobs:
        day = int(j["submit_time"] // HOURS_PER_DAY)
        by_rd[(j["region"], day)].append(j)

    # 1) 하루 전 최적화로 리전·날짜별 VCC 를 만든다
    vcc = {}
    for (r, day), js in by_rd.items():
        h0 = day * HOURS_PER_DAY
        series = actual[r]
        eta = np.array([series[min(h0 + h, len(series) - 1)] for h in range(24)])
        vcc[(r, day)] = solve_vcc(eta, len(js), lam_ratio, delta_max)

    # 2) VCC 상한 안에서 대기열을 소화한다 (EDF, 마감 임박 작업은 예외 허용)
    decisions, forced = {}, 0
    queues = defaultdict(list)
    arrivals = defaultdict(list)
    for j in jobs:
        arrivals[math.floor(j["submit_time"])].append(j)

    n_hours = int(max(j["deadline"] for j in jobs)) + 2
    for t in range(n_hours + 1):
        for j in arrivals.pop(t, ()):
            queues[j["region"]].append(j)
        day = t // HOURS_PER_DAY
        for r in REGIONS:
            q = queues[r]
            if not q:
                continue
            limit = vcc.get((r, day))
            budget = int(round(limit[t % 24])) if limit is not None else 0
            q.sort(key=lambda j: j["deadline"] - j["duration"])   # EDF
            keep = []
            for j in q:
                start = max(t, j["submit_time"])
                last = j["deadline"] - j["duration"]
                if budget > 0:
                    decisions[j["id"]] = (r, start)
                    budget -= 1
                elif last < t + 1:            # 이번이 마지막 기회 — 상한 무시
                    decisions[j["id"]] = (r, start)
                    forced += 1
                else:
                    keep.append(j)
            queues[r] = keep

    for r, q in queues.items():               # 경계에 남은 잔여
        for j in q:
            decisions[j["id"]] = (r, j["deadline"] - j["duration"])
            forced += 1

    s = H.score(decisions, jobs, W, lat, label=f"CICS VCC (λp/λe={lam_ratio})")
    s["vcc_overrides"] = forced
    if verbose:
        print(f"  λp/λe={lam_ratio:<6} {s['total_carbon_kg']:>10,.1f} kg  "
              f"{(1-s['total_carbon_kg']/29225.6)*100:>6.2f}%  "
              f"용량위반 {s['capacity_violations']:>6,}  마감위반 {s['deadline_misses']:>5,}  "
              f"상한무시 {forced:,}")
    return s, decisions


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    print("CICS Virtual Capacity Curve — 원문 식 (4) + 일일 보존 제약")
    print("기준 ① 29,225.6 kg / CAST ④ 10,805.0 kg (63.03%, 위반 227)\n")
    for lr in ([0.0, 0.5, 1.0, 2.0, 5.0] if a.sweep else [0.0]):
        run(lam_ratio=lr)
