# Carbon Forecast Module (LSTM)

8개 리전(KR, US-CAL-CISO, US-TEX-ERCO, US-NY-NYIS, FR, DE, IN, JP)의
향후 24시간 탄소강도(gCO₂/kWh)를 예측하는 LSTM 인터페이스 모듈입니다.

스케줄러/로드밸런서가 `carbon_forecast.py`를 직접 import해서 쓰는 독립 모듈이며,
이 저장소 안에서는 `interface/carbon_forecast_api.py`가 이 모듈을 감싸
스케줄러 쪽에 `get_forecast(t_hour, horizon=24)` 형태로 노출합니다
(168시간 이력이 없거나 torch 로드가 실패하면 더미 백엔드로 자동 폴백).

- Train: 2021~2023 / Val: 2024 / Test: 2025 (rolling-forecast 평가)

---

## 디렉터리 구조

```
carbon_forecast_lstm/
├── carbon_forecast.py     # 핵심 모듈 — 모델 정의 + 로드 + 예측 인터페이스
├── requirements.txt
├── models/                # 8개 리전 LSTM 가중치(.pt) + scaler(.pkl)
├── models_demo/           # models/와 동일한 구조의 별도 가중치 세트
│                          #   (현재 코드에서 직접 참조되진 않음)
├── data/
│   └── carbon_intensity_demo.csv          # 8리전 통합 실측 시계열
│                                           #   예측 입력으로 쓰이는 데이터 (시뮬레이터·carbon_forecast_api가 로드)
└── logs/
    └── {region}_eval_records.csv           # 2025년 rolling-forecast 평가 기록
                                            #   (로드밸런서/스케줄러가 읽는 원본은
                                            #    ../load_balancer/data/lstm_eval/ 쪽)
```

`{region}_eval_records.csv` 컬럼: `timestamp, horizon, y_true, y_pred, abs_err`
(예측 시점별 · horizon(1~24h)별 실제값·예측값·절대오차)

---

## 동작 방식

### 1. 모델 구조

- **`CarbonLSTM`**: 2-layer LSTM(hidden=64) + Linear 1개. 과거 168시간 입력 → 향후 24시간 출력.
- **`CarbonLSTMWithFutureWeather`**: `CarbonLSTM`을 상속. 날씨 데이터가 있는 3개 리전
  (`WEATHER_REGIONS` = US-TEX-ERCO, US-CAL-CISO, DE) 전용 모델로, LSTM의 last_hidden에
  예측 구간(향후 24h)의 날씨 값을 concat한 뒤 출력층에 반영한다.
- 나머지 5개 리전(KR, US-NY-NYIS, FR, IN, JP)은 `CarbonLSTM`만 사용.

### 2. 입력 피처 (`get_feature_cols(region)`)

- 공통 10개(`BASE_FEATURE_COLS`): `carbon_intensity`, `cfe_pct_norm`, `re_pct_norm`,
  sin/cos(hour, dayofweek, month), `is_holiday`
- `WEATHER_REGIONS` 3개 리전은 3개 추가(`WEATHER_FEATURE_COLS`):
  `wind_speed_10m_norm`, `shortwave_radiation_norm`, `temperature_2m_norm` → 총 13개
- 시간 피처(sin/cos·is_holiday)는 `timestamp`만 있으면 `_add_time_features()`가 자동 생성한다.
  공휴일은 리전별 국가 코드(`HOLIDAY_CODES`)로 `holidays` 패키지에서 조회.
- `cfe_pct`/`re_pct`, 날씨 원본값은 실측치라 timestamp만으로는 자동 생성이 불가능하며
  호출자(데이터 파이프라인)가 반드시 공급해야 한다.

### 3. 예측 파이프라인 (`predict_region`)

1. 입력 168시간에 시간 피처 결합, `cfe_pct_norm`/`re_pct_norm` 존재 확인
2. `scaler`(MinMaxScaler)로 `carbon_intensity` 정규화
3. `WEATHER_REGIONS`면 `weather_scaler`로 날씨 원본값 정규화
4. 모델 추론 — `WEATHER_REGIONS`는 예측 구간(t~t+23h) 날씨도 함께 입력
5. 출력을 `scaler`로 역정규화 → gCO₂/kWh 실제값 24개 반환

### 4. 함수 계층

| 함수 | 역할 |
|---|---|
| `load_all_models(model_dir)` | 8리전 모델/scaler/weather_scaler 로드 |
| `predict_region(...)` | 리전 1개 예측 (저수준) |
| `get_carbon_forecast(...)` | 8리전 전체 예측 — `region_data`를 직접 넘김 (실서비스용) |
| `get_forecast_at(t, ...)` | `all_df`에서 t 이전 168h(+`WEATHER_REGIONS`는 t~t+23h 날씨)를 자동 슬라이싱해 `get_carbon_forecast` 호출 (시뮬레이터·백테스트용) |

