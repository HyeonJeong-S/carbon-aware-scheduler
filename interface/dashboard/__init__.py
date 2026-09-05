"""통합 대시보드 (Dash) 패키지.

    python interface/dash_app.py   →  http://localhost:8050

화면(페이지)은 pages/ 폴더에 하나씩 있고 Dash Pages가 자동 등록한다.
    /               메인 화면      — 세계지도 · 실행 중 job · 타임라인 (LSTM 라이브, 2026)
    /overview       전체 개요      — 파이프라인 · 모듈 연결 상태 · 리전 · 계약
    /load-balancer  로드밸런서     — 입력 데이터 · 전/후 비교 · α 스윕 · 실시간 라우팅
    /lstm           LSTM           — 리전별 24h 예측 vs 실측
    /scheduler      스케줄러       — 2025년 1년치 time-shift 검증
"""
