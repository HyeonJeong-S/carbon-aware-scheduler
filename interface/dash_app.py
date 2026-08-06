"""메인 대시보드 Dash 버전 (Streamlit 버전과 별개 앱).

실행:
    python interface/dash_app.py

계산 로직은 interface/dashboard_core.py를 interface/views/main.py(Streamlit)와
공유한다. Dash는 컴포넌트별 콜백으로 값만 갱신하는 구조라, Streamlit 버전에서
겪었던 "재생 중 화면 전체가 깜빡이는" 문제 자체가 구조적으로 없다.
"""

import os
import sys

import dash
import pandas as pd
from dash import Dash, Input, Output, State, dcc, html
from dash import dash_table

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from interface import dashboard_core as core  # noqa: E402
from interface.regions import REGION_LABELS  # noqa: E402

SAVE_COL = "누적 절감량"
TABLE_COLUMNS = ["job_id", "task_type", "출발지", "도착지", "요청시각", "실행시각", SAVE_COL]

app = Dash(__name__)
app.title = "CAST"


def _bar_style(column, max_val, color="#8bc34a", n_bins=20):
    """dash_table 셀 안에 진행바를 그리는 표준 트릭 — 값 구간별로 배경을
    linear-gradient로 나눠서, 그 구간 안 어떤 값이든 해당 위치까지 채워 보이게 한다."""
    styles = []
    for i in range(n_bins):
        lo = max_val * i / n_bins
        hi = max_val * (i + 1) / n_bins
        pct = (i + 1) / n_bins * 100
        if i == n_bins - 1:
            cond = f"{{{column}}} >= {lo}"
        else:
            cond = f"{{{column}}} >= {lo} && {{{column}}} < {hi}"
        styles.append({
            "if": {"filter_query": cond, "column_id": column},
            "background": (f"linear-gradient(90deg, {color} 0%, {color} {pct}%, "
                           f"white {pct}%, white 100%)"),
        })
    return styles


def _kpi_card(label, value):
    return html.Div([
        html.Div(label, style={"color": "#666", "fontSize": "0.85rem"}),
        html.Div(value, style={"fontSize": "1.8rem", "fontWeight": 700}),
    ], style={"flex": 1})


