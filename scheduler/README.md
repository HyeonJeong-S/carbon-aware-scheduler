# 탄소 인식 Time-Shift 스케줄러

클라우드 job을 **탄소 배출이 낮은 시간대로 미뤄서 실행**하는 스케줄러 시뮬레이터입니다.
"job을 언제 실행할지"를 각 job의 마감 여유(중요도) 안에서 탄소·지연 트레이드오프로 결정하고,
그 효과를 웹 대시보드에서 세계지도와 함께 시각적으로 확인할 수 있습니다.

---

## 1. 한눈에 보는 개요

전체 시스템은 3단계 파이프라인이며, 이 저장소는 **마지막 단계(스케줄러)** 를 담당합니다.

```
[LSTM 탄소예측]            [로드밸런서]                 [스케줄러  ← 이 저장소]
과거 탄소강도      →    8개 리전 × 24h 예측    →   어느 리전?(공간이동)  →   언제 실행?(시간이동)
                                                    │
                                                    └─ 결과: 총 탄소 / 지연 / SLO 위반
```

- **로드밸런서**가 job을 어느 리전에서 돌릴지(Spatial shift) 이미 정해서 넘겨줍니다.
- **스케줄러(우리)** 는 그 리전 안에서 **언제 실행할지(Time shift)** 만 결정합니다.
- **LSTM**은 리전별 향후 24시간 탄소강도 예측을 제공합니다 (`interface/carbon_forecast_api.py` 경유).

---

## 2. 핵심 아이디어

job마다 중요도 `k`(1~5)가 있고, 그에 따라 **미룰 수 있는 최대 시간 `L_max`** 가 정해집니다.
급한 job은 거의 못 미루고, 여유 있는 job은 최대 24시간까지 미룰 수 있습니다.

| k | 성격 | 작업 예시 | L_max(최대 지연) | 생성 비율 |
|---|------|-----------|------------------|-----------|
| 5 | 매우 급함 | 웹페이지 로딩, API 응답, 결제 | ~1초 | 30% |
| 4 | 급함 | 검색 결과, 업로드 확인 | ~30초 | 20% |
| 3 | 보통 | 주문상태 업데이트, 배송알림 | ~5분 | 10% |
| 2 | 여유 | 정산배치, DB백업, 재고동기화 | ~6시간 | 10% |
| 1 | 매우 여유 | 로그정리, 통계리포트, 모델재학습 | ~24시간 | 30% |

미룰 수 있는 여유 시간(`L_max`) 안에서, **탄소가 가장 낮은 시각**을 골라 실행합니다.
단 무작정 탄소만 보지 않고, "얼마나 급한지"에 따라 탄소와 지연의 가중치를 바꿉니다.

---

## 3. 스케줄러 알고리즘 (Time-Shift)

`timeshift.py`의 `compute_time_shift()`가 핵심입니다. job 하나에 대해 다음을 계산합니다.

### 3-1. 실행 가능 윈도우

```
t_earliest = submit_time                    # 가장 빨리 시작 가능한 시각(=요청 시각)
t_latest   = deadline - duration            # 마감 지키려면 늦어도 이때는 시작
           = submit_time + L_max            # (deadline = submit + L_max + duration 이므로)
```

이 `[t_earliest, t_latest]` 구간의 1시간 단위 슬롯들이 후보가 됩니다.

### 3-2. α (알파) — 탄소 vs 지연 가중치

```
α = (6 - k) / 5
```

| k | α | 의미 |
|---|-----|------|
| 5 | 0.2 | 급함 → 지연 회피 우선 |
| 3 | 0.6 | 중간 |
| 1 | 1.0 | 여유 → 탄소 최소화 우선 |

### 3-3. 점수(score) 계산 및 최적 슬롯 선택

각 후보 시각 `t`에 대해 두 비용을 0~1로 정규화한 뒤 가중합합니다.

```
C_hat(t) = (C(t) - C_min) / (C_max - C_min)      # 탄소 비용 (그 시각 실행 시 평균 탄소강도)
D_hat(t) = (t - t_earliest) / (t_latest - t_earliest)   # 지연 비용 (얼마나 늦게 시작?)

score(t) = α · C_hat(t) + (1 - α) · D_hat(t)

t*  = argmin score(t)          # 점수가 가장 낮은 시각으로 실행
```

- 여유 있는 job(k=1, α=1.0) → 탄소만 보고 제일 깨끗한 시각으로 크게 미룸
- 급한 job(k=5, α=0.2) → 지연이 커지면 손해라 사실상 즉시 실행

### 3-4. 예외 처리 (fallback)

