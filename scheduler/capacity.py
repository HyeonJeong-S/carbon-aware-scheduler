"""용량 인지 온라인 시간 이동 (Algorithm 1).

기존 scheduler.compute_time_shift 는 각 작업이 **독립적으로** 자기 최적 슬롯을
고르고, 그 슬롯에 자리가 있는지 보지 않는다. 그래서 저탄소 리전·저탄소 시각으로
작업이 몰려 프랑스와 캘리포니아에서 동시 실행 수가 유효 상한 12의 3.4배인
41건에 이른다(논문 §6.4).

이 모듈은 그 결정을 **슬롯 단위 롤링 재평가**로 바꾼다. 미래 슬롯을 미리
예약하지 않고, 매 슬롯마다 아직 실행되지 않은 작업을 다시 놓고 그 슬롯의
잔여 용량 안에서만 채운다.

  CarbonFlex(arXiv 2505.18357) 와 Google CICS(IEEE TPS) 가 같은 방식이다.
  CICS 원문: "Flexible jobs get queued until resources become available."

식 (13)  a_r(t) = ⌊η·cap_r⌋ − |{ j : r(j)=r, τ_j ≤ t < τ_j+d_j }|
         본문 식 (3)을 가용 자리 형태로 다시 쓴 것이다. 즉 §5.2 에서 선언했으나
         구현하지 않았던 제약을 이 알고리즘이 실제로 강제한다. 단, 아래 F_r(t)
         (마감 보장)는 이 상한을 의도적으로 초과할 수 있다 — "절대 못 넘는다"가
         아니라 "일반 배정은 못 넘고, 마지막 기회인 작업만 예외로 넘는다"이다.
         (본문 §5.6 식(12)는 탄소 회계 E_j=P·∫C dt 로 이미 쓰였음 — 1b 2026-09-16
         정정. 이 알고리즘의 식 번호는 (13)부터 시작한다.)
식 (14)  P_r(t) = { j ∈ Q(t) : r(j)=r, score_j(t) = min_{t'∈W_j(t)} score_j(t') }
         score 는 기존 식 (11) 을 그대로 쓴다. 새 점수 함수를 만들지 않는다.
식 (15)  ρ_j(t) = u_j(t) = (D_j − d_j) − t        남은 여유. 오름차순(EDF).

우선순위를 순수 EDF 로 둔 이유는 두 가지다. 첫째, 탄소 이득으로 정렬하면
나중에 측정할 지표로 승자를 미리 뽑는 셈이어서 순환 논리가 된다. 둘째, 여유가
0인 작업이 자동으로 1순위가 되어 별도 예외 규칙이 필요 없다.

마감 보장: u_j(t) < 1 인 작업(=다음 정시면 이미 늦음)은 **대기 집합 전체**에서
골라 무조건 편입한다. P_r(t) 안에서 고르면 "지금이 최선이 아닌" 마감 임박
작업이 누락되어 기아가 발생한다. 이 때문에 |F_r(t)| > a_r(t) 이면 그 슬롯은
의도적으로 상한을 초과하며, 그 건수를 capacity_violations 로 따로 집계한다.
마감 위반(0)과 용량 위반(새로 생김)은 서로 다른 지표이므로 절대 합산하지 않는다.

기아 불가 증명: t 가 한 슬롯 진행할 때 u_j(t) 는 정확히 1 감소하고, u_j(s_j) 가
유한한 정수이므로 유한 슬롯 안에 반드시 u_j(t) < 1 에 도달한다. 그 슬롯에서
용량과 무관하게 실행되므로 어떤 작업도 무한히 연기되지 않는다.

2026-09-16 실측 검증(1b)으로 발견된 버그 둘을 여기서 고쳤다:
  (1) 분수 제출시각 vs 정수 슬롯 t 의 경계 불일치로 후보 offset 0("지금")이
      배제되어 k=3,4,5(전체 60.1%) 중 일부가 다음 정시로 밀려 마감을 어김.
      즉시실행 우회 조건도 `deadline-duration <= submit_time`(L_max>0이면
      항상 거짓이라 사실상 무용지물)이었던 것을 정수 슬롯 기준으로 고쳤다.
  (2) 장부를 정시 빈(ceil(start)~ceil(start+duration))으로 셌더니, 정시 경계를
      안 넘는(=전체의 상당수인) 짧은 작업은 ceil(start)==ceil(start+duration)이
      되어 장부에서 아예 사라졌다(과소계수가 아니라 완전 누락). §6.4 정의
      "τ≤t<τ+d"를 연속 시각 그대로 구현하는 이벤트 스윕(지연-pop 힙, LB의
      auto_capacity()/run_sim() 과 같은 기법)으로 교체했다.
  (3) (2)의 첫 구현이 reserve() 안에서도 _sync 를 불렀는데, 그 인자가 분수
      시각(같은 슬롯 안 즉시실행 경로의 submit_time)이라 힙의 가상 시계가
      뒤이은 avail(r,t)의 정수 t 보다 앞서 전진해버려, 그 사이에 끝난 것으로
      잘못 pop된 작업만큼 avail이 과대평가됐다(장부 자기보고 266건 vs
      결과 재계산 19,332건, 73배 차이 — 1b가 실측으로 특정). pop을
      running()/avail() 안에서 그 슬롯의 t로만 하도록 reserve()의 sync를
      제거했다. CapacityLedger.reserve() 의 docstring에 상세 설명 있음.

2026-09-20 (B1, d6 지시, 1차) capacity_violations 를 episode(극대 연속 구간) 수로
  정의했었다 — 359건. d6가 정리.txt [26]의 원래 정의를 확인해 정정: 662건은
  episode가 아니라 "같은 리전의 다른 작업 i 중 τ_i ≤ τ_j < τ_i+d_i 인 개수 n 이
  cap 이상인 j 의 admission" 개수였다(마감임박 강제 411 + 즉시실행 우회 251).

2026-09-21 (B1, be 지시, 2차 — 재정정) 1차 시도는 emit() 안에서 reserve() 직전에
  led.avail(r,t)를 읽어(이 작업이 들어오기 전 가용치) over_cap = (avail<=0) 으로
  근사했는데, 3,278건이 나와 662와 크게 어긋났다. 원인: 같은 tick에 여러 작업이
  동시에 시작하면 정의상 서로가 서로를 "이미 실행 중"(τ_i=τ_j 도 ≤ 를 만족)으로
  보는데, avail() 근사는 emit() 호출 순서(코드가 우연히 처리하는 순서)만 "이미"로
  잡아 같은 배치 안에서도 먼저 처리된 것과 나중 처리된 것을 다르게 셌다 — 실제
  동시성 정의와 코드의 임의 순서가 어긋난 것.
  고친 방법: _over_cap_admissions() 가 admission 도중에 아무것도 추적하지 않고,
  루프가 다 끝난 완성된 스케줄(out, 즉 최종 (start,end) 전량)에서 이벤트 스윕으로
  사후 재구성한다 — 동시각 시작 배치는 배치 전체를 하나로 묶어(자기 자신만 제외)
  n_other 를 계산하므로 처리 순서에 의존하지 않는다. be가 준 정의로 독립 검증한
  스크립트와 대조해 662 = forced 411 + immediate 251 + normal 0 을 정확히
  재현하는 것을 확인했다(2026-09-21). episode 수·hours_over 는
  capacity_violation_episodes 로 이름 바꿔 보조 지표로 남겼다.

2026-09-20 (B2, d6 지시) 즉시실행 집계 공백을 메웠다: `immediate`는 도착 즉시
  큐를 건너뛴 건수만 세는데, 정상 P/F 선택 경로에서 offset 0이 그대로 선택돼
  delay=0으로 끝나는 작업(forced도 immediate도 아님, 251건)은 어떤 카운터에도
  안 잡혔다. `zero_delay`(delay<=0인 전체 건수)와 `delayed`(나머지)를 stats에
  추가해 immediate ⊆ zero_delay, zero_delay + delayed = n 이 항상 성립하게 했다.
"""

