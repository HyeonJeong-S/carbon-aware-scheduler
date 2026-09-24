# -*- coding: utf-8 -*-
"""Caspian(Bahreini, Tantawi, Tardieu — "Caspian: A Carbon-aware Workload
Scheduler in Multi-Cluster Kubernetes Environments", MASCOTS'24, IEEE) 의
§II(MOSP 정식화)·§III(Algorithm 1~3) 를 원문 수식 그대로 구현한다.

Caspian은 공개 코드가 없다(2026-09-24 확인, IBM Research/MASCOTS'24) — 아래
정식화는 논문 PDF(paper/참고/Caspian_...pdf)의 §II·§III을 직접 옮겨 적은 것이다.
창작·근사가 들어간 자리는 각 함수 docstring에 "단순화:"로 표시했고, 전부
아래 "구현 결정 기록" 절에 다시 모아뒀다.

===========================================================================
원문 §II 전사 (기호는 논문 그대로, 첨자만 코드 변수명과 병기)
===========================================================================
집합/기호:
  N : 작업(workload) 집합, i ∈ N
  M : 스포크 클러스터 집합, j ∈ M
  T : 시간 슬롯 집합(지평 T), t ∈ T
  작업 i = (a_ij, r_i, l_i, d_i):
      a_ij ∈ {0,1}  — 정책(작업 i가 클러스터 j에서 실행 가능하면 1)
      r_i           — 필요 자원량
      l_i           — 실행 시간(슬롯 수)
      d_i           — 마감(슬롯)
  클러스터 j = (C_j^t, I_j^t, ρ_j):
      C_j^t — 슬롯 t에서 클러스터 j의 가용 자원량
      I_j^t — 슬롯 t에서 클러스터 j의 탄소집약도
      ρ_j   — 전력 효율 계수(상수, 낮을수록 효율적 — 원문 각주3)
  결정변수: x^t_ij ∈ {0,1} — 작업 i가 클러스터 j에서 슬롯 t에 "시작"하면 1
  Δ^t_i = {t-l_i+1, ..., t} — 슬롯 t'에 시작한 작업이 슬롯 t에도 "실행 중"이려면
                              t' ∈ Δ^t_i (즉 아직 안 끝났어야 함)

목적함수 (식 1~3, 원문 그대로):
  Z1(x) = Σ_{j∈M} Σ_{t∈T}  [ Σ_{i∈N} Σ_{t'∈Δ^t_i} x^{t'}_ij · r_i ]
                            ───────────────────────────────────────
                                        C_j^t · I_j^t · ρ_j
      (분자 = 슬롯 t·클러스터 j의 총 자원사용량. 탄소·전력효율로 나눠 "저탄소
       시간·장소에서 자원을 많이 쓸수록" 커지게 만든 효용 — 최대화 대상)

  Z2(x) = Σ_i Σ_j Σ_t  x^t_ij / γ(i,t)
      γ(i,t) = max(1, l_i + t − d_i)   — 지연 페널티(마감 초과분, 안 늦으면 1)

  Z3(x) = Σ_i Σ_j Σ_t  x^t_ij / λ(i,t)
      λ(i,t) = t + l_i                — 완료 시각 그 자체(마감 무관, 너무 늦은
                                         완료 자체를 억제)

결합 목적함수 (스칼라화, 원문 그대로):
  Z(x) = ω̄1·Z1(x) + ω̄2·Z2(x) + ω̄3·Z3(x)
  ω̄_k = ω_k / θ_k,   θ_k = 1/Z̄_k   (Z̄_k = Z_k 단독 LP완화 최적값)

제약 (식 5~8, 원문 그대로):
  (5) Σ_i Σ_{t'∈Δ^t_i} x^{t'}_ij · r_i ≤ C_j^t   ∀j,t      — 용량, **하드**
  (6) Σ_j Σ_t x^t_ij ≤ 1                         ∀i        — 작업당 최대 1번
                                                               (강제 배정 아님 —
                                                               0이면 이번 주기엔
                                                               미배정)
  (7) x^t_ij ≤ a_ij                               ∀i,j,t   — 정책/적합성
  (8) x^t_ij ∈ {0,1}                                        — 정수성

===========================================================================
Algorithm 1 Scheduler(δ) — 원문 그대로
===========================================================================
  while True:
      (M,N) ← getClusterAndWorkloadInfo()
      y ← Optimizer(M,N)
      for i in N:
          if isValid(y[i]): setTarget(i, y[i])   # 이번 주기에 배정 확정
          else: suspend(i)                        # 다음 주기로 미룸
      wait(δ)

===========================================================================
Algorithm 2 Optimizer(M,N) — 원문 그대로
===========================================================================
  1: θ_k ← LPSolver(Z_k, M, N)  ∀k∈{1,2,3}     # 각 목적함수 단독 LP완화 최적값의 역수
  2: Z(x) ← Σ_k ω̄_k · Z_k(x)
  3: x̄ ← LPSolver(Z, M, N)                     # 결합 목적함수의 LP완화
  4: x ← 0, y_i ← -1 ∀i                          # y_i=-1: 이번 주기 미배정
  5: b_i ← Σ_{j,t} x̄^t_ij  ∀i                    # LP 해의 분수질량 = 우선순위 점수
  6: N을 b_i 내림차순 정렬
  7: for i in N (정렬된 순서):
  8:     (j*,t*) ← Allocation(i, x, Z, M)
  9:     if isValid(j*): x^{t*}_{ij*} ← 1
  10:        if t* == 1(=지금 슬롯): y_i ← j*     # 지금 시작 → 실제 배치
  11: return y

===========================================================================
Algorithm 3 Allocation(i, x, Z, M) — 원문 그대로
===========================================================================
  1: (j,t)쌍 전체를 z^t_ij(결합 목적함수의 (i,j,t) 계수) 내림차순 정렬
  2: (j*,t*) ← (-1,-1)
  3: for (j,t) in 정렬된 순서:
  4:     if fit(i,x,j,t') for all t'∈{t,...,t+l_i-1}:   # 식(5)(7)이 실행 구간
                                                          # 전체에서 성립하는지
  5:         (j*,t*) ← (j,t); break
  6: return (j*,t*)

===========================================================================
구현 결정 기록 (전부 "단순화" 또는 "매핑" — 창작 없음, 전부 여기 명시)
===========================================================================
[매핑] N = 우리 146,000개 job. M = 우리 REGIONS 8개(원문의 스포크 클러스터).
       T = 시간지평 24슬롯(우리 예측 지평 HORIZON=24와 동일하게 맞춤 — 원문은
       T의 절대값을 못 박지 않음, "a horizon of T time slots"로만 서술).
[매핑] d_i = 우리 job의 deadline(시간). l_i = duration을 슬롯(정수 시간)으로
       올림. δ(재평가 주기) = 1시간 — 우리 시스템 전체의 SLOT=1과 통일, CAST의
       Algorithm 1과 같은 주기라 비교 가능.
[단순화] a_ij = 1 (모든 작업이 모든 리전에서 실행 가능) — CAST 쪽 §5.2 기본
       설정(네트워크 SLO 하드 제한 없음, l_net_max=None)과 맞춤. 원문처럼 정책
       제약을 둘 근거(우리 시스템엔 "이 작업은 이 리전 금지" 같은 규칙이 없음)가
       없어서 항등적으로 허용.
[단순화] r_i = 1, C_j^t = K_r = 12(전 리전·전 슬롯 균일) — 우리 시스템의 용량
       정의(§5.2 식(3), "동시 실행 수 ≤ K_r")가 원래 "자원량"이 아니라 "동시
       실행 작업 수" 상한이라, Caspian의 자원량(r_i/C_j^t) 형식주의를 여기 그대로
       얹으면 r_i=1(모든 작업이 자원 1단위 소비)이 유일하게 자연스러운 대응이다.
       이렇게 하면 식(5)가 CAST의 식(3)과 문자 그대로 같아져 두 스케줄러가 같은
       용량 정의로 채점된다(공정성 확보).
[단순화] ρ_j = 1 (전 리전 균일) — 원문 실험도 ρ_j를 실측이 아니라 임의로
       가정했다("we assume power efficiency factor... set ρ1=ρ3=200, ρ2=100").
       우리 시스템엔 리전별 전력효율 데이터가 없어 실측 가정 없이 균일값을 쓴다
       (임의의 비균일 값을 만들어내는 것보다 정직하다고 판단). 이 단순화 때문에
       우리 Z1은 사실상 "저탄소 구간에 자원을 많이 쓸수록 좋다"만 남고 원문의
       "리전별 하드웨어 효율 차이" 축은 반영되지 않는다.
[단순화] I_j^t = 우리 LSTM 예측값 Ĉ_r(t) (실측이 아니라 예측 — CAST의 "예측으로
       결정" 원칙과 통일, 공정한 비교를 위해 필수). 배출량 채점은 반드시
       harness.score()가 실측으로 한다(아래 "채점" 절 참고) — Caspian 내부의
       *결정*에만 예측을 쓴다.
[단순화·주의, 중요] l_i를 정수 슬롯(시간)으로 올림하는 것 — 원문 정식화 자체가
       슬롯 단위 정수 l_i를 전제하는데, 우리 작업의 60.1%(k=3,4,5)는 실행시간이
       분·초 단위다(예: k=5는 1~5초). 이들을 전부 "1슬롯(1시간) 점유"로 올림하면
       실제로는 몇 초만 쓰는 용량을 1시간 통째로 쓰는 것처럼 취급하게 되어
       Caspian의 용량 경합이 실제보다 훨씬 심해진다. **이건 창작이 아니라
       Caspian의 원문 정식화 자체가 슬롯 이하 단위를 지원하지 않는다는 구조적
       한계이고, 우리가 도입한 근사가 아니다** — 다만 그 한계가 우리 워크로드
       에서는 남달리 크게 불리하게 작용한다는 점은 명시해야 공정하다.
[경계 처리 규약, 2d 요청 — 2026-09-24 성능 문제로 1차 수정] 마감이 소프트라
       종료 보장이 없다. 시뮬레이션은 유한하므로 다음 규칙을 쓴다: 어떤 작업이
       **자기 마감(d_i)을 FORCE_BUFFER_HOURS(=1시간) 넘게 지나도록** 한 번도
       배정(y_i≠-1)받지 못하면, 그 시점에 "예측 기반 배정을 포기"하고 즉시(그
       시각, 홈 리전) 강제 배치한다.
       최초 설계는 "제출 후 48시간(가장 긴 k=1 마감의 2배)"이었으나, 실측
       파일럿(48시간, 800개 작업)에서 미배정 큐가 시간당 순증 +3~4건으로
       꾸준히 불어나 LP 크기가 선형 이상으로 커지고 주기당 처리 시간이
       0.3초(t=0)→1.5초(t=19)로 5배 늘어나는 걸 확인했다 — 원인은 "제출 후
       48시간"이 k=3,4,5(마감 여유가 수 분~수십 분에 불과한 60.1%)에게도
       똑같이 48시간의 유예를 주어 큐에 불필요하게 오래 남긴 것이었다.
       "자기 마감 + 1시간"으로 바꾸면 여유가 짧은 작업은 실제로 짧게만
       큐에 남고(원문의 "곧 놓칠 마감" 압박을 그대로 반영), 여유가 긴
       작업(k=1, 최대 24h)만 최대 ~25시간 남는다 — 큐 크기의 구조적 상한이
       "동시에 마감이 도래하는 작업 수" 근처로 줄어든다.
       이 강제배치 건수를 boundary_forced로 따로 세어 보고한다 — Caspian이
       마감을 얼마나/어떻게 놓치는지의 핵심 증거가 된다(강제배치 자체가 곧
       "이 알고리즘이 이 작업의 마감을 못 지켰다"는 뜻이다 — harness의
       deadline_misses와 논리적으로 겹친다).
[재최적화 주기·불일치] 원문은 "δ 는 워크로드 QoS 요구·평균 실행시간에 따라
       스케줄러가 정한다"고만 하고 절대값을 안 박는다. 우리는 δ=1시간(CAST와
       동일)을 썼다 — 원문의 실제 배포 사례(§V, 40시간·200개 job 실험)에서 δ가
       얼마였는지는 논문에 안 적혀 있어 알 수 없다. 이 불일치를 한계로 남긴다.
[버그 수정, 2026-09-24, 2d가 결과 이상으로 발견] 최초 구현은 dispatch 시각을
       그냥 now(정수 시)로 기록했다. now는 "floor(제출시각)"에서 온 값이라
       실제 제출시각보다 최대 1시간 이를 수 있는데, 그걸 그대로 시작시각으로
       쓰면 harness의 마감판정("start+duration > deadline"이면 위반)이 "제출도
       하기 전에 이미 시작해 일찍 끝난 것"처럼 계산돼 마감위반이 인위적으로
       사라진다. 실측(60일 표본): 79.2%의 배정이 start<submit_time이었고
       최대 격차는 정확히 0.9999h(=1시간 미만, floor 오차 그대로). ω1=0.0
       전체실행 결과가 "마감위반 0 / 용량위반 89,319"로 나와(용량 하드·마감
       소프트인 원문 설계와 정반대) 2d가 짚어냈다. 수정: dispatch 시각을
       max(now, submit_time)으로(CAST의 capacity.py와 같은 관례) — 슬롯
       버킷팅(어느 시간 슬롯을 점유하는지)은 그대로 now 기준을 쓰고, harness에
       보고하는 실제 시작시각만 correct하게 당김. 이 버그가 있던 상태로 나온
       결과(ω1=0.0·0.25 전체실행, 60일 올림/분수 대조)는 전부 무효로 보고
       버그수정 후 재실행했다 — 아래 run_caspian_sweep.py/run_caspian_bind_study.py
       실행 이력과 caspian_sweep_results/ 파일의 타임스탬프로 구분 가능하다.
"""