app.layout = html.Div([
    dcc.Interval(id="tick", interval=int(core.PLAY_INTERVAL_SEC * 1000),
                 n_intervals=0, disabled=True),

    # 상단 바
    html.Div([
        html.Div([
            html.Span("CAST", style={"fontSize": "2.2rem", "fontWeight": 800,
                                      "letterSpacing": "-0.02em"}),
            html.Span("Carbon-Aware Spatio-Temporal Scheduler",
                       style={"fontSize": "0.85rem", "color": "#888", "marginLeft": "0.8rem"}),
        ]),
        html.Div([
            dcc.DatePickerSingle(
                id="date-picker", date=core.WINDOW_START.date(),
                min_date_allowed=core.WINDOW_START.date(),
                max_date_allowed=core.WINDOW_END.date(),
                display_format="YYYY-MM-DD",
            ),
            dcc.Input(id="hour-input", type="number", min=0, max=23, step=1, value=12,
                      style={"width": "56px", "marginLeft": "0.5rem"}),
            html.Button("▶", id="play-btn", n_clicks=0,
                        style={"marginLeft": "0.6rem", "width": "36px"}),
            html.Button("■", id="stop-btn", n_clicks=0,
                        style={"marginLeft": "0.3rem", "width": "36px"}),
            dcc.Dropdown(
                id="speed-dropdown",
                options=[{"label": f"{s}x", "value": s} for s in (0.5, 1.0, 1.25, 1.5)],
                value=1.0, clearable=False, searchable=False,
                style={"width": "90px", "marginLeft": "0.5rem"},
            ),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
              "padding": "0.6rem 1.5rem", "borderBottom": "1px solid #eee"}),

    html.Div([
        # 왼쪽 (좁음)
        html.Div([
            html.Div("24시간동안 리전별 탄소 그래프 (LSTM 예측값)",
                     style={"fontWeight": 700, "marginTop": "0.8rem", "marginBottom": "0.3rem"}),
            dcc.Graph(id="forecast-chart", config={"displayModeBar": False}),
            html.Div(style={"height": "2rem"}),
            html.Div("CAST 적용 전후 누적 탄소 배출량 (그날 0시부터)",
                     style={"fontWeight": 700, "marginBottom": "0.3rem"}),
            dcc.Graph(id="lb-diff-chart", config={"displayModeBar": False}),
            html.Div(id="lb-caption",
                     style={"fontSize": "0.8rem", "color": "#888", "marginTop": "0.3rem"}),
        ], style={"flex": "1", "borderRight": "2px solid #ccc", "paddingRight": "1.5rem",
                  "minWidth": "0"}),

        # 오른쪽 (넓음)
        html.Div([
            dcc.Graph(id="map-chart", config={"displayModeBar": False}),
            html.Div(style={"height": "0.8rem"}),
            html.Div(id="kpi-row", style={"display": "flex", "gap": "3rem",
                                          "marginBottom": "0.6rem"}),
            dash_table.DataTable(
                id="job-table",
                columns=[{"name": c, "id": c} for c in TABLE_COLUMNS],
                data=[],
                style_table={"height": "140px", "overflowY": "auto"},
                style_cell={"fontSize": "0.78rem", "padding": "3px", "textAlign": "left"},
                style_cell_conditional=[
                    {"if": {"column_id": SAVE_COL}, "textAlign": "left"},
                ],
                style_header={"fontWeight": 700, "backgroundColor": "#f7f7f7"},
            ),
            html.Div("요청◆ · · 대기 ── 실행 · 빨강=현재 (그 날 0~24시 UTC)",
                     style={"fontSize": "0.8rem", "color": "#888", "margin": "0.5rem 0"}),
            dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
        ], style={"flex": "3", "paddingLeft": "1.5rem", "minWidth": "0"}),
    ], style={"display": "flex", "padding": "1rem 1.5rem"}),
], style={"fontFamily": "-apple-system, sans-serif"})


# 재생/정지 — Streamlit 버전과 달리 각 버튼이 자기 콜백만 갖고, 위젯 값을
# 프레임워크가 몰래 되돌리는 문제 자체가 Dash 콜백 구조에는 없다.
@app.callback(
    Output("tick", "disabled"),
    Input("play-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_play(_play_clicks, _stop_clicks):
    return dash.ctx.triggered_id != "play-btn"


@app.callback(
    Output("tick", "interval"),
    Input("speed-dropdown", "value"),
)
def set_speed(speed):
    return int(core.PLAY_INTERVAL_SEC * 1000 / (speed or 1.0))


@app.callback(
    Output("date-picker", "date"),
    Output("hour-input", "value"),
    Input("tick", "n_intervals"),
    State("date-picker", "date"),
    State("hour-input", "value"),
    prevent_initial_call=True,
)
def advance_time(_n_intervals, picked_day, picked_hour):
    t_now = core.t_now_of(picked_day, picked_hour or 0)
    nxt = min(t_now + 1, core.MAX_T)
    new_day = (core.BASE_TIME + pd.Timedelta(hours=nxt)).date()
    return new_day, int(nxt % 24)


@app.callback(
    Output("forecast-chart", "figure"),
    Output("lb-diff-chart", "figure"),
    Output("lb-caption", "children"),
    Output("map-chart", "figure"),
    Output("kpi-row", "children"),
    Output("job-table", "data"),
    Output("job-table", "style_data_conditional"),
    Output("timeline-chart", "figure"),
    Input("date-picker", "date"),
    Input("hour-input", "value"),
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

    region_counts = {}
    for d in running:
        region_counts[d["region"]] = region_counts.get(d["region"], 0) + 1
    routes = {}
    for d in running:
        o, a = d["origin"], d["region"]
        if o != a:
            routes[(o, a)] = routes.get((o, a), 0) + 1
    map_fig = core.draw_map(routes=routes, region_counts=region_counts, height=260)

    kpi = [
        _kpi_card("현재 시각(UTC)", core.map_fmt(t_now)),
        _kpi_card("실행 중인 작업", f"{len(running)}개"),
        _kpi_card("이 시점 절감", f"{saved_now:,.0f} gCO₂"),
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

    bar_styles = _bar_style(SAVE_COL, core.MAP_SAVED_BAR_MAX)

    timeline_fig = core.draw_timeline(running, t_now, t_now - picked_hour, height=175)

    return forecast_fig, lb_fig, lb_caption, map_fig, kpi, rows, bar_styles, timeline_fig


if __name__ == "__main__":
    app.run(debug=False, port=8050)
