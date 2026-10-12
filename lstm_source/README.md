# LSTM 학습 원본

`carbon_forecast_lstm/` 이 **쓰는 쪽**(추론 인터페이스와 배포 모델)이라면,
여기는 그 모델을 **만든 쪽**이다. 논문 부록 B 가 가리키는 학습 조건의 출처다.

## 들어 있는 것

| 경로 | 내용 |
|---|---|
| `5[hard_stop]Carbon_Forecast_LSTM.ipynb` | 학습 코드 전부 — 전처리·정규화·데이터셋·모델·학습 루프·평가 |
| `logs/training_summary.json` | 리전별 최적 epoch · best val MAE · 학습 시간 |
| `logs/evaluation_overall.json` | 리전별 MAE / RMSE / MAPE (시험 구간 2025년) |
| `logs/evaluation_patterns.json` | 예측 지평·시각·요일·계절별 MAE |
| `logs/*.png` | 학습 점검 그림 6장 |

## 핵심 설정 (노트북에서 그대로)

- 분할: 학습 2021–2023 · 검증 2024 · 시험 2025 — **연도 단위**라 시간 순서가 지켜진다
- 정규화: MinMaxScaler(0,1), **학습 구간으로만 적합** 후 검증·시험은 transform
- 모델: 2층 LSTM(은닉 64, dropout 0.2) → Linear(64 → 24). 과거 168시간 → 향후 24시간
- 피처: 공통 10개. 캘리포니아·텍사스·독일은 기상 3개가 더해져 13개이며,
  예측 구간(향후 24h)의 기상도 출력층에 concat 된다
- 손실: 정규화 값의 MSE. 다만 **best 모델은 역변환한 MAE 로 고른다**
- 최적화: Adam(lr 1e-3, weight decay 1e-4), 기울기 노름 1.0 에서 clip
- 조기 종료: 최대 150 epoch, patience 15 + 최적 epoch 로부터 30 epoch(hard),
  최소 20 epoch 전에는 멈추지 않음. ReduceLROnPlateau(factor 0.5, patience 8)
- 시드 42

## 빠져 있는 것과 그 이유

`.gitignore` 참조. `data/`(42MB)·`models/`(2MB)·`logs/*_eval_records.csv`(80MB)는
다른 곳에 같은 파일이 있거나 노트북이 다시 만든다. 전부 넣으면 114MB 라 뺐다.

- 모델 가중치 → `carbon_forecast_lstm/models/` (바이트 단위로 동일)
- 평가 기록 → `load_balancer/data/lstm_eval/` (바이트 단위로 동일, 논문의 단일 출처)

## 주의

노트북 주석에 "날씨 피처 2개가 추가됨"이라고 적힌 곳이 있는데 **실제로는 3개**다
(기온을 나중에 넣고 주석을 안 고친 흔적). 저장된 가중치의 `input_size` 가 13 이므로
논문 쪽(공통 10 + 기상 3)이 맞다.
