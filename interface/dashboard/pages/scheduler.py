"""스케줄러 검증 — 2025년 1년치, 로드밸런서와 같은 job 목록 + 같은 배정 결과 위에서
세 비교군(단순 LB 즉시 / 탄소 LB 즉시 / 탄소 LB + time-shift)을 SimPy 로 돌린 결과."""

import time

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from interface.dashboard import data, theme
from scheduler.config import MODES

dash.register_page(__name__, path="/scheduler", name="스케줄러", order=4)

MODE_ORDER = ["simple_lb_immediate", "carbon_lb_immediate", "carbon_lb_timeshift"]
MODE_LABEL = {"simple_lb_immediate": "단순 LB + 즉시", "carbon_lb_immediate": "탄소 LB + 즉시",
              "carbon_lb_timeshift": "탄소 LB + time-shift (ours)"}
MODE_COLOR = {"simple_lb_immediate": theme.BASELINE_GRAY, "carbon_lb_immediate": theme.ACCENT,
              "carbon_lb_timeshift": theme.OURS_GREEN}


def layout(**_):
    return html.Div([
        dcc.Interval(id="sched-poll", interval=2000, n_intervals=0),
        html.Div([
            html.Div([html.H1("스케줄러 검증 — 2025년 1년치 결과"),
                      theme.caption("리전 배정은 로드밸런서(α=auto)가 준 것을 그대로 쓰고, 스케줄러는 그 리전 안에서 "
                                    "'언제' 실행할지만 정한다. 탄소 회계는 2025년 실측값(y_true) 기준.")]),
            html.Button("다시 실행", id="sched-rerun", n_clicks=0, className="btn"),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"}),
        html.Div(id="sched-body"),
        dcc.Download(id="sched-download"),
    ])


@callback(Output("sched-poll", "disabled"), Input("sched-rerun", "n_clicks"),
          prevent_initial_call=True)
def rerun(_):
    data.start_validation_async(force=True)
    return False


@callback(Output("sched-body", "children"), Output("sched-poll", "disabled", allow_duplicate=True),
          Input("sched-poll", "n_intervals"), prevent_initial_call="initial_duplicate")
def render(_):
    st = data.validation_state()
    if st["status"] in ("idle", "running"):
        if st["status"] == "idle":
            data.start_validation_async()
        elapsed = (time.time() - st["started"]) if st["started"] else 0
        return html.Div([
            theme.notice(f"2025년 1년치 시뮬레이션 실행 중… (146,000 job × 3 비교군, 약 1분) — {elapsed:.0f}초 경과",
                         "info"),
            dcc.Loading(html.Div(style={"height": "60px"}), type="dot"),
        ]), False
    if st["status"] == "error":
        return theme.notice(f"시뮬레이션 실패: {st['error']}", "error"), True
    return _render_results(st), True


def _render_results(st):
    comparison = st["comparison"]
    results = st["results"]
    immediate = results["carbon_lb_immediate"]
    shifted = results["carbon_lb_timeshift"]

    total_simple = comparison["simple_lb_immediate"]["total_carbon"]
    total_imm = comparison["carbon_lb_immediate"]["total_carbon"]
    total_shift = comparison["carbon_lb_timeshift"]["total_carbon"]
    overall_pct = (1 - total_shift / total_imm) * 100 if total_imm else 0.0
    avg_delay = comparison["carbon_lb_timeshift"]["avg_delay"]
    n_jobs = comparison["carbon_lb_timeshift"]["n_jobs"]
    slo_viol = comparison["carbon_lb_timeshift"]["slo_violation_rate"]
    saved_total = total_imm - total_shift

    kpis = theme.kpi_row(
        theme.kpi("time-shift 절감률", f"{overall_pct:.1f}%", "탄소 LB 즉시실행 대비", "good"),
        theme.kpi("절감한 탄소", f"{saved_total / 1e6:,.2f} tCO₂", f"{saved_total:,.0f} g"),
        theme.kpi("평균 지연", f"{avg_delay:.2f} h", "time-shift 로 미룬 시간"),
        theme.kpi("SLO(마감) 위반율", f"{slo_viol * 100:.2f}%",
                  "정상" if slo_viol == 0 else "위반 발생", "good" if slo_viol == 0 else "bad"),
        theme.kpi("전체 절감 (단순 LB 대비)", f"{(1 - total_shift / total_simple) * 100:.1f}%",
                  f"공간 {(1 - total_imm / total_simple) * 100:.1f}% + 시간 추가", "good"),
    )

    # (좌) 비교군별 총 탄소
    modes = [m for m in MODE_ORDER if m in comparison]
    vals = [comparison[m]["total_carbon"] / 1e6 for m in modes]
    fig = theme.base_fig(height=300, xaxis_title="총 탄소 배출 (tCO₂)", showlegend=False)
    fig.add_trace(go.Bar(x=vals, y=[MODE_LABEL[m] for m in modes], orientation="h",
                         marker_color=[MODE_COLOR[m] for m in modes],
                         text=[f"{v:,.1f} tCO₂" for v in vals], textposition="auto",
                         hovertemplate="%{y}: %{x:.2f} tCO₂<extra></extra>"))
    fig.update_yaxes(autorange="reversed")

    # (우) k별 지연·절감
    imm_by_id = {r["job_id"]: r["carbon_emitted"] for r in immediate}
    agg = {}
    for r in shifted:
        d = agg.setdefault(r["k"], {"n": 0, "delay": 0.0, "saved": 0.0})
        d["n"] += 1
        d["delay"] += r["delay"]
        d["saved"] += imm_by_id.get(r["job_id"], r["carbon_emitted"]) - r["carbon_emitted"]
    ks = sorted(agg, reverse=True)
    fig2 = theme.base_fig(height=300, barmode="group", legend=dict(orientation="h", y=1.15),
                          yaxis=dict(title="평균 지연(h)"),
                          yaxis2=dict(title="절감(tCO₂)", overlaying="y", side="right", showgrid=False))
    fig2.add_bar(x=[f"k={k}" for k in ks], y=[agg[k]["delay"] / agg[k]["n"] for k in ks],
                 name="평균 지연(h)", marker_color=theme.ACCENT,
                 hovertemplate="%{x} 평균지연 %{y:.2f}h<extra></extra>")
    fig2.add_bar(x=[f"k={k}" for k in ks], y=[agg[k]["saved"] / 1e6 for k in ks],
                 name="절감(tCO₂)", marker_color=theme.OURS_GREEN, yaxis="y2",
                 hovertemplate="%{x} 절감 %{y:.2f} tCO₂<extra></extra>")

    # 상세
    cdf = pd.DataFrame(comparison).T.loc[modes]
    cdf.insert(0, "비교군", [MODES[m] for m in modes])
    cdf["n_jobs"] = cdf["n_jobs"].map(lambda v: f"{v:,.0f}")
    cdf["total_carbon"] = cdf["total_carbon"].map(lambda v: f"{v:,.0f} g")
    cdf["avg_delay"] = cdf["avg_delay"].map(lambda v: f"{v:.3f} h")
    cdf["slo_violation_rate"] = cdf["slo_violation_rate"].map(lambda v: f"{v:.4f}")

    counts = pd.Series([r["region"] for r in shifted]).value_counts()
    reg_fig = theme.base_fig(height=260, yaxis_title="배정 job 수", showlegend=False)
    reg_fig.add_trace(go.Bar(x=list(counts.index), y=counts.values,
                             marker_color=[theme.REGION_COLORS.get(r, theme.ACCENT) for r in counts.index],
                             hovertemplate="%{x}: %{y:,} job<extra></extra>"))

    return html.Div([
        theme.caption(f"job {n_jobs:,}개 · 2025년 1년치 · 탄소 회계 "
                      f"{'실측' if st['carbon_is_real'] else '더미'} · 예측: {st['backend']} · "
                      f"시뮬레이션 {st['elapsed']:.0f}초"),
        kpis,
        theme.hr(),
        html.Div([
            html.Div([theme.section("비교군별 총 탄소 배출량", theme.graph("sched-fig-modes", fig),
                                    caption="① → ② 는 로드밸런서의 공간 이동 기여, ② → ③ 이 스케줄러(time-shift)의 기여.")],
                     className="col-1"),
            html.Div([theme.section("중요도(k)별 지연·절감", theme.graph("sched-fig-k", fig2),
                                    caption="k=5(급함)는 지연 ≈0, k=1(여유)일수록 많이 미뤄 탄소를 아낌 (설계 의도).")],
                     className="col-1"),
        ], className="row"),
        theme.details("상세 수치 · 리전 배정 분포 · 결과 CSV",
                      theme.table(cdf, page_size=5),
                      theme.graph("sched-fig-region", reg_fig),
                      html.Button("결과 CSV 다운로드 (time-shift 146,000행)", id="sched-download-btn",
                                  n_clicks=0, className="btn")),
    ])


@callback(Output("sched-download", "data"), Input("sched-download-btn", "n_clicks"),
          prevent_initial_call=True)
def download(n):
    if not n:
        return dash.no_update
    st = data.validation_state()
    if st["status"] != "done":
        return dash.no_update
    df = pd.DataFrame(st["results"]["carbon_lb_timeshift"])
    return dcc.send_data_frame(df.to_csv, "scheduler_validation_2025.csv", index=False)