import heapq
import math
from itertools import pairwise

import numpy as np

HORIZON = 24            # 예측 지평 (h)
SLOT = 1                # 슬롯 길이 (h)


# ────────────────────────────── 용량 장부 ──────────────────────────────
class CapacityLedger:
    """(리전) 동시 실행 수 장부 — §6.4 정의(τ_j ≤ t < τ_j+d_j)를 연속 시각 그대로.

    온라인 판정(avail)은 지연-pop 최소힙으로 O(log n): 활성 작업의 종료시각을
    힙에 넣어두고, 질의 시각 이하로 끝난 것들을 그때그때 걷어낸다(LB의
    simulator.py `running` 힙과 같은 기법). 최종 peak/hours_over 는 기록해둔
    (start, end) 전체를 한 번 이벤트 스윕해서 정확히 다시 센다 — verify_cap.py의
    concurrency_peak()와 동일한 알고리즘/동률 규약(동시각이면 시작을 먼저)이라
    장부 자기보고와 사후 재계산이 이제 일치해야 한다.

    정시 빈(bin) 배열을 쓰지 않는 이유: ceil(start)==ceil(start+duration)이면
    (=작업이 정시 경계를 안 넘으면) 그 작업은 어느 빈에도 안 걸려 장부에서
    통째로 빠진다. 전체 작업의 60%가 1시간보다 훨씬 짧아 이 경우가 흔하다 —
    정시 빈으로는 점유가 과대도 과소도 아니라 아예 안 보이는 작업이 생긴다.
    """

    def __init__(self, regions, capacity):
        self.cap = int(capacity)
        self._heap = {r: [] for r in regions}    # 활성 작업 종료시각 min-heap (지연 pop)
        self._log = {r: [] for r in regions}      # (start, end) 전량 기록 — 최종 집계용

    def _sync(self, region, t):
        h = self._heap[region]
        while h and h[0] <= t:
            heapq.heappop(h)

    def running(self, region, t):
        self._sync(region, t)
        return len(self._heap[region])

    def avail(self, region, t):
        return self.cap - self.running(region, t)

    def reserve(self, region, start, duration):
        """새 작업을 힙에 넣는다 — 여기서는 절대 pop 하지 않는다.

        2026-09-16(1b) 발견: reserve 안에서 start(분수, 같은 슬롯 안의 즉시실행
        경로일 수 있음) 기준으로 _sync 하면, 그 직후 큐 로직이 정수 슬롯 t로
        avail(r,t)를 부를 때 힙이 이미 t를 지나 전진해 있어(가상 시계가
        t보다 앞섬) 그 사이에 끝난 것으로 잘못 pop된 작업이 있으면 avail이
        과대평가된다(장부 자기보고 266건 vs 재계산 19,332건, 73배 차이의 원인).
        pop은 running()/avail() 안에서 그 슬롯의 t로만 하면 충분하다 — t는
        전체 루프에서 단조증가하고, 여기서 push하는 end는 항상 > t(= start ≥
        t, duration > 0)이므로 이 reserve가 미래의 어떤 sync에도 조기 제거될
        위험이 없다. 동시 실행 수는 시작 이벤트에서만 늘고 모든 시작이
        avail() 검사를 거치므로, 시작 시점만 봐도 불변식(동시 ≤ 상한, F 제외)은
        유지된다(1b 확인).
        """
        end = start + duration
        heapq.heappush(self._heap[region], end)
        self._log[region].append((start, end))

    def _sweep(self, region):
        """식 (3)과 동일한 이벤트 스윕으로 (peak, 상한초과 누적시간, 위반 건수)을 계산.

        위반 "건수"의 정의(2026-09-20, B1): 식 (3)은 ∀t(연속 시각)에 대한 제약이므로
        위반도 연속 시각 위의 사건이다 — 개별 admission을 세면(과거 capacity_violations가
        그랬다) 같은 초과 구간에서 여러 작업이 잇따라 들어올 때마다 중복으로 세어
        구간(episode) 수보다 부풀려진다. 여기서는 concurrency가 상한을 넘는 **극대
        연속 구간(maximal episode)의 개수**를 위반 건수로 정의한다 — hours_over가
        그 구간들의 "길이 합"이듯, violations는 그 구간들의 "개수"다. 같은 잣대(이벤트
        스윕)로 재는 것이므로 자기보고와 사후 독립 재계산이 CSV만 있으면 항상 일치한다.
        """
        ev = []
        for s, e in self._log[region]:
            if e > s:
                ev.append((s, 1))
                ev.append((e, -1))
        ev.sort(key=lambda x: (x[0], -x[1]))   # 동시각이면 시작을 먼저 (보수적)
        cur = mx = 0
        spans = []
        for t, d in ev:
            cur += d
            mx = max(mx, cur)
            spans.append((t, cur))
        over = 0.0
        episodes = 0
        prev_over = False
        for (t0, c0), (t1, _) in pairwise(spans):
            is_over = c0 > self.cap
            if is_over:
                over += t1 - t0
                if not prev_over:
                    episodes += 1
            prev_over = is_over
        return mx, over, episodes

    def peak(self, region):
        return self._sweep(region)[0]

    def hours_over(self, region):
        return self._sweep(region)[1]

    def violations(self, region):
        return self._sweep(region)[2]


