# -*- coding: utf-8 -*-
"""CASPER의 공식 MILP(Carbon Aware Provisioner, CAP)를 원문 그대로 재구현.

원문 확인 위치(2026-09-24, 0c/fd 직접 읽음):
    .../prior/casper/CAP/milp_scheduler.py 의 Carbon.schedule_servers
    .../prior/casper/CAP/config.py

**원문 그대로 확인한 사실 (개념 유비 아님, 코드 직접 대조):**
- 목적함수: alpha*max_obj_1*Σ_ij x_ij*C_j + (1-alpha)*max_obj_2*Σ_i s_i
  (탄소 vs "서버 대수" — 탄소 vs 지연이 아니다. 지연은 목적함수에 없다.)
- alpha=0.9 는 Carbon.schedule_servers(진짜 CAP, docstring:
  "This is the Carbon Aware Provisioner (CAP)") 안에 하드코딩돼 있다.
  alpha=0.5 는 **다른 클래스** Latency.schedule_servers 안에 있는데, 그
  docstring은 "latency greedy scheduler **to compare with** the Carbon
  Aware Scheduler"라고 스스로 밝힌다 — 즉 CAP이 아니라 비교용 베이스라인.
  config.py의 SCHEDULER="carbon" 기본값도 Carbon(alpha=0.9) 쪽을 가리킨다.
  → CAP의 alpha는 0.9다. 0.5는 CAP이 아닌 별개 정책의 값이다.
- 지연은 목적함수가 아니라 하드 제약: x_ij*(latency[i][j]-MAX_LATENCY) <= 0
  (MAX_LATENCY=500ms, config.py)
- 용량: Σ_i x_ij <= s_j * SERVER_CAPACITY(=10), 서버 상한 s_j<=100(변수
  upBound), 전체 서버 상한 Σs_i <= MAX_SERVERS_PER_REGION(100)*n_regions
- 수요: Σ_j x_ij = request_rates[i] (전량 배정 — 미배정/드롭 변수 없음)

**우리 데이터로 옮기며 내린 판단(요청대로 전부 기록):**
1. request_rates[i] = 그 시간(정수 시간 버킷)에 리전 i에서 **제출된 작업
   건수**. CASPER 원문이 "requests/hour"를 다루므로 이게 가장 직접적인
   매핑이다. 다른 매핑(예: 동시 실행 중인 작업 수)은 CASPER의 "매 시간
   새로 도착하는 요청을 그 시간에 배정"이라는 원문 의미와 안 맞아서 안 씀.
2. capacities[j] = SERVER_CAPACITY = 10 그대로, MAX_SERVERS_PER_REGION = 100
   그대로 — 우리 유효 상한 12와 절대 맞추지 않았다(맞추면 그건 CASPER가
   아니라 CASPER 흉내낸 우리 시스템이 된다). 그 결과 전체 용량 상한이
   100*10*8=8,000/시간인데 시간당 평균 작업 수는 146,000/8,760≈16.7건이라
   용량 제약은 사실상 전 구간에서 느슨하다 — 이것도 결과로 그대로 보고한다.
3. CASPER는 시간 이동을 하지 않는다 — 실행 시각은 항상 submit_time이다.
4. carbon_intensities[j] = 그 시간의 **실측** 탄소집약도. CASPER 원문
   (MilpScheduler.compute_carbon_intensities)도 예측이 아니라
   "그 시간의" 값을 직접 읽는다 — 원문 자체가 예측 모듈이 없다(전제 자체가
   다르다: CASPER는 웹 요청을 그 순간 즉시 배정하므로 미래를 볼 필요가 없음).
5. 지연 행렬은 latency.ms(원문과 같은 단위), 우리 8개 리전 실측 최댓값이
   244ms로 MAX_LATENCY=500ms보다 항상 작다 — 즉 우리 데이터에서는 CASPER의
   지연 하드 제약이 단 한 번도 실제로 작동(route 차단)하지 않는다. 이건
   우리가 뭘 잘못 옮겨서가 아니라 원문 절대값(500ms)을 그대로 쓴 결과이며,
   그대로 보고한다.
6. 같은 (origin, hour) 배치 안에서 어느 특정 job이 어느 목적지로 가는지는
   CASPER 자신의 정식화에도 없는 정보다 — CAP은 "요청 수"만 다루고 개별
   요청의 duration을 모델에 넣지 않는다(우리 작업엔 duration이 있지만
   CASPER 목적함수엔 등장하지 않음). 그래서 같은 배치 안에서는 주어진 순서
   그대로 목적지 카운트에 채워 넣는다 — 이는 임의 선택이지만 CASPER
   자신의 수식도 이 선택에 무차별하므로(목적함수 값 자체가 안 바뀜)
   왜곡이 아니다. 다만 우리 채점(§5.7 식16)은 duration에 민감하므로,
   배치 안 job 순서를 바꾸면 총배출 소수점 단위가 흔들릴 수 있다는 점은
   밝혀둔다(배치당 최대 십여 건 수준이라 총합 영향은 미미할 것으로 본다).

채점은 절대 여기서 하지 않는다 — scheduler.prior_harness.score()에 넘긴다.

실행: ./.venv/bin/python -m scheduler.prior_casper [--alpha 0.9] [--hours N]
"""
import argparse
import math
import time