### 5. 반환 형식

```json
{
  "generated_at": "2025-03-15T14:00:00",
  "forecast": {
    "KR": [352.1, 348.9, ..., 310.2],
    "FR": [78.3, 76.1, ..., 82.4]
  }
}
```

- `index 0` = 요청 시각 t 자체의 예측값 (t+1이 아님), `index 23` = t로부터 23시간 후
- 단위: gCO₂/kWh

---

## 설치

```bash
pip install -r requirements.txt        # 저장소 루트의 requirements.txt 에 이미 포함되어 있음
```

## 데이터

| 파일 | 내용 |
|---|---|
| `data/carbon_intensity_demo.csv` | 2026-01-01 ~ 2026-07-20 실측 이력 (8리전 × 시간별, cfe/re/날씨 포함) — 통합 대시보드의 **라이브 LSTM 입력** |
| `../load_balancer/data/lstm_eval/{region}_eval_records.csv` | 2025년 rolling-forecast 평가 기록 (timestamp, horizon, y_true, y_pred) — 로드밸런서 1년 실험 · 스케줄러 검증의 단일 출처 (이 폴더에 두던 사본은 중복이라 제거) |
| `models/` | 배포 모델 (검증용 최종) · `models_demo/` 데모용 모델 (2026 H1) |

---

## B (스케줄러) 사용법

```python
from carbon_forecast_lstm.carbon_forecast import get_forecast_at, load_all_models
import pandas as pd

models, scalers, weather_scalers = load_all_models('./models')

result = get_forecast_at(
    t=pd.Timestamp('2025-03-15 14:00'),
    models=models,
    scalers=scalers,
    all_df=carbon_df,
    # 필수 컬럼: timestamp, region, carbon_intensity, cfe_pct, re_pct
    # US-TEX-ERCO, US-CAL-CISO, DE는 wind_speed_10m, shortwave_radiation, temperature_2m도 필수
    weather_scalers=weather_scalers,
)
# result['forecast']['KR'] = [24개 예측값, gCO₂/kWh]
```

### 반환 형식

```json
{
  "generated_at": "2025-03-15T14:00:00",
  "forecast": {
    "KR": [352.1, 348.9, ..., 310.2],
    "FR": [78.3, 76.1, ..., 82.4],
    ...
  }
}
```

---

## 주의사항

- **index 0 = 요청 시각 t 시점 자체의 예측값** (t+1이 아님)
  `index 23` = t로부터 23시간 후
- `all_df`에는 **`cfe_pct`, `re_pct` 원본 컬럼이 반드시 포함**되어야 합니다.
  (timestamp만으로는 자동 생성 불가능한 실측값이라 C의 데이터 파이프라인에서 공급)
- `all_df`에서 `US-TEX-ERCO`, `US-CAL-CISO`, `DE` 리전은 **`wind_speed_10m`, `shortwave_radiation`,
  `temperature_2m` 원본 컬럼도 반드시 포함**되어야 합니다 (날씨 피처로 학습된 모델이라 없으면 예측 실패).
  이 리전들은 예측 구간(t ~ t+23h)의 날씨도 필요하므로, `all_df`가 그 구간까지 커버해야 합니다
  (= 예측 가능한 마지막 시각은 데이터 끝 − 24h).
  이 3개 리전 중 하나라도 컬럼이 없으면 해당 호출은 예외가 발생하고,
  `carbon_forecast_api.get_forecast()`는 8개 리전 전체를 더미로 폴백시킵니다.
- 예측 시점 `t` 기준 **이전 168시간(1주일)** 데이터가 `all_df`에 있어야 합니다.
  데이터 시작일 기준으로는 `시작일 + 168시간` 이후부터 예측 가능합니다.
  (예: test가 2025-01-01부터 시작하면 2025-01-08 00:00 이후로 예측 요청)
- 리전 키는 `carbon_forecast.py`의 `REGIONS` 딕셔너리 기준입니다:
  `KR, US-CAL-CISO, US-TEX-ERCO, US-NY-NYIS, FR, DE, IN, JP`

---

## 배포 체크리스트

- [ ] Drive에서 `models/` 폴더 통째로 다운로드 (`{region}_weather_scaler.pkl` 3개 포함)
- [ ] `carbon_forecast.py`의 `REGIONS` 키가 실제 모델 파일명과 일치하는지 확인
- [ ] `BASE_INPUT_SIZE = 10` 반영됐는지 확인 (cfe_pct_norm, re_pct_norm 포함)
- [ ] `WEATHER_REGIONS` 3개 리전은 입력 13 (`get_input_size(region)`)인지 확인
- [ ] 로컬(VSCode 등)에서 `load_all_models()` 한 번 실행해 에러 없는지 확인 후 push
      — `carbon_forecast.py`는 코랩이 아닌 환경에서 처음 돌아가는 코드이므로
        push 전 로드 테스트 필수