import math
import time

import numpy as np
import pulp

from interface.regions import REGIONS

T_LOOKAHEAD = 24        # Caspian의 지평 T (슬롯). 우리 예측지평과 통일.
DELTA_HOURS = 1          # 재평가 주기 δ. CAST Algorithm 1과 통일.
CAP_DEFAULT = 12         # C_j^t = K_r, 전 리전·전 슬롯 균일 (prior_harness.CAP과 동일)
FORCE_BUFFER_HOURS = 1.0  # 경계 처리: 자기 마감을 이만큼 넘기면 강제 배치(위 기록 참고)


def _slots(duration_hours: float) -> int:
    """l_i — 소수 시간을 정수 슬롯으로 올림(위 '구현 결정 기록' 참고)."""
    return max(1, math.ceil(duration_hours - 1e-9))


def _gamma(l_i: int, t_start: float, deadline_slot: float) -> float:
    """γ(i,t) = max(1, l_i + t - d_i)."""
    return max(1.0, l_i + t_start - deadline_slot)


def _lambda(l_i: int, t_start: float) -> float:
    """λ(i,t) = t + l_i."""
    return t_start + l_i


class _Occupancy:
    """리전별 슬롯별 이미 확정된 점유량 — 식(5) 우변(C_j^t)에서 빼줄 배경 부하.

    Caspian이 슬롯 단위로만 동작하므로(위 기록 참고), 여기서도 정수 슬롯
    그리드로 점유를 센다. 이미 dispatch된(y_i가 확정된) 작업만 반영한다.

    2026-09-24 (2d 지시) r_i 가중치 지원 추가 — 기본은 r_i=1(작업당 1단위,
    기존 동작과 동일). fractional=True 모드에서는 r_i=min(duration,1.0)로
    슬롯 미만 작업의 점유를 실제 비중만큼만 반영한다(아래 run_caspian의
    fractional 인자·"l_i 올림 부풀림" 진단 참고).
    """

    def __init__(self, regions):
        self.count = {r: {} for r in regions}   # region -> {slot: 가중합}

    def add(self, region, start_slot, l_i, weight=1.0):
        d = self.count[region]
        for s in range(start_slot, start_slot + l_i):
            d[s] = d.get(s, 0.0) + weight

    def used(self, region, slot):
        return self.count[region].get(slot, 0.0)


