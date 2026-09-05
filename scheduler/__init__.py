"""탄소 인식 time-shift 스케줄러 패키지.

    timeshift     : 핵심 알고리즘 — 실행 가능 윈도우 안에서 탄소·지연 가중 score 최소 슬롯 선택
    simulator     : SimPy 이벤트 루프 (도착 → 대기 → 실행)
    metrics       : 총 탄소 · 평균 지연 · SLO 위반율 집계
    data_loader   : jobs.csv + 로드밸런서 배정 결과 로딩
    carbon_forecast: 탄소강도 예측/실측 접근 (interface/ 로 위임)
    config        : 비교군 정의 등 상수

리전 정의와 모듈 간 데이터 계약은 저장소 루트의 interface/ 패키지가 단일 출처다.
"""
