"""모듈 간 인터페이스 계층.

3개 모듈(LSTM · 로드밸런서 · 스케줄러)이 서로의 내부 구현을 몰라도 되도록,
데이터 계약과 표기 변환을 이 패키지 한 곳에 모아둔다.

    regions             : 리전 표기 통합 (LB 표기 ↔ LSTM/표준 코드 ↔ ISO-3)
    carbon_forecast_api : LSTM 예측 경계 (실모델 또는 더미)
    carbon_2025         : 2025년 사전계산 예측/실측 (eval_records)
    carbon_history      : LSTM 입력 이력 · 실측 시계열 로딩
    lb_assignment       : 로드밸런서 배정 결과 로딩
    dashboard           : 통합 대시보드 (Dash)

하위 모듈은 여기서 미리 import하지 않는다 — `interface.regions`만 쓰는 쪽(스케줄러 config 등)이
LSTM 모델 로딩(수 초~십수 초)을 떠안지 않게 하기 위해서다. 필요한 모듈을 직접 import한다:

    from interface import carbon_forecast_api
    from interface.regions import to_region
"""