import pulp as plp

from interface.regions import REGIONS

from . import prior_harness as H

MAX_LATENCY = 500.0          # ms, CASPER CAP/config.py Config.MAX_LATENCY
MAX_SERVERS_PER_REGION = 100  # Config.MAX_SERVERS_PER_REGION
SERVER_CAPACITY = 10          # Config.SERVER_CAPACITY
ALPHA_CAP = 0.9                # Carbon.schedule_servers (진짜 CAP)
ALPHA_LATENCY_BASELINE = 0.5   # Latency.schedule_servers (비교용, 참고 실행)


def _bucket_by_hour(jobs):
    buckets = {}
    for j in jobs:
        h = int(math.floor(j["submit_time"]))
        buckets.setdefault(h, []).append(j)
    return buckets


def _solve_hour(carbon_intensities, latency, request_rates, alpha, n_regions):
    """CASPER CAP/milp_scheduler.py::Carbon.schedule_servers 원문 그대로.

    변수·제약 이름까지 원문 대응관계를 알아볼 수 있게 맞췄다. alpha만 인자로
    뺐다(원문은 0.9로 하드코딩).
    """
    opt_model = plp.LpProblem(name="model")
    max_carbon_intensities = max(carbon_intensities)
    max_servers = MAX_SERVERS_PER_REGION * n_regions
    total_req = sum(request_rates)
    max_obj_1 = 1 / (max_carbon_intensities * total_req) if total_req > 0 else 1.0
    max_obj_2 = 1 / max_servers

    set_R = range(n_regions)
    x_vars = {
        (i, j): plp.LpVariable(cat=plp.LpInteger, lowBound=0, name=f"x_{i}_{j}")
        for i in set_R for j in set_R
    }
    s_vars = {
        i: plp.LpVariable(cat=plp.LpInteger, lowBound=0, upBound=MAX_SERVERS_PER_REGION, name=f"s_{i}")
        for i in set_R
    }

    opt_model.addConstraint(
        plp.LpConstraint(e=plp.lpSum(s_vars[i] for i in set_R), sense=plp.LpConstraintLE,
                          rhs=max_servers, name="max_server"))

    for j in set_R:
        opt_model.addConstraint(
            plp.LpConstraint(e=plp.lpSum(x_vars[i, j] for i in set_R) - s_vars[j] * SERVER_CAPACITY,
                              sense=plp.LpConstraintLE, rhs=0, name=f"capacity_const{j}"))

    for i in set_R:
        opt_model.addConstraint(
            plp.LpConstraint(e=plp.lpSum(x_vars[i, j] for j in set_R), sense=plp.LpConstraintEQ,
                              rhs=request_rates[i], name=f"sched_all_reqs_const{i}"))

    for i in set_R:
        for j in set_R:
            opt_model.addConstraint(
                plp.LpConstraint(e=x_vars[i, j] * (latency[i][j] - MAX_LATENCY),
                                  sense=plp.LpConstraintLE, rhs=0, name=f"latency_const{i}_{j}"))

    objective = (alpha * max_obj_1 * plp.lpSum(x_vars[i, j] * carbon_intensities[j]
                                                for i in set_R for j in set_R)
                 + (1 - alpha) * max_obj_2 * plp.lpSum(s_vars[i] for i in set_R))
    opt_model.setObjective(objective)
    opt_model.solve(plp.PULP_CBC_CMD(msg=False))

    if opt_model.sol_status not in (1,):
        raise RuntimeError(f"CASPER MILP infeasible/미해결 (request_rates={request_rates})")

    return {(i, j): int(round(x_vars[i, j].varValue or 0)) for i in set_R for j in set_R}


