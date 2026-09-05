"""LSTM 탄소강도 예측 — 실제 모델이 내놓는 24시간 예측을 실측과 나란히 본다 (2026 라이브 축)."""

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from interface import carbon_forecast_api as api
from interface import dashboard_core as core
from interface.dashboard import theme
from interface.regions import REGIONS, label

dash.register_page(__name__, path="/lstm", name="LSTM", order=3)


def layout(**_):
    st = api.status()
    return html.Div([
        html.H1("LSTM 탄소강도 예측"),
        theme.caption("carbon-forecast-LSTM/models 의 학습된 모델이 향후 24시간 탄소강도를 예측한다. "
                      "입력 = 그 시점 이전 168시간 실측 이력 (carbon_intensity · cfe · re · 시간 피처, "
                      "날씨 리전 3곳은 풍속·일사량·기온 추가)."),
        theme.notice(api.backend_info(), "ok" if st["ready"] else "warn"),
        theme.kpi_row(
            theme.kpi("모델 상태", "연결됨" if st["ready"] else "미연결"),
            theme.kpi("예측 가능 시작", str(st["forecastable_from"] or "-")[:16]),
            theme.kpi("이력 끝", str(st["history_end"] or "-")[:16]),
            theme.kpi("입력 피처", "10 (날씨 리전 13)"),
        ),
        theme.notice(
            "LSTM 입력 중 cfe_pct·re_pct(무탄소/재생에너지 비중)는 실측 데이터가 없어 탄소강도로부터 "
            "만든 임시 추정값을 쓰고 있습니다.", "info") if st["placeholder_cfe_re"] else None,

        theme.section("예측 조회", html.Div([
            html.Label("예측 기준 시각 (UTC)"),
            dcc.DatePickerSingle(id="lstm-date", date=core.WINDOW_START.date(),
                                 min_date_allowed=core.WINDOW_START.date(),
                                 max_date_allowed=core.WINDOW_END.date(),
                                 display_format="YYYY-MM-DD"),
            dcc.Input(id="lstm-hour", type="number", min=0, max=23, step=1, value=12,
                      className="hour-input"),
            html.Span("시", className="subtle"),
            dcc.Checklist(id="lstm-show-actual", options=[{"label": " 실측 겹쳐 보기", "value": "on"}],
                          value=["on"], className="checks-inline", style={"marginLeft": "1rem"}),
            dcc.Checklist(id="lstm-regions", inline=True, className="checks-inline",
                          options=[{"label": f" {r}", "value": r} for r in REGIONS], value=list(REGIONS),
                          style={"marginLeft": "1rem"}),
        ], className="controls"),
            caption="LSTM은 이 시점 이전 168시간 이력이 있어야 동작한다. 없으면 더미(사인파+노이즈)로 폴백한다."),

        html.Div(id="lstm-backend-note"),
        theme.graph("lstm-chart"),
        html.Div(id="lstm-mae", className="kpi-row"),
        theme.section("예측값 표 (행 = 리전, 열 = 몇 시간 후, gCO₂/kWh)", html.Div(id="lstm-table")),

        theme.details("이 예측이 스케줄러·로드밸런서에서 어떻게 쓰이나", theme.md(
            "**스케줄러**는 job을 미룰 수 있는 시간(`L_max`) 안에서 이 예측값을 보고 "
            "**탄소가 가장 낮은 시각**을 고른다.\n\n"
            "```\nscore(t) = α · (탄소 비용) + (1 - α) · (지연 비용)\nt* = argmin score(t)\n```\n\n"
            "**로드밸런서**는 index 0(이 슬롯의 예측값)으로 리전 간 상대 탄소강도 M̃ 를 만들어 "
            "ILP 목적함수 `α·M̃ + (1−α)·l̃` 에 넣는다.\n\n"
            "즉 위 곡선이 낮게 내려가는 시간대·리전으로 job이 이동한다.")),
    ])


@callback(
    Output("lstm-backend-note", "children"),
    Output("lstm-chart", "figure"),
    Output("lstm-mae", "children"),
    Output("lstm-table", "children"),
    Input("lstm-date", "date"),
    Input("lstm-hour", "value"),
    Input("lstm-show-actual", "value"),
    Input("lstm-regions", "value"),
)
def update(picked_day, picked_hour, show_actual, regions):
    t_hour = core.t_now_of(picked_day, int(picked_hour or 0))
    forecast = api.get_forecast(t_hour=t_hour, horizon=24)
    used = api.last_backend()
    regions = [r for r in REGIONS if r in (regions or [])] or list(REGIONS)

    when = core.map_fmt(t_hour)
    if used == "lstm":
        note = theme.notice(f"{when} UTC 기준 예측 — 실제 LSTM 모델이 생성했습니다.", "ok")
    else:
        note = theme.notice(f"{when} UTC 기준 예측 — 이 시점은 168시간 이력이 없어 더미로 대체했습니다.", "warn")

    actual = core.load_map_actual() if show_actual else None
    xs = [core.BASE_TIME + pd.Timedelta(hours=t_hour + h) for h in range(24)]

    fig = theme.base_fig(height=420, legend=dict(orientation="h", y=-0.18),
                         yaxis_title="gCO₂/kWh", xaxis_title="시각 (UTC)")
    mae_cards = []
    for r in regions:
        pred = np.asarray(forecast[r], dtype=float)
        fig.add_trace(go.Scatter(x=xs, y=pred, name=f"{r} 예측", mode="lines",
                                 line=dict(color=theme.REGION_COLORS[r], width=2),
                                 hovertemplate=f"{r} 예측 %{{y:.0f}}<br>%{{x|%m-%d %H시}}<extra></extra>"))
        if actual is not None and r in actual:
            arr = actual[r]
            act = np.array([arr[min(t_hour + h, len(arr) - 1)] for h in range(24)], dtype=float)
            fig.add_trace(go.Scatter(x=xs, y=act, name=f"{r} 실측", mode="lines",
                                     line=dict(color=theme.REGION_COLORS[r], width=1.2, dash="dot"),
                                     hovertemplate=f"{r} 실측 %{{y:.0f}}<br>%{{x|%m-%d %H시}}<extra></extra>"))
            mae = float(np.mean(np.abs(pred - act)))
            mape = float(np.mean(np.abs(pred - act) / np.maximum(act, 1e-6)) * 100)
            mae_cards.append(theme.kpi(f"{r} MAE (24h)", f"{mae:.1f} g", f"MAPE {mape:.1f}%"))
    if len(regions) > 4 and mae_cards:
        for c in mae_cards:
            c.style = {"minWidth": "120px"}

    df = pd.DataFrame({f"+{h}h": [round(forecast[r][h]) for r in regions] for h in range(24)},
                      index=[f"{r} ({label(r)})" for r in regions])
    df.insert(0, "리전", df.index)
    return note, fig, mae_cards, theme.table(df, page_size=8)