# ─────────────────────── 탄소 창 평균 (누적합 가속) ───────────────────────
class _Windows:
    """구간 평균을 O(1) 로 얻기 위한 누적합.

    1년치를 매 슬롯 재평가하면 창 평균 계산이 수백만 번 일어난다. 누적합을
    미리 만들어 두지 않으면 파이썬에서 수십 분이 걸린다.
    """

    def __init__(self, actual, pred24):
        # actual[r] : (n_hours,)          실측 — 탄소 회계용
        # pred24[r] : (n_issue, HORIZON)  발행 시각별 향후 24 h 예측 — 판단용
        #
        # 2026-09-21 오프셋 보정(be 승인, 정리.txt [49]): pred24[h][0]은 "h(지금)"이
        # 아니라 "h+1(한 시간 뒤)"의 예측이다 — carbon_2025.load_2025()가 열 색인을
        # horizon-1로 채우고(horizon=1이 열0), eval_records의 horizon은 "발행 시각
        # 기준 몇 시간 뒤"이므로 열0=1시간 뒤가 원자료 자체의 규약이다(실측 대조로
        # 확인: pred24['FR'][200][0]이 eval_records의 timestamp=발행시각+1h,
        # horizon=1 행의 y_pred와 정확히 일치). carbon_2025.forecast_at()은 이미 이
        # 보정을 하고 있다(index0을 실측 actual(h)로 갈아끼우고 pred[h][:23]을
        # "h+1..h+23"으로 씀) — 그 컨벤션을 그대로 재사용해서 pred_mean()의 창별
        # 인덱싱 코드는 그대로 두고, 여기 배열 조립 단계에서만 "combined[h] =
        # [actual(h), pred24(h)[0], ..., pred24(h)[22]]" 로 다시 쌓는다. 이렇게 하면
        # offset=0이 진짜 "지금(실측)"을, offset=i(i>=1)가 진짜 "h+i"를 가리키게 된다.
        combined = {}
        for r, p in pred24.items():
            a = actual[r]
            n = min(len(a), p.shape[0])
            c = np.empty((n, HORIZON))
            c[:, 0] = a[:n]
            c[:, 1:] = p[:n, : HORIZON - 1]
            combined[r] = c

        self.act = {r: np.concatenate([[0.0], np.cumsum(v)]) for r, v in actual.items()}
        self.act_n = {r: len(v) for r, v in actual.items()}
        self.prd = {r: np.concatenate([np.zeros((v.shape[0], 1)), np.cumsum(v, axis=1)], axis=1)
                    for r, v in combined.items()}
        self.prd_n = {r: v.shape[0] for r, v in combined.items()}

    def actual_mean(self, r, start, dur_h):
        cs, n = self.act[r], self.act_n[r]
        if n <= 0:
            raise ValueError(f"실측 탄소 계열이 비어있음: region={r!r}")
        a = min(max(math.floor(start), 0), n - 1)
        b = min(a + max(1, math.ceil(dur_h)), n)
        return (cs[b] - cs[a]) / (b - a)

    def pred_mean(self, r, issue_t, offset, dur_h):
        """issue_t 시점에 발행된 예측에서, offset 시간 뒤부터 dur_h 동안의 평균."""
        cs, n = self.prd[r], self.prd_n[r]
        if n <= 0:
            raise ValueError(f"예측 계열이 비어있음: region={r!r}")
        i = min(max(math.floor(issue_t), 0), n - 1)
        a = min(max(int(offset), 0), HORIZON - 1)
        b = min(a + max(1, math.ceil(dur_h)), HORIZON)
        return (cs[i][b] - cs[i][a]) / (b - a)