- `t_latest <= t_earliest` (미룰 여유 없음) → 즉시 실행
- 요청 시각이 예측 범위(24h)를 넘어감 → 즉시 실행
- 후보 슬롯이 없음 → 즉시 실행

이 구조 덕분에 **SLO(마감) 위반은 원천적으로 0** 입니다. 애초에 `t_latest`(마감 안)에서만 후보를 찾기 때문입니다.

---

## 4. 비교군 3개

같은 job 집합을 세 방식으로 각각 시뮬레이션해서 "우리 방식이 얼마나 나은지"를 분리해서 보여줍니다.
`schedule_job(job, carbon_series, mode)`의 `mode`로 전환합니다.

| 비교군 | 리전 (로드밸런서가 데이터로 제공) | 실행 시각 (스케줄러) | 역할 |
|--------|-----------|-----------|------|
| 1. 단순 LB + 즉시실행 | 원본 배정 (`region`) | 즉시 | baseline |
| 2. 탄소 LB + 즉시실행 | 탄소 인식 배정 (`배정`) | 즉시 | 리전 선택만의 효과 |
| 3. **탄소 LB + time-shift (ours)** | 탄소 인식 배정 (`배정`) | **최적 시각** | 리전 + 시간 이동 |

- 리전 선택(공간 이동)은 **로드밸런서 담당**이라, 스케줄러는 각 비교군의 리전을 데이터에서 읽기만 합니다.
- 스케줄러가 실제로 계산하는 것은 **비교군 3의 실행 시각(time-shift)** 뿐입니다.
- 2 → 3: "시간까지 옮기면" 추가로 얼마나 더 주는지 ← **우리(스케줄러) 기여분**

> 통합 대시보드의 스케줄러 화면과 CLI(`run_cli.py`) 모두 3개 비교군을 출력합니다.
> ① → ② 가 로드밸런서(공간 이동)의 기여, ② → ③ 이 스케줄러(시간 이동)의 기여입니다.

---

## 5. 측정 지표

`metrics.py`가 job 전체에 대해 집계합니다.

- **total_carbon** — 총 탄소 배출량 합계 (gCO₂)
- **avg_delay** — 평균 지연 시간 (h)
- **slo_violation_rate** — 마감 위반 비율 (정상이면 0)

job별 탄소 배출량:
```
carbon_emitted = (실행 구간의 평균 탄소강도) × duration
```

---

## 6. 데이터

### job 데이터
기본은 **2025년 1년치** — 로드밸런서와 완전히 같은 입력을 씁니다.
- `load_balancer/data/jobs.csv` — 146,000개 job (8리전 × 365일 × 50개/일, 시간 단위는 초)
- `load_balancer/framework/results/assign_alpha_auto.csv` — 로드밸런서의 **리전 배정 결과** (α=auto)

위 파일이 없을 때만 `data/job/` 의 7일치(2,800개)로 폴백합니다.
- `gen_jobs.py` — job 생성기 (SEED=42, 재현 가능, N_DAYS=7 개발용)
- `jobs.csv` · `jobs_routed_alpha_auto.csv` · `README_jobs.md` (열 정의)

스케줄러는 리전을 스스로 고르지 않습니다. 로드밸런서가 배정한 리전을 그대로 사용하며,
읽는 일은 `interface/lb_assignment.py`가 맡습니다 (`assign_*.csv` · `jobs_routed_*.csv` 모두 지원).

### 탄소강도 — `scheduler/carbon_forecast.py` → `interface/`
- **2025 검증**: `interface/carbon_2025.py` 가 `eval_records` 에서 실측(y_true, 탄소 회계)과
  발행 시각별 24h 예측(y_pred, 스케줄링 판단)을 복원합니다 — 로드밸런서와 동일 소스·시간축.
- **라이브(2026)**: `interface/carbon_forecast_api.get_forecast(t_hour)` 가 실제 LSTM 모델을 호출하고,
  torch가 없거나 이력이 부족하면 더미(사인파+노이즈)로 자동 폴백합니다. `backend_info()` 로 확인.

### 8개 리전 (LSTM zone 코드 기준으로 통일)
`US-CAL-CISO`(미 서부/캘리포니아), `US-TEX-ERCO`(미 중부/텍사스), `US-NY-NYIS`(미 동부/뉴욕),
`FR`(프랑스), `DE`(독일), `KR`(한국), `IN`(인도), `JP`(일본).

리전 이름은 모듈마다 표기가 달라서(`Korea` vs `KR` 등) `interface/regions.py`가 단일 출처로 관리합니다.
지도에서는 3개 미국 리전이 하나의 국가(USA)로 합쳐집니다 (`regions.to_iso3()`).

---

