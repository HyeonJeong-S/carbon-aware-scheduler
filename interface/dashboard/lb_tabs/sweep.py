"""③ α 스윕 · 모드 비교 — 파레토 곡선(사후 평가) · 운영 모드 3종 · 전체 결과 표."""

import pandas as pd
import plotly.graph_objects as go
from dash import html

from interface.dashboard import data, theme

_KNEE_QA = (
    "점 하나 = α 하나로 1년을 완주한 run. x축 = 지불한 값(평균 지연), y축 = 얻은 것(탄소 절감률).\n\n"
    "**곡선이 처음엔 가파르다가 점점 눕는 이유 = 한계 수익 체감:**\n"
    "- α를 조금만 올려도 처음엔 **싼 거래**부터 잡는다 — 프랑스↔독일(12ms), 한국↔일본(30ms)처럼 "
    "몇 ms만 내주면 큰 절감이 나오는 경로들.\n"
    "- α를 더 올릴수록 남은 건 **비싼 거래**뿐 — 아시아→유럽(240ms급) 장거리를 태워야 겨우 조금 더 "
    "아껴지는 구간.\n"
    "- 실측으로 보면: α 0→0.5는 지연 29ms로 절감 46%를 사지만, 0.75→1은 **지연 +52ms를 내고 절감 "
    "+1%p**밖에 못 산다.\n\n"
    "**무릎점 = 싼 거래가 소진되는 경계.** 그 앞은 '안 사면 손해', 그 뒤는 '사면 손해'인 지점이라, "
    "합리적 운영점은 무릎 근처일 수밖에 없다.\n\n"
    "**★(auto)가 곡선보다 위에 뜨는 이유:** 고정 α는 교환비가 나쁜 시간(리전 간 탄소 격차가 없는 "
    "시간)에도 같은 강도로 job을 옮겨 지연을 낭비한다. auto는 매 시간 그 시간의 곡선에서 무릎을 다시 "
    "찾아 좋은 시간에만 공격적으로 움직이므로, 1년 평균으로 보면 **같은 지연 예산에서 더 많은 절감**이 "
    "나온다 — 이 별이 곡선 위에 있다는 것 자체가 시변 α의 존재 증명."
)

_MODES = [("alpha_0", "🏠 지역(레이턴시) 중심", "α=0 — 항상 가장 가까운 리전"),
          ("alpha_0.5", "⚖️ 균형", "α=0.5 — 탄소·지연 절충"),
          ("alpha_1", "🌱 탄소 중심", "α=1 — 항상 가장 깨끗한 리전")]