def _z_components(job, region_idx, t_start, l_i, deadline_slot, cap, W, issue_hour, region_code):
    """(i,j,t) 하나의 Z1,Z2,Z3 개별 기여도. r_i=ρ_j=1, C_j=cap (위 단순화 기록).

    Z1 기여 = (1/cap) * Σ_{τ=t}^{t+l_i-1} 1/I_region(τ)   (예측 탄소집약도의 역수 합)
    Z2 기여 = 1/γ(i,t)
    Z3 기여 = 1/λ(i,t)
    """
    inv_intensity_sum = 0.0
    for tau in range(t_start, t_start + l_i):
        offset = tau - issue_hour
        if offset < 0:
            offset = 0
        # 예측은 1시간 평균(=그 슬롯의 대표값)으로 근사 — capacity._Windows.pred_mean 재사용
        mean_c = W.pred_mean(region_code, issue_hour, offset, 1.0)
        inv_intensity_sum += 1.0 / max(mean_c, 1e-6)
    z1 = inv_intensity_sum / cap
    z2 = 1.0 / _gamma(l_i, t_start, deadline_slot)
    z3 = 1.0 / _lambda(l_i, t_start)
    return z1, z2, z3


def _solve_lp_optimum(active, occ, cap, weights, W, now_hour, regions, T):
    """LPSolver(Z, M, N) — 결합(또는 단일) 목적함수의 LP완화를 풀고
    (최적값, {job_id: {(region,t_start): x값}}) 을 돌려준다.

    weights = (w1,w2,w3) — 단일 목적함수 LP는 예: (1,0,0).
    변수는 실현 가능한 (j, t_start) 쌍에 대해서만 만든다(전부 만들면 낭비 —
    슬롯 t_start가 지평 T를 넘거나 옥트먼트 밖이면 애초에 변수를 안 만듦).
    """
    prob = pulp.LpProblem("caspian_mosp", pulp.LpMaximize)
    x = {}         # (job_id, region, t_start) -> LpVariable
    coeff = {}     # 같은 키 -> 결합 계수(z1*w1+z2*w2+z3*w3)
    by_job = {}    # job_id -> [(region,t_start), ...]

    for job in active:
        jid = job["id"]
        l_i = job["_l_i"]
        r_i = job["_r_i"]
        d_slot = job["_deadline_slot"]
        by_job[jid] = []
        for region in regions:
            for t_start in range(0, T):
                # 용량 사전 배제: 이 구간에 기존 점유+r_i가 cap을 넘으면 변수 자체를 안 만든다
                # (식(5)를 변수 생성 단계에서 걸러 LP 크기를 줄인다 — 결과는 동일,
                # capacity 제약을 명시적으로 또 걸 필요가 없어짐).
                feasible = True
                for tau in range(t_start, t_start + l_i):
                    if occ.used(region, tau) + r_i > cap:
                        feasible = False
                        break
                if not feasible:
                    continue
                z1, z2, z3 = _z_components(job, None, t_start, l_i, d_slot, cap,
                                            W, now_hour, region)
                c = weights[0] * z1 + weights[1] * z2 + weights[2] * z3
                var = pulp.LpVariable(f"x_{jid}_{region}_{t_start}", lowBound=0, upBound=1)
                key = (jid, region, t_start)
                x[key] = var
                coeff[key] = c
                by_job[jid].append((region, t_start))

    if not x:
        return 0.0, {}

    prob += pulp.lpSum(coeff[k] * x[k] for k in x)

    # 식 (6): 작업당 최대 1번 (강제 아님)
    for jid, opts in by_job.items():
        if opts:
            prob += pulp.lpSum(x[(jid, r, t)] for r, t in opts) <= 1

    # 식 (5): 용량 — 슬롯 t'가 실제로 이 슬롯에 걸치는 모든 (job,region,start) 합
    # (r_i 가중 — 기본 r_i=1은 기존과 동일, fractional 모드는 r_i=min(duration,1))
    for region in regions:
        for t in range(0, T + max((j["_l_i"] for j in active), default=1)):
            terms = []
            for job in active:
                jid = job["id"]
                l_i = job["_l_i"]
                r_i = job["_r_i"]
                for t_start in range(max(0, t - l_i + 1), min(T, t + 1)):
                    key = (jid, region, t_start)
                    if key in x:
                        terms.append(r_i * x[key])
            if terms:
                prob += pulp.lpSum(terms) <= cap - occ.used(region, t)

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    obj_val = pulp.value(prob.objective) or 0.0
    xval = {k: (v.value() or 0.0) for k, v in x.items()}
    return obj_val, xval