def _alpha(k):
    """기존 scheduler.compute_alpha 와 동일. k 가 작을수록 탄소 가중치가 커진다."""
    return (6 - k) / 5


def _over_cap_admissions(out, regions, cap):
    """상한 위반 배정 개수 — 정리.txt [26]의 정확한 정의를 완성된 스케줄(out)에서 그대로 잰다.

    정의: 작업 j 에 대해 같은 리전의 다른 작업 i 중 τ_i ≤ τ_j < τ_i+d_i 인 개수를
    n 이라 할 때, n ≥ cap 이면 j 의 admission을 위반으로 센다. admission 시점의
    내부 장부 상태(led.avail 등)를 실행 도중에 추적하지 않고, 다 끝난 스케줄의
    (start, end) 쌍만으로 사후에 재구성한다 — 그래야 이 함수 자체가 곧 "독립
    재계산"이라 자기보고와 사후 검증이 절대 어긋날 수 없다.

    같은 시각에 여러 작업이 동시에 시작하면(흔하다 — 슬롯이 정수 tick이므로) 서로가
    서로를 "이미 실행 중"으로 본다(τ_i = τ_j 도 ≤ 를 만족). 그래서 동시각 배치는
    이벤트 스윕에서 종료를 먼저 처리한 뒤(반개구간 배제) 시작을 한 번에 묶어서
    처리하고, 그 직전 concurrency + (배치 크기 − 1) 을 배치 내 각 작업의 n 으로 쓴다.
    """
    forced_ct = immediate_ct = normal_ct = 0
    by_region = {r: [] for r in regions}
    for v in out.values():
        by_region[v["region"]].append(v)

    for jobs_r in by_region.values():
        ev = []
        for idx, v in enumerate(jobs_r):
            ev.append((v["scheduled_start"], 0, idx))
            ev.append((v["scheduled_start"] + v["duration"], 1, idx))
        ev.sort(key=lambda x: (x[0], -x[1]))   # 동시각이면 종료(1)를 먼저

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
            n_other = before + (batch - 1)
            if n_other >= cap:
                for _, _, idx in ev[j2:k2]:
                    v = jobs_r[idx]
                    if v["forced"]:
                        forced_ct += 1
                    elif v["immediate"]:
                        immediate_ct += 1
                    else:
                        normal_ct += 1
            i = k2

    return forced_ct, immediate_ct, normal_ct