def _solve_hour_latency_baseline(latency, request_rates, alpha, n_regions):
    """CASPER CAP/milp_scheduler.py::Latency.schedule_servers 원문 그대로.

    **처음 구현에서 실수했던 부분** — 이건 Carbon.schedule_servers에 alpha만
    0.5로 바꾼 게 아니다. 목적함수의 1항 자체가 carbon_intensities[j]가 아니라
    latencies[i][j]다(탄소를 아예 안 본다, 원문의 "latency greedy scheduler
    **to compare with** the Carbon Aware Scheduler" — 비교용 비-탄소 정책).
    이 함수를 따로 만들어 고쳤다.
    """
    opt_model = plp.LpProblem("model", plp.LpMinimize)
    max_latency_per_region = [max(row) for row in latency]
    max_servers = MAX_SERVERS_PER_REGION * n_regions
    max_obj_1 = 1 / sum(i * j for i, j in zip(request_rates, max_latency_per_region)) \
        if sum(i * j for i, j in zip(request_rates, max_latency_per_region)) > 0 else 1.0
    max_obj_2 = 1 / max_servers

    set_R = range(n_regions)
    x_vars = {
        (i, j): plp.LpVariable(cat=plp.LpInteger, lowBound=0, name=f"x_{i}_{j}")
        for i in set_R for j in set_R
    }
    s_vars = {
        i: plp.LpVariable(cat=plp.LpInteger, lowBound=0, upBound=MAX_SERVERS_PER_REGION, name=f"s_{i}")
        for i in set_R
    }

    opt_model.addConstraint(
        plp.LpConstraint(e=plp.lpSum(s_vars[i] for i in set_R), sense=plp.LpConstraintLE,
                          rhs=max_servers, name="max_server"))
    for j in set_R:
        opt_model.addConstraint(
            plp.LpConstraint(e=plp.lpSum(x_vars[i, j] for i in set_R) - s_vars[j] * SERVER_CAPACITY,
                              sense=plp.LpConstraintLE, rhs=0, name=f"capacity_const{j}"))
    for i in set_R:
        opt_model.addConstraint(
            plp.LpConstraint(e=plp.lpSum(x_vars[i, j] for j in set_R), sense=plp.LpConstraintEQ,
                              rhs=request_rates[i], name=f"sched_all_reqs_const{i}"))
    # 원문(Latency.schedule_servers)엔 latency 하드 제약이 없다 — latency가 이미
    # 목적함수 자체이기 때문. Carbon.schedule_servers와의 유일한 구조적 차이.

    objective = (alpha * max_obj_1 * plp.lpSum(latency[i][j] * x_vars[i, j] for i in set_R for j in set_R)
                 + (1 - alpha) * max_obj_2 * plp.lpSum(s_vars[i] for i in set_R))
    opt_model.setObjective(objective)
    opt_model.solve(plp.PULP_CBC_CMD(msg=False))

    if opt_model.sol_status not in (1,):
        raise RuntimeError(f"CASPER(latency) MILP infeasible/미해결 (request_rates={request_rates})")

    return {(i, j): int(round(x_vars[i, j].varValue or 0)) for i in set_R for j in set_R}