def _allocation(job, occ, cap, wbar, W, now_hour, regions):
    """Algorithm 3 — z^t_ij 내림차순으로 (j,t) 후보를 보며 첫 fit을 채택."""
    l_i = job["_l_i"]
    r_i = job["_r_i"]
    d_slot = job["_deadline_slot"]
    cands = []
    for region in regions:
        for t_start in range(0, T_LOOKAHEAD):
            z1, z2, z3 = _z_components(job, None, t_start, l_i, d_slot, cap,
                                        W, now_hour, region)
            z = wbar[0] * z1 + wbar[1] * z2 + wbar[2] * z3
            cands.append((z, region, t_start))
    cands.sort(key=lambda c: -c[0])

    for _, region, t_start in cands:
        fit = all(occ.used(region, tau) + r_i <= cap for tau in range(t_start, t_start + l_i))
        if fit:
            return region, t_start
    return None, None


def run_caspian(jobs, W, omega1, omega2=1.0, omega3=1.0, cap=CAP_DEFAULT,
                regions=None, delta_hours=DELTA_HOURS, t_lookahead=T_LOOKAHEAD,
                force_buffer_hours=FORCE_BUFFER_HOURS, verbose=False,
                fractional=False):
    """Caspian Algorithm 1(Scheduler)을 δ시간 주기로 잡을 끝까지 돌린다.

    fractional : False(기본) — r_i=1(작업당 1단위, 원문 그대로의 "개수" 읽기).
                 True — r_i=min(duration_hours,1.0)(2d 지시, 2026-09-24) —
                 슬롯 미만 작업(60.1%, k=3,4,5)이 슬롯 하나를 통째로 점유하는
                 것으로 계상되는 부풀림을 완화하는 대조 실행용. l_i(점유 슬롯
                 "개수")는 그대로 올림값을 쓴다 — 이 대조는 "각 슬롯 안에서
                 얼마나 무겁게 점유하는가"만 완화하고 "몇 슬롯에 걸치는가"는
                 안 건드린다(원문 r_i·C_j^t가 "자원량"이지 "개수"가 아니라는
                 점에 더 가까운 읽기 — 자세한 근거는 파일 상단 기록 참고).

    반환: (decisions, stats)
      decisions : {job_id: (region_code, start_hour)}  — harness.score() 입력 그대로
      stats     : dict — boundary_forced 등 진단 정보
    """
    regions = regions or REGIONS
    jobs_by_submit = {}
    for j in jobs:
        jobs_by_submit.setdefault(math.floor(j["submit_time"]), []).append(j)

    n_hours = int(max(j["deadline"] for j in jobs)) + int(force_buffer_hours) + 2
    occ = _Occupancy(regions)
    decisions = {}
    queue = []          # 아직 dispatch 안 된 job들
    boundary_forced = 0
    t0 = time.time()

    for now in range(0, n_hours, delta_hours):
        for j in jobs_by_submit.pop(now, ()):
            j["_l_i"] = _slots(j["duration"])
            j["_r_i"] = min(j["duration"], 1.0) if fractional else 1.0
            j["_deadline_slot"] = j["deadline"]
            queue.append(j)

        # 경계 처리: 자기 마감을 force_buffer_hours 넘도록 미배정인 작업은
        # 즉시(홈 리전) 강제 배치
        still_queue = []
        for j in queue:
            if now >= j["deadline"] + force_buffer_hours:
                # 실제 시작은 max(now, submit_time) — CAST(capacity.py)와 동일 관례.
                # (2026-09-24 버그 수정: 이전엔 start=now를 그대로 썼는데, now는
                # floor(submit_time) 처리 때문에 실제 제출시각보다 최대 1시간
                # 이를 수 있었다 — 그러면 harness의 마감판정이 "제출 전에 이미
                # 시작한 것"처럼 계산돼 마감위반이 인위적으로 사라진다. 2d가
                # ω1=0.0 전체실행에서 "마감위반 0·용량위반 89,319"라는 Caspian
                # 답지 않은 결과로 이 버그를 잡아냈다.)
                start = max(now, j["submit_time"])
                occ.add(j["region"], math.floor(start), j["_l_i"], j["_r_i"])
                decisions[j["id"]] = (j["region"], start)
                boundary_forced += 1
            else:
                still_queue.append(j)
        queue = still_queue
        if not queue:
            continue

        active = queue
        # Algorithm 2, step 1: 단일 목적함수 LP완화로 정규화 상수 θ_k
        theta = []
        for w in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            zbar, _ = _solve_lp_optimum(active, occ, cap, w, W, now, regions, t_lookahead)
            theta.append(1.0 / zbar if zbar > 1e-9 else 0.0)
        wbar = (omega1 * theta[0], omega2 * theta[1], omega3 * theta[2])

        # step 3: 결합 목적함수 LP완화
        _, xval = _solve_lp_optimum(active, occ, cap, wbar, W, now, regions, t_lookahead)

        # step 5~6: b_i 내림차순 정렬
        b = {}
        for (jid, region, t_start), v in xval.items():
            b[jid] = b.get(jid, 0.0) + v
        active.sort(key=lambda j: -b.get(j["id"], 0.0))

        # step 7~11: Algorithm 3 그리디 배정
        remaining = []
        for j in active:
            region, t_start = _allocation(j, occ, cap, wbar, W, now, regions)
            if region is None:
                remaining.append(j)   # 이번 주기엔 자리 없음 — 다음 주기로
                continue
            if t_start == 0:          # "지금" 슬롯 → 실제 dispatch
                # 실제 시작은 max(now, submit_time) — 위 경계처리와 같은 버그수정.
                start = max(now, j["submit_time"])
                occ.add(region, math.floor(start), j["_l_i"], j["_r_i"])
                decisions[j["id"]] = (region, start)
            else:
                remaining.append(j)   # 미래 슬롯 계획 — 이번 주기엔 미확정, 큐 유지
        queue = remaining

        if verbose and now % 168 == 0:
            elapsed = time.time() - t0
            frac_done = now / n_hours if n_hours > 0 else 0
            eta_h = (elapsed / frac_done - elapsed) / 3600 if frac_done > 1e-6 else float("nan")
            print(f"  t={now}h/{n_hours}h({100*frac_done:.1f}%) 큐={len(queue)} 확정={len(decisions)} "
                  f"강제={boundary_forced} 경과={elapsed:.1f}s 남은시간추정={eta_h:.2f}h",
                  flush=True)

    # 시뮬레이션 끝까지 못 정해진 잔여(있어서는 안 되지만 방어적으로) 강제 배치
    for j in queue:
        decisions[j["id"]] = (j["region"], j["submit_time"])
        boundary_forced += 1

    stats = dict(boundary_forced=boundary_forced, wall_seconds=time.time() - t0)
    return decisions, stats
