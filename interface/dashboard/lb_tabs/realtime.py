"""④ 실시간 라우팅 — 매 프레임 실제 LSTM 모델이 24h 예측을 새로 계산하고 ILP가 그 자리에서 배정 (2026 축)."""

import json

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from interface.dashboard import data, theme
from interface.dashboard.lb_tabs.common import RC, R

SPEEDS = {"0.5×": 4000, "1×": 2000, "2×": 1000, "4×": 400}   # 배속 → 슬롯당 ms
DEFAULT_T = 200
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def render(_d: dict) -> html.Div:
    t_min, t_max = data.rt_t_range()
    marks = {t: (data.RT_BASE + pd.Timedelta(hours=t)).strftime("%m-%d") for t in range(t_min, t_max + 1, 24 * 30)}
    return html.Div([
        theme.caption("①~③탭은 사전 계산된 1년치(2025) 결과지만, 이 탭은 매 프레임 실제 LSTM 모델(torch)이 2026 데모 "
                      "데이터로 24시간 예측을 새로 계산하고 ILP가 그 자리에서 배정한다. ▶ 재생을 누르면 1시간 슬롯씩 자동 진행."),
        dcc.Interval(id="lb-rt-tick", interval=2000, n_intervals=0, disabled=True),
        html.Div([
            html.Div([html.Label(f"슬롯 시각 t (시간) — t=0 ↔ 2026-01-01 00:00 UTC, LSTM은 이력 168h 이후({t_min})부터 "
                                 f"데모 데이터 끝-24h({t_max})까지"),
                      dcc.Slider(id="lb-rt-t", min=t_min, max=t_max, step=1, value=DEFAULT_T, marks=marks,
                                 tooltip={"placement": "bottom", "always_visible": True})], className="col-3"),
            html.Div([html.Label("α (탄소↔지연)"),
                      dcc.Dropdown(id="lb-rt-alpha", clearable=False, searchable=False, value="auto",
                                   options=[{"label": a, "value": a} for a in ["auto", "0", "0.25", "0.5", "0.75", "1"]])],
                     className="col-1"),
            html.Div([html.Label("재생 배속"),
                      dcc.Dropdown(id="lb-rt-speed", clearable=False, searchable=False, value="1×",
                                   options=[{"label": k, "value": k} for k in SPEEDS])], className="col-1"),
            html.Div([html.Label(" "), html.Button("▶ 재생", id="lb-rt-play", n_clicks=0,
                                                    className="btn btn-primary", style={"width": "100%"})],
                     className="col-1"),
        ], className="row", style={"alignItems": "flex-end"}),
        dcc.Loading(html.Div(id="lb-rt-body"), type="dot", delay_show=200),
    ])


@callback(Output("lb-rt-tick", "disabled"), Output("lb-rt-play", "children"),
          Input("lb-rt-play", "n_clicks"), State("lb-rt-tick", "disabled"), prevent_initial_call=True)
def toggle(_n, disabled):
    playing = disabled  # 눌렀으니 반전
    return (not playing), ("⏸ 일시정지" if playing else "▶ 재생")


@callback(Output("lb-rt-tick", "interval"), Input("lb-rt-speed", "value"))
def speed(value):
    return SPEEDS.get(value, 2000)


@callback(Output("lb-rt-t", "value"), Output("lb-rt-tick", "disabled", allow_duplicate=True),
          Output("lb-rt-play", "children", allow_duplicate=True),
          Input("lb-rt-tick", "n_intervals"), State("lb-rt-t", "value"), State("lb-rt-t", "max"),
          prevent_initial_call=True)
def advance(_n, t, t_max):
    if t is None or t >= t_max:
        return dash.no_update, True, "▶ 재생"
    return t + 1, dash.no_update, dash.no_update


