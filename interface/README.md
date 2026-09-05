# interface — 모듈 간 데이터 계약 + 통합 대시보드

이 프로젝트는 담당이 3개로 나뉘어 있고, 각자 자기 폴더에서 독립적으로 작업합니다.

```
carbon_forecast_lstm/   탄소강도 24시간 예측        (LSTM 담당)
load_balancer/          어느 리전에서 실행할지       (로드밸런서 담당)
scheduler/              그 리전에서 언제 실행할지     (스케줄러 담당)
interface/              ← 위 셋을 이어주는 계약 계층 + Dash 대시보드
```

모듈끼리 서로의 내부 구현(모델 구조, 최적화 알고리즘 등)을 알 필요가 없도록,
**주고받는 데이터의 형식과 이름만** 이 폴더에 모아둡니다.
한쪽 구현이 바뀌어도 여기 계약만 지키면 나머지는 건드릴 필요가 없습니다.

---

## 데이터 흐름

```
[LSTM]  ──리전별 24h 예측──▶  carbon_forecast_api  ──▶  [로드밸런서] · [스케줄러]
                                                              │
[로드밸런서]  ──job별 배정 리전──▶  lb_assignment  ──────────▶  [스케줄러]
```

---

## 0. 통합 대시보드 (Dash)

```bash
python -m interface.dash_app        # → http://localhost:8050   (--port, --debug 옵션)
```

| 화면 | 경로 | 파일 | 시간축 |
|---|---|---|---|
| 메인 화면 | `/` | `dashboard/pages/main.py` (+ `live.py`) | 2026 라이브 |
| 전체 개요 | `/overview` | `dashboard/pages/overview.py` | — |
| 로드밸런서 | `/load-balancer` | `dashboard/pages/load_balancer.py` | ①~③ 2025 · ④ 2026 라이브 |
| LSTM | `/lstm` | `dashboard/pages/lstm.py` | 2026 라이브 |
| 스케줄러 | `/scheduler` | `dashboard/pages/scheduler.py` | 2025 |

```
interface/
├── dash_app.py            진입점 (create_app → app.run) — `cast-dashboard` 콘솔 스크립트
└── dashboard/
    ├── app.py             Dash(use_pages=True) + 상단 내비게이션
    ├── data.py            무거운 데이터 로더 (LB 결과 · 스케줄러 검증 백그라운드 실행 · 실시간 라우팅 · 실험 재실행)
    ├── live.py            메인 화면 계산 로직 (지도 · 타임라인 · 누적 탄소, 2026 라이브 축)
    ├── theme.py           색 · plotly 레이아웃 · KPI/섹션/표 조각 (리전 색의 단일 출처)
    ├── assets/style.css   공통 CSS (Dash가 자동 서빙)
    ├── pages/             화면 5개 (Dash Pages 자동 등록)
    └── lb_tabs/           로드밸런서 화면의 탭 4개 + 실험 재실행 블록
```

- 서버가 뜨면 백그라운드에서 LSTM 모델 로드 · 146k job 로드 · 스케줄러 검증(약 1분)을 미리 돌려둔다.
- 무거운 계산은 `functools.lru_cache` 로 프로세스 안에 한 번만 캐시된다.
- 로드밸런서의 "실험 다시 실행"은 `run_experiments.py` 를 별도 프로세스로 띄우고 로그를 폴링한다 (~40분).

### 시간축 두 개

| 축 | t = 0 | 쓰는 곳 | 데이터 |
|---|---|---|---|
| **2025** | 2025-01-01 00:00 UTC | 로드밸런서 1년 실험 · 스케줄러 검증 | `load_balancer/data/lstm_eval/*_eval_records.csv` (실측 y_true + LSTM 사전계산 y_pred) |
| **2026** | 2026-01-01 00:00 UTC | 메인 화면 · LSTM 화면 · 실시간 라우팅 | `carbon_forecast_lstm/data/carbon_intensity_demo.csv` 위에서 LSTM 모델을 그 자리에서 호출 |

두 축 모두 job 워크로드는 같은 `jobs.csv`(146,000개, 초 단위 UTC 절대축)를 쓴다.

---

## 1. `regions.py` — 리전 표기 통합

같은 리전을 세 모듈이 **다른 이름**으로 부르고 있었습니다. 이게 가장 큰 연결 문제였습니다.

| 리전 | 로드밸런서 | LSTM | 표준(채택) |
|---|---|---|---|
| 미 서부 | `US_West` | `US-CAL-CISO` | `US-CAL-CISO` |
| 미 중부 | `US_Central` | `US-TEX-ERCO` | `US-TEX-ERCO` |
| 미 동부 | `US_East` | `US-NY-NYIS` | `US-NY-NYIS` |
| 프랑스 | `France` | `FR` | `FR` |
| 독일 | `Germany` | `DE` | `DE` |
| 한국 | `Korea` | `KR` | `KR` |
| 인도 | `India` | `IN` | `IN` |
| 일본 | `Japan` | `JP` | `JP` |

**표준은 LSTM의 zone 코드를 따릅니다.** LSTM이 실제 학습된 모델 파일을 그 코드로
저장해두었기 때문입니다 (`carbon_forecast_lstm/models/KR_lstm.pt` 등).

