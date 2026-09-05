"""메인 화면 — LSTM 라이브(2026-01-08 ~ 2026-07-19) 위에서 세 모듈이 맞물려 도는 모습.

  · 24시간 리전별 탄소 예측(LSTM)   · CAST 적용 전후 누적 탄소(그날 0시부터)
  · 세계지도(실행 중 job · 이동 화살표)   · 실행 중 job 표   · 요청→대기→실행 타임라인
계산 로직은 interface/dashboard/live.py.
"""

import dash
import pandas as pd
from dash import Input, Output, State, callback, ctx, dash_table, dcc, html

from interface.dashboard import live as core
from interface.dashboard import theme
from interface.regions import REGION_LABELS

dash.register_page(__name__, path="/", name="메인 화면", order=0)

SAVE_COL = "누적 절감량"
TABLE_COLUMNS = ["job_id", "task_type", "출발지", "도착지", "요청시각", "실행시각", SAVE_COL]
SPEEDS = (0.5, 1.0, 1.25, 1.5, 2.0)

layout = html.Div([
    dcc.Interval(id="main-tick", interval=int(core.PLAY_INTERVAL_SEC * 1000),
                 n_intervals=0, disabled=True),

    html.Div([
        html.Div([
            html.Span("LSTM 라이브 데모 · ", className="subtle"),
            html.Span(f"{core.WINDOW_START:%Y-%m-%d} ~ {core.WINDOW_END:%Y-%m-%d} (UTC)",
                      className="subtle"),
        ]),
        html.Div([
            dcc.DatePickerSingle(
                id="main-date", date=core.WINDOW_START.date(),
                min_date_allowed=core.WINDOW_START.date(),
                max_date_allowed=core.WINDOW_END.date(),
                display_format="YYYY-MM-DD",
            ),
            html.Button("−", id="main-hour-minus", n_clicks=0, className="btn btn-icon"),
            dcc.Input(id="main-hour", type="number", min=0, max=23, step=1, value=12,
                      className="hour-input"),
            html.Button("+", id="main-hour-plus", n_clicks=0, className="btn btn-icon"),
            html.Button("▶", id="main-play", n_clicks=0, className="btn btn-icon",
                        title="자동 재생 (1시간씩 전진)"),
            html.Button("■", id="main-stop", n_clicks=0, className="btn btn-icon", title="정지"),
            dcc.Dropdown(
                id="main-speed",
                options=[{"label": f"{s:g}x", "value": s} for s in SPEEDS],
                value=1.0, clearable=False, searchable=False,
                style={"width": "90px"},
            ),
        ], className="controls"),
    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
              "marginBottom": "0.4rem"}),

    html.Div([
        html.Div([
            html.Div("24시간동안 리전별 탄소 그래프 (LSTM 예측값)", className="chart-title"),
            theme.graph("main-forecast"),
            html.Div(style={"height": "1.5rem"}),
            html.Div("CAST 적용 전후 누적 탄소 배출량 (금일 0시부터)", className="chart-title"),
            theme.graph("main-lb-diff"),
            html.Div(id="main-lb-caption", className="caption"),
        ], className="main-left"),

        html.Div([
            html.Div(theme.graph("main-map"), className="map-wrap"),
            html.Div(style={"height": "0.6rem"}),
            html.Div(id="main-kpis", className="kpi-row"),
            dash_table.DataTable(
                id="main-table",
                columns=[{"name": c, "id": c} for c in TABLE_COLUMNS],
                data=[],
                style_table={"height": "160px", "overflowY": "auto"},
                style_cell={"fontSize": "0.78rem", "padding": "3px 6px", "textAlign": "left",
                            "fontFamily": "inherit"},
                style_header={"fontWeight": 700, "backgroundColor": "#f4f4f2"},
            ),
            html.Div("요청◆ · · 대기 ── 실행 · 빨강=현재 (그 날 0~24시 UTC)", className="caption",
                     style={"margin": "0.5rem 0"}),
            theme.graph("main-timeline"),
        ], className="main-right"),
    ], className="main-split"),
])