def run_casper(jobs, actual, latency, alpha, regions=REGIONS, max_hours=None, verbose_every=500,
               policy="carbon"):
    """policy: "carbon" -> Carbon.schedule_servers (진짜 CAP, alpha=0.9 원문)
               "latency" -> Latency.schedule_servers (비-탄소 비교용, alpha=0.5 원문)"""
    n_regions = len(regions)
    ridx = {r: i for i, r in enumerate(regions)}
    buckets = _bucket_by_hour(jobs)
    hours = sorted(buckets)
    if max_hours is not None:
        hours = [h for h in hours if h < max_hours]

    decisions = {}
    t0 = time.time()
    for k, h in enumerate(hours):
        batch = buckets[h]
        request_rates = [0] * n_regions
        by_origin = {i: [] for i in range(n_regions)}
        for j in batch:
            oi = ridx[j["region"]]
            request_rates[oi] += 1
            by_origin[oi].append(j)

        if sum(request_rates) == 0:
            continue

        if policy == "carbon":
            carbon_intensities = []
            for r in regions:
                series = actual[r]
                carbon_intensities.append(series[h] if h < len(series) else series[-1])
            xij = _solve_hour(carbon_intensities, latency, request_rates, alpha, n_regions)
        elif policy == "latency":
            xij = _solve_hour_latency_baseline(latency, request_rates, alpha, n_regions)
        else:
            raise ValueError(policy)

        for i in range(n_regions):
            queue = list(by_origin[i])
            for j in range(n_regions):
                cnt = xij.get((i, j), 0)
                for _ in range(cnt):
                    if not queue:
                        break
                    job = queue.pop()
                    decisions[job["id"]] = (regions[j], job["submit_time"])
            for job in queue:  # 반올림으로 남으면(이론상 없음) 홈 리전 fallback
                decisions[job["id"]] = (job["region"], job["submit_time"])

        if verbose_every and (k + 1) % verbose_every == 0:
            elapsed = time.time() - t0
            print(f"  [{k+1}/{len(hours)}시간] {elapsed:.1f}s 경과, "
                  f"평균 {elapsed/(k+1)*1000:.1f}ms/시간", flush=True)

    return decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=None, help="지정 안 하면 0.9와 0.5 둘 다 돌린다")
    ap.add_argument("--hours", type=int, default=None, help="디버그용 — 앞 N시간만")
    args = ap.parse_args()

    jobs, actual, pred24, W, latency = H.load_all()
    print(f"작업 {len(jobs):,}건, 리전 {len(REGIONS)}개, 시간 버킷 최대 {args.hours or '전체(8760)'}")

    runs = [(ALPHA_CAP, "carbon")] if args.alpha is not None and args.alpha == ALPHA_CAP else None
    if args.alpha is not None:
        runs = [(args.alpha, "carbon")]
    else:
        runs = [(ALPHA_CAP, "carbon"), (ALPHA_LATENCY_BASELINE, "latency")]

    for alpha, policy in runs:
        label = (f"CASPER CAP(carbon, α={alpha})" if policy == "carbon"
                 else f"CASPER Latency-baseline(비탄소, α={alpha})")
        print(f"\n=== {label} 실행 ===")
        t0 = time.time()
        decisions = run_casper(jobs, actual, latency, alpha, max_hours=args.hours, policy=policy)
        dt = time.time() - t0
        print(f"  배정 완료: {len(decisions):,}건, {dt:.1f}s")

        s = H.score(decisions, jobs, W, latency, label=label)
        print(f"  {s['label']}: {s['total_carbon_kg']:,.1f} kg, "
              f"지연 {s['avg_latency_ms']:.1f} ms, "
              f"마감위반 {s['deadline_misses']:,}, 용량위반 {s['capacity_violations']:,}")


if __name__ == "__main__":
    main()
