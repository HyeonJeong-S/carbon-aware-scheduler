"""전체 개요 — 세 모듈이 어떻게 이어지는지, 지금 무엇이 연결돼 있는지."""

import os

import dash
from dash import html

from interface import carbon_forecast_api as api
from interface.dashboard import data, theme
from interface.dashboard import live as core
from interface.regions import REGIONS, label

dash.register_page(__name__, path="/overview", name="전체 개요", order=1)


def _stage(title, sub, ok, detail):
    pill = html.Span("연결됨" if ok else "미연결", className=f"pill {'pill-ok' if ok else 'pill-warn'}")
    return html.Div([
        html.Div([html.B(title), html.Span(" ", ), pill]),
        html.Div(sub, className="subtle", style={"fontSize": "0.85rem", "margin": "0.2rem 0 0.4rem"}),
        html.Div(detail, className="caption"),
    ], className="card col-1")


def layout(**_):
    st = api.status()
    lb_ok = os.path.exists(data.YEAR_ASSIGN_CSV) and data.lb_results_available()
    val = data.validation_state()

    if lb_ok:
        s = data.lb_load_all()["summary"]
        base, auto = s["baseline"]["metrics"], s.get("alpha_auto", {}).get("metrics")
    else:
        base = auto = None

    lstm_detail = api.backend_info()
    if st["ready"]:
        lstm_detail += (f" · 예측 가능 {core.WINDOW_START:%Y-%m-%d} ~ {core.WINDOW_END:%Y-%m-%d} "
                        "(2026 라이브 이력, 날씨 리전은 예측 구간 24h 날씨가 필요해 이력 끝-24h까지)")

    sched_detail = data.validation_detail(val)

    result_rows = None
    if base and auto:
        result_rows = theme.md(
            "| 지표 | Baseline (홈 리전 즉시 실행) | CAST 로드밸런서 (α-auto) | 변화 |\n|---|---:|---:|---:|\n"
            f"| 총 탄소 배출 | {base['total_carbon_kg']:,.1f} kg | **{auto['total_carbon_kg']:,.1f} kg** | "
            f"**{(auto['total_carbon_kg'] / base['total_carbon_kg'] - 1) * 100:+.1f} %** |\n"
            f"| 평균 네트워크 지연 | {base['avg_latency_ms']:.1f} ms | {auto['avg_latency_ms']:.1f} ms | "
            f"+{auto['avg_latency_ms'] - base['avg_latency_ms']:.1f} ms |\n"
            f"| p95 지연 | {base['p95_latency_ms']:.0f} ms | {auto['p95_latency_ms']:.0f} ms | — |\n"
            f"| 드롭된 job | {base['dropped']} | {auto['dropped']} | — |\n"
            f"| 홈 리전 처리 비율 | {base['home_ratio'] * 100:.1f} % | {auto['home_ratio'] * 100:.1f} % | "
            f"{(auto['home_ratio'] - base['home_ratio']) * 100:+.1f} pp |")
        if val["status"] == "done":
            c = val["comparison"]
            imm = c["carbon_lb_immediate"]["total_carbon"]
            sh = c["carbon_lb_timeshift"]["total_carbon"]
            result_rows = html.Div([
                result_rows,
                theme.caption(
                    f"여기에 스케줄러의 시간 이동을 더하면 같은 리전 배정 위에서 추가로 "
                    f"{(1 - sh / imm) * 100:.1f}% 를 더 줄인다 "
                    f"({imm / 1e6:,.2f} → {sh / 1e6:,.2f} tCO₂, SLO 위반 "
                    f"{c['carbon_lb_timeshift']['slo_violation_rate'] * 100:.2f}%). 스케줄러 화면 참고."),
            ])

    return html.Div([
        html.H1("Carbon-Aware Scheduler"),
        theme.caption("탄소가 낮은 리전(공간)과 시간대(시간)로 job을 옮겨 실행하는 시스템 — "
                      "예측(LSTM) → 공간 이동(ILP 로드밸런서) → 시간 이동(Time-Shift 스케줄러)"),

        theme.section("파이프라인", html.Div([
            _stage("① LSTM 탄소강도 예측", "리전별 향후 24h 탄소강도 → {region: [24 × gCO₂/kWh]}",
                   st["ready"], lstm_detail),
            html.Div("▶", style={"alignSelf": "center", "color": "#aaa", "fontSize": "1.4rem"}),
            _stage("② 로드밸런서 (어느 리전?)", "1시간 슬롯마다 ILP 배정, 파레토 무릎점 α 자동 선택",
                   lb_ok, "results/assign_alpha_auto.csv 를 스케줄러가 그대로 사용"
                   if lb_ok else "results/summary.json 없음 — 로드밸런서 화면에서 실험을 실행하세요"),
            html.Div("▶", style={"alignSelf": "center", "color": "#aaa", "fontSize": "1.4rem"}),
            _stage("③ 스케줄러 (언제 실행?)", "L_max 안에서 탄소·지연 가중 score 최소 시각 선택 (SLO 위반 0)",
                   val["status"] != "error", sched_detail),
        ], className="row")),

        theme.section("핵심 결과 — 8개 리전 × 146,000 jobs × 1년(2025) 실측 탄소강도",
                      result_rows or theme.notice("로드밸런서 결과가 없어 표시할 수 없습니다.", "warn")),

        theme.section("시간축 두 개", theme.md(
            "| 축 | t = 0 | 쓰는 곳 | 데이터 |\n|---|---|---|---|\n"
            "| **2025** | 2025-01-01 00:00 UTC | 로드밸런서 1년 실험 · 스케줄러 검증 | "
            "`lstm_eval/*_eval_records.csv` (실측 y_true + LSTM 사전계산 y_pred) |\n"
            "| **2026** | 2026-01-01 00:00 UTC | 메인 화면 · LSTM 화면 · 실시간 라우팅 | "
            "`carbon_intensity_demo.csv` (실측 이력) 위에서 **LSTM 모델을 그 자리에서 호출** |\n\n"
            "두 축 모두 job 워크로드는 같은 `jobs.csv`(146,000개, 초 단위 UTC 절대축)를 쓴다.")),

        theme.section("리전 (8개)",
                      html.Div([html.Div([html.Code(r), f" — {label(r)}"], className="col-1",
                                         style={"padding": "0.2rem 0"}) for r in REGIONS],
                               style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)"}),
                      caption="모듈마다 표기가 달라(Korea / KR / KOR) interface/regions.py 가 표준 코드로 통일한다."),

        theme.details("모듈 간 계약 요약", theme.md(
            "| 주는 쪽 | 받는 쪽 | 내용 | 형식 |\n|---|---|---|---|\n"
            "| LSTM | 로드밸런서 · 스케줄러 | 리전별 향후 24h 탄소강도 | `{리전: [24개 float]}` gCO₂/kWh |\n"
            "| 로드밸런서 | 스케줄러 | job별 실행 리전 | `{job_name: {origin, assigned}}` |\n"
            "| 스케줄러 | (결과) | job별 실행 시각·배출량 | `scheduled_start`, `carbon_emitted`, `slo_satisfied` |\n\n"
            "자세한 내용은 `interface/README.md` 참고.")),
    ])
