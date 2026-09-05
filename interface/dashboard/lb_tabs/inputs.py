"""① 입력 데이터 — 리전별 실측 탄소강도 · 레이턴시 행렬 · job 제출 분포."""

import plotly.graph_objects as go
from dash import html

from interface.dashboard import data, theme
from interface.dashboard.lb_tabs.common import RC, R


def render(d: dict) -> html.Div:
    carbon, jobs, latency = d["carbon"], d["jobs"], d["latency"]
    x = data.lb_ts(carbon.time_s)
    fig = theme.base_fig(height=420, legend=dict(orientation="h", y=1.12),
                         xaxis_title="시각 (UTC)", yaxis_title="gCO₂/kWh")
    for r in R:
        fig.add_trace(go.Scatter(x=x, y=carbon[r], name=r, mode="lines", line=dict(color=RC[r], width=1.5),
                                 hovertemplate=f"{r}: %{{y:.0f}} g/kWh<br>%{{x|%m-%d %H시}}<extra></extra>"))

    lat_fig = theme.base_fig(height=420, yaxis_autorange="reversed")
    lat_fig.add_trace(go.Heatmap(z=latency, x=R, y=R, colorscale=theme.BLUE_SEQ,
                                 text=latency.astype(int), texttemplate="%{text}",
                                 hovertemplate="%{y} → %{x}: %{z} ms<extra></extra>", showscale=False))

    pivot = (jobs.assign(h=((jobs.submit_time // 3600) % 24).astype(int))
             .groupby(["region", "h"]).size().unstack(fill_value=0)
             .reindex(index=R, columns=range(24), fill_value=0))
    sub_fig = theme.base_fig(height=420, yaxis_autorange="reversed", xaxis_title="UTC 시각")
    sub_fig.add_trace(go.Heatmap(z=pivot.values, x=list(range(24)), y=R, colorscale=theme.BLUE_SEQ,
                                 hovertemplate="%{y} · UTC %{x}시: %{z}개<extra></extra>",
                                 colorbar=dict(title="개")))

    return html.Div([
        theme.section("리전별 탄소강도 (실측, 1시간 해상도)", theme.graph("lb-fig-carbon", fig),
                      caption="소스: data/lstm_eval의 y_true (실측). 1월 1~7일은 1월 8일 프로파일 반복."),
        html.Div([
            html.Div(theme.section("리전 간 레이턴시 (ms)", theme.graph("lb-fig-lat", lat_fig),
                                   caption="Azure inter-region round-trip latency, 대칭 8×8."), className="col-1"),
            html.Div(theme.section("job 제출 분포 (리전 × UTC 시각)", theme.graph("lb-fig-sub", sub_fig),
                                   caption="UTC 기준이라 리전별 봉우리가 시차만큼 어긋나 보인다 "
                                           "(각 리전의 현지 낮이 서로 다른 UTC 시간대에 위치)."), className="col-1"),
        ], className="row"),
        theme.details("jobs.csv 미리보기 / 통계",
                      theme.table(jobs.head(50), page_size=10),
                      theme.caption(f"총 {len(jobs):,}개 · 리전별 {len(jobs) // 8:,}개 균등 · "
                                    f"deferrable(L_max≥1h) {(jobs.L_max >= 3600).mean() * 100:.1f}%")),
    ])