# ───────────────────────────── Algorithm 1 ─────────────────────────────
def run_rolling(jobs, actual, pred24, capacity, regions,
                n_hours=None, horizon=HORIZON, home_region=False):
    """슬롯 단위 온라인 용량 인지 시간 이동.

    jobs      : scheduler.data_loader 형식 dict 목록
    actual    : {리전: 배열[시간]}                실측 (회계)
    pred24    : {리전: 배열[발행시각][24]}        예측 (판단)
    capacity  : 유효 상한 ⌊η·cap_r⌋ (전 리전 균일 — LB 의 auto_capacity 규약)
    home_region : True 면 로드밸런서 배정을 무시하고 출발 리전을 쓴다(B3 대조군)

    반환 (results, stats)
    """
    W = _Windows(actual, pred24)
    if n_hours is None:
        n_hours = int(max(j["deadline"] for j in jobs)) + 2
    led = CapacityLedger(regions, capacity)

    def region_of(j):
        return j["region"] if home_region else (j.get("carbon_region") or j["region"])

    # 제출 슬롯별 도착 목록
    arrivals = {}
    for j in jobs:
        arrivals.setdefault(math.floor(j["submit_time"]), []).append(j)

    Q = {r: [] for r in regions}          # 리전별 대기 집합
    out, forced, immediate = {}, 0, 0

    def emit(j, r, start, forced_flag, immediate_flag):
        d = j["duration"]
        led.reserve(r, start, d)
        rate = W.actual_mean(r, start, d)
        out[j["id"]] = dict(
            job_id=j["id"], k=j["k"], region=r,
            submit_time=j["submit_time"], duration=d,
            scheduled_start=start, delay=start - j["submit_time"],
            carbon_emitted=rate * d,
            slo_satisfied=(start + d) <= j["deadline"] + 1e-9,
            forced=forced_flag,
            immediate=immediate_flag,
        )

    for t in range(0, n_hours + 2):
        for j in arrivals.pop(t, ()):
            r = region_of(j)
            # 정수 슬롯 기준으로 "다른 정시가 없는" 작업만 즉시실행으로 우회한다.
            # deadline-duration(=submit_time+L_max, 둘 다 분수)을 그대로 submit_time과
            # 비교하면 L_max>0인 한 항상 거짓이 되어(버그, 2026-09-16 발견) 우회가
            # 무용지물이었다 — floor 를 씌워 "정수 슬롯 격자 위에 다른 후보가
            # 있는가"로 바꿨다. k=3,4,5(전체의 60.1%)의 대부분이 여기 해당한다.
            # 이 경로는 용량 검사를 받지 않는다(미룰 수 없는 작업이라 막을 수 없음,
            # 정리.txt [26] 항목3) — 그래서 emit()에서 over_cap 여부만 별도로 집계한다.
            if math.floor(j["deadline"] - j["duration"]) <= math.floor(j["submit_time"]):
                emit(j, r, j["submit_time"], False, True)
                immediate += 1
            else:
                Q[r].append(j)

        for r in regions:
            if not Q[r]:
                continue
            a = led.avail(r, t)

            # 마감 보장 — 대기 집합 전체에서 고른다 (P 안에서 고르면 기아 발생)
            # u_j(t) < 1 이면 다음 슬롯은 이미 늦으므로 이 슬롯이 마지막 기회다.
            F, rest = [], []
            for j in Q[r]:
                if (j["deadline"] - j["duration"]) - t < 1:
                    F.append(j)
                else:
                    rest.append(j)

            # 식 (14) : 남은 윈도우에서 지금이 최선인 작업.
            # offset 0 은 "이 슬롯에서 지금 시작"을 뜻하고, 실제 시각은
            # max(t, submit_time) 이다(job 첫 고려 슬롯에서만 submit_time이
            # t보다 분수만큼 늦을 수 있음 — 재고려 슬롯에서는 t가 이미 지났으므로
            # 항상 t와 같다). offset 0을 lo=ceil(submit_time-t)로 배제하던 것이
            # 원래 버그: 분수 제출시각이면 거의 항상 1이 되어 "지금"이 후보에서
            # 통째로 빠졌다. lo는 항상 0이어야 한다.
            P = []
            for j in rest:
                d = j["duration"]
                hi = int(min(j["deadline"] - d, t + horizon) - t)
                if hi < 0:
                    continue
                cand = range(0, hi + 1)
                cost = {i: W.pred_mean(r, t, i, d) for i in cand}
                cmin, cmax = min(cost.values()), max(cost.values())
                den = (j["deadline"] - d) - j["submit_time"]
                al = _alpha(j["k"])
                best_i, best_s = 0, float("inf")
                for i in cand:
                    ch = 0.0 if cmax == cmin else (cost[i] - cmin) / (cmax - cmin)
                    actual_start = max(t, j["submit_time"]) if i == 0 else (t + i)
                    dh = (actual_start - j["submit_time"]) / den if den > 0 else 0.0
                    s = al * ch + (1 - al) * dh
                    if s < best_s:                     # 동률이면 가장 이른 슬롯
                        best_s, best_i = s, i
                if best_i == 0:                        # 지금이 최선
                    P.append(j)

            # 식 (15) : 남은 여유 오름차순 (EDF)
            P.sort(key=lambda j: (j["deadline"] - j["duration"]) - t)
            room = max(a - len(F), 0)
            S = F + P[:room]
            forced += len(F)

            picked = {id(j) for j in S}
            F_ids = {id(j) for j in F}
            Q[r] = [j for j in Q[r] if id(j) not in picked]

            for j in S:
                start = max(t, j["submit_time"])
                emit(j, r, start, id(j) in F_ids, False)

        if not any(Q.values()) and not arrivals:
            break

    # B2(2026-09-20): `immediate`는 도착 즉시 큐를 건너뛴 건수만 센다. 그런데 큐에
    # 들어간 뒤에도 offset 0("지금")이 그대로 선택돼 delay=0으로 끝나는 작업이
    # 따로 있다(정상 P/F 선택 경로) — 이들은 forced도 immediate도 아니어서
    # 예전에는 어떤 카운터에도 안 잡혔다(146,000건 중 251건). zero_delay로 명시해
    # immediate + (zero_delay - immediate) + delayed = n 이 항상 맞아떨어지게 한다.
    zero_delay = sum(1 for v in out.values() if v["delay"] <= 1e-9)
    # B1 재정정(2026-09-20, be): §6.4 서술("상한 위반 배정")과 정리.txt [26]의 662건은
    # episode(극대 연속 구간) 수가 아니라 **admission 단위 개수**였다 — "같은 리전의
    # 다른 작업 i 중 τ_i ≤ τ_j < τ_i+d_i 인 개수 n 이 cap 이상인 j 의 admission".
    # admission 시점에 진행 순서(emit 호출 순서)로 근사하면 틀린다 — 같은 tick에
    # 동시에 시작하는 배치는 서로를 "이미 실행 중"으로 보는데, 코드상 먼저 emit된
    # 것만 "이미"로 잡히기 때문이다(실측: 3,278 = 662의 5배, be가 준 정의로 검증해
    # 틀렸음을 확인함). _over_cap_admissions()가 다 끝난 스케줄에서 사후로 다시
    # 재구성하므로 이게 곧 독립 재계산이고, 662 = forced 411 + immediate 251 을
    # 정확히 재현한다(2026-09-21 확인).
    over_cap_forced, over_cap_immediate, over_cap_normal = _over_cap_admissions(out, regions, capacity)
    over_cap_admissions = over_cap_forced + over_cap_immediate + over_cap_normal
    stats = dict(
        n=len(out),
        total_carbon_kg=sum(v["carbon_emitted"] for v in out.values()) / 1000.0,
        slo_violations=sum(1 for v in out.values() if not v["slo_satisfied"]),
        forced_admissions=forced,
        capacity_violations=over_cap_admissions,
        over_cap_forced=over_cap_forced,
        over_cap_immediate=over_cap_immediate,
        over_cap_normal=over_cap_normal,
        capacity_violation_episodes=sum(led.violations(r) for r in regions),
        immediate=immediate,
        zero_delay=zero_delay,
        delayed=len(out) - zero_delay,
        peak={r: led.peak(r) for r in regions},
        hours_over={r: led.hours_over(r) for r in regions},
        capacity=capacity,
    )
    return out, stats