@callback(Output("lb-rt-body", "children"), Input("lb-rt-t", "value"), Input("lb-rt-alpha", "value"))
def body(t, alpha):
    t = int(t or DEFAULT_T)
    res = data.realtime_route_slot(t, alpha)
    s = res["summary"]
    now = data.RT_BASE + pd.Timedelta(hours=t)
    backend_ok = res["forecast_backend"] == "lstm"

    fx = [data.RT_BASE + pd.Timedelta(hours=t + h) for h in range(24)]
    ff = theme.base_fig(height=380, legend=dict(orientation="h", y=1.15), yaxis_title="gCO₂/kWh (LSTM 예측)")
    for r in R:
        ff.add_trace(go.Scatter(x=fx, y=res["forecast_gco2_per_kwh"][r], name=r, mode="lines",
                                line=dict(color=RC[r], width=2),
                                hovertemplate=f"{r}: %{{y:.0f}} g/kWh<br>%{{x|%m-%d %H시}}<extra></extra>"))
    load = s["region_load"]
    lf = theme.base_fig(height=380, yaxis_title="배정 job 수", showlegend=False)
    lf.add_trace(go.Bar(x=R, y=[load[r] for r in R], marker_color=[RC[r] for r in R],
                        hovertemplate="%{x}: %{y}개<extra></extra>"))

    adf = pd.DataFrame(res["assignments"])
    if adf.empty:
        assign_block = theme.caption("이 슬롯에 제출된 job이 없습니다 — 예측만 발행됨.")
    else:
        moved = adf[adf.origin != adf.assigned]
        assign_block = html.Div([theme.caption(f"{len(adf)}개 중 {len(moved)}개가 홈 리전 밖으로 이동"),
                                 theme.table(adf, page_size=15)])

    return html.Div([
        html.H2(f"🕐 {now.year}년 {now.month}월 {now.day}일({WEEKDAYS[now.dayofweek]}) {now:%H:%M} UTC · t={t}"),
        theme.kpi_row(
            theme.kpi("예측 백엔드", "LSTM ✅" if backend_ok else "더미 폴백"),
            theme.kpi("α (적용값)", f"{res['alpha']:g}" if res["alpha"] is not None else "—", res["alpha_mode"]),
            theme.kpi("job 수", f"{s['n_jobs']}", f"드롭 {s['dropped']}", "good" if s["dropped"] == 0 else "bad"),
            theme.kpi("평균 지연", f"{s['avg_latency_ms']:.1f} ms" if s["avg_latency_ms"] else "—"),
            theme.kpi("예상 배출 (예측 기반)", f"{s['est_total_carbon_g'] / 1000:.2f} kg"),
        ),
        theme.notice("LSTM 범위 밖이라 더미 예측으로 폴백했습니다.", "warn") if not backend_ok else None,
        html.Div([
            html.Div(theme.section(f"리전별 향후 24시간 예측 (t={t} 시점 발행, index 0 = 이 슬롯)",
                                   theme.graph("lb-rt-fig-fc", ff)), className="col-3"),
            html.Div(theme.section("이 슬롯의 리전별 배정 수", theme.graph("lb-rt-fig-load", lf)), className="col-2"),
        ], className="row"),
        theme.section("job별 배정 (origin → assigned)", assign_block),
        html.Button("⬇️ 이 결과 JSON 다운로드", id="lb-rt-download-btn", n_clicks=0, className="btn"),
        theme.details("원본 JSON 보기 (스케줄러 인계 형식)",
                      html.Pre(json.dumps(res, ensure_ascii=False, indent=2), className="mono")),
    ])


@callback(Output("lb-rt-download", "data"), Input("lb-rt-download-btn", "n_clicks"),
          State("lb-rt-t", "value"), State("lb-rt-alpha", "value"), prevent_initial_call=True)
def download(n, t, alpha):
    if not n:
        return dash.no_update
    res = data.realtime_route_slot(int(t), alpha)
    return {"content": json.dumps(res, ensure_ascii=False, indent=2), "filename": f"route_t{int(t)}.json"}