```python
from interface.regions import REGIONS, to_region, to_iso3, label

to_region("Korea")        # -> "KR"     (로드밸런서 표기)
to_region("KR")           # -> "KR"     (이미 표준)
to_region("IN-NO")        # -> "IN"     (과거 스케줄러 코드도 호환)
to_iso3("KR")             # -> "KOR"    (지도용 국가코드, 미국 3리전은 모두 USA)
label("US-NY-NYIS")       # -> "US East (New York)"
```

---

## 2. `carbon_forecast_api.py` — LSTM 경계

스케줄러는 torch·scaler·168시간 입력 같은 LSTM 내부를 몰라야 합니다. 이 함수 하나만 씁니다.

```python
from interface import carbon_forecast_api

forecast = carbon_forecast_api.get_forecast(t_hour=12, horizon=24)
# -> {"KR": [24개 값], "FR": [...], ...}   단위 gCO₂/kWh, index 0 = 기준 시각
```

**2단계 자동 폴백**으로 동작합니다. 모델 로딩(수 초~십수 초)은 import 시점이 아니라
**첫 호출 때** 한 번 일어납니다 — `interface.regions` 만 쓰는 쪽이 로딩 비용을 떠안지 않게 하기 위해서입니다.

1. **실제 LSTM** — torch 설치 + `models/*.pt` 존재 + 요청 시점 t 이전 **168시간 이력**이 있으면 진짜 예측
   (날씨 리전 3곳은 예측 구간 t~t+23h 의 날씨도 있어야 하므로 이력 끝-24h 까지)
2. **더미** — 위 조건이 안 되면 사인파 + 노이즈

호출마다 어느 쪽이 응답했는지 `last_backend()`로 확인할 수 있습니다.

```python
carbon_forecast_api.backend_info()   # 전반적인 연결 상태
carbon_forecast_api.last_backend()   # 'lstm' | 'dummy'  ← 방금 그 호출이 쓴 백엔드
carbon_forecast_api.status()         # 예측 가능 구간 등 상세
```

> LSTM 쪽 원래 시그니처는 `get_forecast_at(t, models, scalers, all_df, weather_scalers)` 이며,
> 이 어댑터가 그 호출과 리전 코드 변환을 대신 처리합니다.

### 입력 이력 — `carbon_history.py`

LSTM은 t 이전 168시간의 `carbon_intensity` + `cfe_pct` + `re_pct` (+ 날씨 리전은 `wind_speed_10m`,
`shortwave_radiation`, `temperature_2m`) 를 요구합니다.

| 컬럼 | 현재 출처 |
|---|---|
| 전부 | `carbon_forecast_lstm/data/carbon_intensity_demo.csv` — 2026-01-01 ~ 07-20 실측 (`is_placeholder=False`) |

cfe/re 가 없는 CSV 나 더미 시계열로 이력을 만들 때는 탄소강도로부터 역산한 **임시 추정값**을 넣고
`is_placeholder=True` 로 표시합니다. `load_actual_series()` 는 같은 파일에서 **탄소 회계용 실측 시계열**을 만듭니다.

### 2025 사전계산 — `carbon_2025.py`

로드밸런서의 1년 실험과 스케줄러 검증은 **같은 `eval_records`** 를 씁니다.
한 행 = (예측 대상 시각, horizon, y_true, y_pred) 이므로 발행 시각 = timestamp − horizon 으로
"t 시점에 알 수 있었던 향후 24시간 예측"을 그대로 복원합니다. 1월 1~7일은 1월 8일 프로파일 반복(합의 규약).

---

## 3. `lb_assignment.py` — 로드밸런서 경계

로드밸런서가 job별로 "어느 리전에서 돌릴지" 정한 결과를 읽습니다.
**스케줄러는 리전을 스스로 고르지 않습니다.**

지원 형식 3가지 (자동 인식):

| | 파일 | 원본 리전 | 배정 리전 |
|---|---|---|---|
| A | `load_balancer/framework/results/assign_*.csv` | `origin` | `assigned` |
| B | `scheduler/data/job/jobs_routed_alpha_auto.csv` | `region` | `배정` |
| C | `load_balancer/routed/jobs_routed_*.csv` | `region` | `assigned_region` |

```python
from interface.lb_assignment import load_assignments, attach_to_jobs

a = load_assignments("…/assign_alpha_auto.csv")
# -> {"j_002120": {"origin": "IN", "assigned": "FR"}, …}

attach_to_jobs(jobs, a)
# job["region"]        <- origin    (비교군1 baseline)
# job["carbon_region"] <- assigned  (비교군2·3)
```

---

## 계약 요약

| 주는 쪽 | 받는 쪽 | 내용 | 형식 |
|---|---|---|---|
| LSTM | 로드밸런서·스케줄러 | 리전별 향후 24h 탄소강도 | `{리전: [24개 float]}` gCO₂/kWh |
| 로드밸런서 | 스케줄러 | job별 실행 리전 | `{job_name: {origin, assigned}}` |
| 스케줄러 | (결과) | job별 실행 시각·배출량 | `scheduled_start`, `carbon_emitted`, `slo_satisfied` |

리전 이름은 **모든 경계에서 `regions.to_region()`을 거쳐 표준 코드로 정규화**됩니다.