def render(d: dict) -> html.Div:
    summary = d["summary"]
    runs, auto = data.lb_alpha_runs(summary)
    base_m = summary["baseline"]["metrics"]
    am = summary[auto]["metrics"] if auto else None

    def saving_pct(m):
        return (1 - m["total_carbon_kg"] / base_m["total_carbon_kg"]) * 100

    fixed = [k for k in runs if k != auto]
    xs = [summary[k]["metrics"]["avg_latency_ms"] for k in fixed]
    ys = [saving_pct(summary[k]["metrics"]) for k in fixed]
    labels = [f"α={k.split('_')[1]}" for k in fixed]
    fig = theme.base_fig(height=540, width=540, legend=dict(orientation="h", y=1.08),
                         xaxis_title="평균 네트워크 지연 (ms) — 오른쪽일수록 비쌈",
                         yaxis_title="탄소 절감률 (% vs baseline) — 위일수록 좋음")
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers+text", text=labels, textposition="bottom right",
                             name="고정 α 스윕", line=dict(color=theme.ACCENT, width=2),
                             marker=dict(size=10, color=theme.ACCENT),
                             hovertemplate="%{text}: 지연 %{x:.1f}ms · 절감 %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=[base_m["avg_latency_ms"]], y=[0], mode="markers+text", text=["baseline"],
                             textposition="top right", textfont=dict(color=theme.MUTED), name="baseline (절감 0%)",
                             marker=dict(size=12, color=theme.BASELINE_GRAY, symbol="diamond")))
    if am:
        fig.add_trace(go.Scatter(x=[am["avg_latency_ms"]], y=[saving_pct(am)], mode="markers+text",
                                 text=["★ α=auto"], textposition="top left", textfont=dict(size=14),
                                 name="α = auto (무릎점)", marker=dict(size=14, color=theme.INK, symbol="star")))

    mode_cards = []
    for key, title, desc in _MODES:
        if key not in summary:
            continue
        m = summary[key]["metrics"]
        mode_cards.append(html.Div([
            html.Div(html.B(title)), theme.caption(desc),
            theme.kpi("총 탄소", f"{m['total_carbon_kg']:,.0f} kg",
                      f"{(m['total_carbon_kg'] / base_m['total_carbon_kg'] - 1) * 100:+.1f}%", "good"),
            theme.kpi("평균 지연", f"{m['avg_latency_ms']:.1f} ms"),
            theme.kpi("홈 리전 비율", f"{m['home_ratio'] * 100:.0f} %"),
        ], className="card col-1"))

    rows = []
    for name in ["baseline", *runs]:
        m = summary[name]["metrics"]
        if m["mode"] != "ilp":
            alpha = "—"
        elif m.get("alpha_mode") == "auto":
            alpha = f"auto (평균 {m['alpha']:g})"
        else:
            alpha = f"{m['alpha']:g}"
        rows.append({
            "run": name, "모드": m["mode"], "α": alpha,
            "총탄소 (kg)": f"{m['total_carbon_kg']:,.1f}", "평균지연 (ms)": f"{m['avg_latency_ms']:.1f}",
            "p95지연 (ms)": f"{m['p95_latency_ms']:.0f}", "홈리전": f"{m['home_ratio'] * 100:.1f}%",
            "드롭": m["dropped"], "탄소절감 (vs baseline)": f"{saving_pct(m):.1f}%",
        })

    return html.Div([
        theme.section(
            "파레토 곡선 — 사후 평가 (1년 집계)",
            theme.caption("run 하나가 점 하나 (x=평균 지연, y=탄소 절감률). 파란 곡선은 같은 1년을 α만 바꿔 여러 번 "
                          "재생해야 얻어지는 사후(hindsight) 기준선이고, auto는 매 시각 그 시점의 LSTM 예측만으로 "
                          "실시간 달성한 값이다. 실시간 관점의 그림(누적 배출·시간별 절감)은 ②탭에."),
            theme.notice(f"⭐ α = auto (슬롯별 파레토 무릎점) — 총 탄소 {am['total_carbon_kg']:,.0f} kg "
                         f"(baseline 대비 {saving_pct(am):.1f}% 절감) · 평균 지연 {am['avg_latency_ms']:.1f} ms · "
                         f"슬롯 평균 α = {am['alpha']:g}", "ok") if am else None,
            html.Div([
                html.Div([theme.graph("lb-fig-pareto", fig),
                          theme.caption("좌상단이 이상적 (지연은 적게, 절감은 많이). ★ = auto가 실제로 도달한 지점 — "
                                        "곡선보다 위에 떠 있다면 같은 지연 예산으로 고정 α보다 더 아꼈다는 뜻.")],
                         style={"flex": "0 0 560px"}),
                html.Div(theme.details("Q. 곡선이 왜 이런 모양인가요? — 무릎점이 생기는 이유",
                                       theme.md(_KNEE_QA), open_=True), className="col-1"),
            ], className="row")),
        theme.hr(),
        theme.section("세 가지 운영 모드", html.Div(mode_cards, className="row")),
        theme.hr(),
        theme.section("전체 결과 표", theme.table(pd.DataFrame(rows), page_size=10),
                      caption="고정 α run들은 auto의 비교 기준. auto = 매 슬롯 파레토 무릎점 α 자동 선택."),
    ])
