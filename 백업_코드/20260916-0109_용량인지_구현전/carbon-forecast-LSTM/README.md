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
carbon-forecast-LSTM/
├── carbon_forecast.py     # 핵심 모듈 — 모델 정의 + 로드 + 예측 인터페이스
├── requirements.txt
├── models/                # 8개 리전 LSTM 가중치(.pt) + scaler(.pkl)
├── models_demo/           # models/와 동일한 구조의 별도 가중치 세트
│                          #   (현재 코드에서 직접 참조되진 않음)
├── data/
│   └── carbon_intensity_demo.csv          # 8리전 통합 실측 시계열
│                                           #   예측 입력으로 쓰이는 데이터 (시뮬레이터·carbon_forecast_api가 로드)
└── logs/
    └── {region}_eval_records_{2025,2026}.csv
                                            # LSTM으로 돌린 리전별 롤링 예측 결과 (연도별)
```

`{region}_eval_records_*.csv` 컬럼: `timestamp, horizon, y_true, y_pred, abs_err`
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
pip install -r requirements.txt
```

## 사용법

```python
from carbon_forecast import load_all_models, get_forecast_at
import pandas as pd

models, scalers, weather_scalers = load_all_models('./models')

result = get_forecast_at(
    t=pd.Timestamp('2025-03-15 14:00'),
    models=models,
    scalers=scalers,
    all_df=carbon_df,
    # 필수 컬럼: timestamp, region, carbon_intensity, cfe_pct, re_pct
    # WEATHER_REGIONS(US-TEX-ERCO, US-CAL-CISO, DE)는
    # wind_speed_10m, shortwave_radiation, temperature_2m도 필수
    weather_scalers=weather_scalers
)
# result['forecast']['KR'] = [24개 예측값, gCO₂/kWh]
```