## 7. 디렉토리 구조

저장소는 담당별 최상위 폴더로 나뉘고, 그 사이는 `interface/`가 이어줍니다.

```
carbon-aware-scheduler/
├── carbon_forecast_lstm/        # LSTM 담당 (탄소강도 24h 예측)
├── load_balancer/               # 로드밸런서 담당 (어느 리전에서?)
├── interface/                   # 모듈 간 데이터 계약 ← interface/README.md 참고
│   ├── regions.py               #   리전 표기 통합 (LB 표기 ↔ LSTM 코드 ↔ ISO-3)
│   ├── carbon_forecast_api.py   #   LSTM 경계 (실모델 또는 더미)
│   └── lb_assignment.py         #   로드밸런서 배정 결과 로딩
└── scheduler/                   # ← 스케줄러(time-shift) 담당, 이 문서
    ├── README.md
    ├── run_cli.py               # 터미널에서 3개 비교군 빠르게 실행 (python -m scheduler.run_cli)
    ├── data/job/                # 7일치 폴백 job 데이터 (위 6절 참고)
    │
    ├── __init__.py              # ← scheduler 자체가 파이썬 패키지
        ├── config.py            # 비교군 정의 (리전 정의는 interface에서 가져옴)
        ├── carbon_forecast.py   # interface/carbon_forecast_api 로 위임하는 얇은 계층
        ├── data_loader.py       # job 로딩 + 로드밸런서 배정 붙이기
        ├── timeshift.py         # 핵심: α 계산, time-shift 알고리즘, 비교군 분기
        ├── simulator.py         # SimPy 이벤트 시뮬레이션 루프
        └── metrics.py           # 지표 집계·출력
```

시뮬레이션 흐름: `data_loader`가 job을 읽고 → `carbon_forecast`가 탄소 시계열을 만들고 →
`simulator`가 각 job을 `scheduler.schedule_job()`으로 처리(SimPy로 도착→대기→실행 재현) →
`metrics`가 집계 → `run_cli` / 통합 대시보드(`interface/dashboard/pages/scheduler.py`)가 출력.

---

## 8. 실행 방법

### 설치 (저장소 루트)
```bash
python -m venv venv
venv\Scripts\activate          # Windows (Git Bash: source venv/Scripts/activate)
pip install -e ".[lstm,dev]"      # pyproject — dash · simpy · torch · pytest 전부 포함
```

### 통합 대시보드 (권장)
```bash
python -m interface.dash_app
```
브라우저에서 `http://localhost:8050/scheduler` — 2025년 1년치 세 비교군 시뮬레이션이 서버 기동 시
백그라운드로 실행되고(약 1분), 끝나면 절감률·지연·SLO 위반율·k별 분석·결과 CSV가 표시됩니다.
시점별 세계지도·타임라인은 메인 화면(`/`)에 있습니다.

### 터미널 (숫자만 빠르게)
```bash
python -m scheduler.run_cli
```

---

## 9. 2025년 1년치 검증 결과

| 비교군 | 총 탄소 | 평균 지연 | SLO 위반 |
|---|---:|---:|---:|
| ① 단순 LB + 즉시 | 29.23 tCO₂ | 0 h | 0 |
| ② 탄소 LB + 즉시 | 12.61 tCO₂ | 0 h | 0 |
| ③ **탄소 LB + time-shift (ours)** | **9.96 tCO₂** | 2.06 h | **0** |

- ② → ③: time-shift 만으로 **추가 21.0 %** 절감 (2.65 tCO₂), 마감 위반 0.
- ① → ③: 공간 + 시간 이동 합쳐 **65.9 %** 절감.
- 지연은 여유 있는 job(k=1·2)에 집중되고 급한 job(k=3~5)은 사실상 즉시 실행됩니다.

---

## 10. 현재 상태 / 다음 단계

**검증된 것**
- time-shift 알고리즘이 설계대로 동작 (k별 차등 지연, SLO 위반 0)
- 2025년 1년치 실측 탄소강도 + 로드밸런서 실제 배정 위에서 추가 절감 확인

**외부 입력 (다른 담당 → 데이터로만 받음)**
- **로드밸런서** — 리전 배정 결과(`assign_alpha_auto.csv`)를 입력으로만 사용. 스케줄러 코드에 LB 알고리즘은 없음.
- **LSTM** — 2025 검증은 사전 계산된 예측(y_pred), 2026 라이브 데모는 실제 모델 호출. 둘 다 `interface/` 경유.

**다음 단계**
- 에너지 모델 정교화 (job 전력 프로파일), marginal emission factor 회계, 리전별 전력 단가를 포함한 다목적 최적화