@callback(
    Output("main-tick", "disabled"),
    Input("main-play", "n_clicks"),
    Input("main-stop", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_play(_play, _stop):
    return ctx.triggered_id != "main-play"


@callback(Output("main-tick", "interval"), Input("main-speed", "value"))
def set_speed(speed):
    return int(core.PLAY_INTERVAL_SEC * 1000 / (speed or 1.0))


@callback(
    Output("main-date", "date"),
    Output("main-hour", "value"),
    Output("main-tick", "disabled", allow_duplicate=True),
    Input("main-tick", "n_intervals"),
    Input("main-hour-minus", "n_clicks"),
    Input("main-hour-plus", "n_clicks"),
    State("main-date", "date"),
    State("main-hour", "value"),
    prevent_initial_call=True,
)
def step_time(_n, _minus, _plus, picked_day, picked_hour):
    """재생 틱 또는 ±버튼으로 1시간 이동. 23시→다음날 0시처럼 날짜도 함께 넘어간다.
    재생이 구간 끝에 닿으면 자동으로 멈춘다."""
    t_now = core.t_now_of(picked_day, picked_hour or 0)
    delta = -1 if ctx.triggered_id == "main-hour-minus" else 1
    nxt = max(core.MIN_T, min(t_now + delta, core.MAX_T))
    new_day = (core.BASE_TIME + pd.Timedelta(hours=nxt)).date()
    hit_end = ctx.triggered_id == "main-tick" and nxt >= core.MAX_T
    return new_day, int(nxt % 24), (True if hit_end else dash.no_update)


@callback(
    Output("main-forecast", "figure"),
    Output("main-lb-diff", "figure"),
    Output("main-lb-caption", "children"),
    Output("main-map", "figure"),
    Output("main-kpis", "children"),
    Output("main-table", "data"),
    Output("main-table", "style_data_conditional"),
    Output("main-timeline", "figure"),
    Input("main-date", "date"),
    Input("main-hour", "value"),
)
def update_dashboard(picked_day, picked_hour):
    picked_hour = int(picked_hour or 0)
    t_now = core.t_now_of(picked_day, picked_hour)

    jobs, submit_h = core.load_map_jobs()
    actual = core.load_map_actual()
    running = core.map_running_at(jobs, submit_h, actual, t_now)
    saved_now = sum(d["saved"] for d in running)

    forecast_fig = core.draw_forecast_chart(t_now)

    before_total, after_total = core.cumulative_totals(t_now, t_now - picked_hour)
    lb_fig = core.draw_lb_diff_chart(before_total, after_total)
    lb_caption = (f"그날 00:00 ~ {core.map_fmt(t_now)[11:]} UTC에 제출된 job 누적 — "
                  "baseline 리전·즉시실행 vs 실제(carbon-aware 리전·time-shift) 탄소 비교")

    region_counts, routes = {}, {}
    for d in running:
        region_counts[d["region"]] = region_counts.get(d["region"], 0) + 1
        o, a = d["origin"], d["region"]
        if o != a:
            routes[(o, a)] = routes.get((o, a), 0) + 1
    map_fig = core.draw_map(routes=routes, region_counts=region_counts, height=300)

    kpis = [
        theme.kpi("현재 시각(UTC)", core.map_fmt(t_now)),
        theme.kpi("실행 중인 작업", f"{len(running)}개"),
        theme.kpi("이 시점 절감", f"{saved_now:,.0f} gCO₂"),
    ]

    rows = [{
        "job_id": d["job_id"],
        "task_type": core.MAP_TASK_TYPE.get(d["k"], f"k={d['k']}"),
        "출발지": REGION_LABELS.get(d["origin"], d["origin"]),
        "도착지": REGION_LABELS.get(d["region"], d["region"]),
        "요청시각": core.map_fmt(d["submit_time"])[5:],
        "실행시각": core.map_fmt(d["scheduled_start"])[5:],
        SAVE_COL: round(d["saved"], 0),
    } for d in sorted(running, key=lambda x: x["saved"], reverse=True)]
    bar_styles = theme.bar_style(SAVE_COL, core.MAP_SAVED_BAR_MAX)

    timeline_fig = core.draw_timeline(running, t_now, t_now - picked_hour, height=190)
    return forecast_fig, lb_fig, lb_caption, map_fig, kpis, rows, bar_styles, timeline_fig
