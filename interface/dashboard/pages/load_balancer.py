"""로드밸런서 — 탄소 인지 ILP 라우팅 (1년 실데이터 · Azure 8리전).

탭: ① 입력 데이터 ② 전/후 비교 ③ α 스윕 · 모드 비교 ④ 실시간 라우팅 (LSTM 라이브)
"""

import json
import time

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html

from interface.dashboard import data, theme

dash.register_page(__name__, path="/load-balancer", name="로드밸런서", order=2)

R = data.LB_REGIONS                       # LB 표기 순서 (그래프 축에 그대로 사용)
RC = {lb: theme.REGION_COLORS[data.to_std(lb)] for lb in R}   # LB 표기 → 리전 색
UTC_OFFSET = data.lb_config.UTC_OFFSET
SHOW_MAX = 5000
RT_SPEEDS = {"0.5×": 4000, "1×": 2000, "2×": 1000, "4×": 400}   # 배속 → 슬롯당 ms


def layout(**_):
    if not data.lb_results_available():
        return html.Div([
            html.H1("로드밸런서"),
            theme.notice("결과가 없습니다. 아래 '실험 다시 실행'을 누르거나 터미널에서 "
                         "`python load_balancer/02_프레임워크/run_experiments.py` 를 실행하세요 (약 40분).", "warn"),
            _rerun_block(),
        ])
    return html.Div([
        html.Div([
            html.Div([html.H1("탄소 인지 로드밸런서"),
                      theme.caption("LSTM + ILP 라우팅 시뮬레이터 · 2025년 1년 실데이터 · Azure 8리전 · "
                                    "매 1시간 슬롯 파레토 무릎점으로 α 자동 선택")]),
            theme.details("데이터 · 가정", theme.md(
                "- 탄소강도: **실측** (lstm_eval의 y_true, 2025년 1년치)\n"
                "- 라우팅 예측: **LSTM** (1시간 전 발행 y_pred, 사전 계산)\n"
                "- 탄소 회계: 실측값 적분 (예측과 분리)\n"
                "- 용량: baseline 피크 × 1.2, headroom 0.8 (가정)\n"
                "- job 전력 1 kW 균일 (가정)")),
        ], style={"display": "flex", "justifyContent": "space-between", "gap": "2rem",
                  "alignItems": "flex-start"}),
        dcc.Tabs(id="lb-tabs", value="t1", className="tabs", children=[
            dcc.Tab(label="① 입력 데이터", value="t1", className="tab", selected_className="tab--selected"),
            dcc.Tab(label="② 전 / 후 비교", value="t2", className="tab", selected_className="tab--selected"),
            dcc.Tab(label="③ α 스윕 · 모드 비교", value="t3", className="tab", selected_className="tab--selected"),
            dcc.Tab(label="④ 실시간 라우팅 (LSTM)", value="t4", className="tab", selected_className="tab--selected"),
        ]),
        dcc.Loading(html.Div(id="lb-tab-body"), type="dot", delay_show=300),
        theme.hr(),
        _rerun_block(),
        dcc.Download(id="lb-download"),
        dcc.Download(id="lb-rt-download"),
    ])


def _rerun_block():
    return theme.details("🔄 실험 다시 실행 (α 스윕, 약 40분)", html.Div([
        theme.caption("baseline + 고정 α 5개 + α=auto 를 1년치 전체로 다시 돌려 results/ 와 03_라우팅결과/ 를 "
                      "갱신한다. 백그라운드 프로세스로 실행되며 아래에 로그가 표시된다."),
        dcc.ConfirmDialogProvider(
            html.Button("실험 다시 실행", className="btn btn-primary", id="lb-rerun-btn"),
            id="lb-rerun-confirm", message="1년치 실험을 다시 실행할까요? 약 40분이 걸리고 기존 결과를 덮어씁니다."),
        dcc.Interval(id="lb-exp-poll", interval=3000, n_intervals=0),
        html.Div(id="lb-exp-status"),
    ]))


@callback(Output("lb-exp-status", "children"), Output("lb-exp-poll", "disabled"),
          Input("lb-rerun-confirm", "submit_n_clicks"), Input("lb-exp-poll", "n_intervals"))
def experiments_status(submit_clicks, _n):
    if ctx.triggered_id == "lb-rerun-confirm" and submit_clicks:
        data.start_experiments()
    st = data.experiments_state()
    if st["status"] == "idle":
        return None, True
    if st["status"] == "running":
        mins = (time.time() - st["started"]) / 60
        return html.Div([theme.notice(f"실행 중… {mins:.0f}분 경과", "info"),
                         html.Pre(st["log_tail"], className="mono")]), False
    kind = "ok" if st["status"] == "done" else "error"
    msg = "완료 — 결과가 갱신되었습니다 (탭을 다시 선택하면 반영)." if kind == "ok" \
        else f"실패 (returncode={st['returncode']})"
    return html.Div([theme.notice(msg, kind), html.Pre(st["log_tail"], className="mono")]), True


# ═════════════════════ 탭 전환 ═════════════════════
@callback(Output("lb-tab-body", "children"), Input("lb-tabs", "value"))
def render_tab(tab):
    d = data.lb_load_all()
    return {"t1": tab_inputs, "t2": tab_compare, "t3": tab_sweep, "t4": tab_realtime}[tab](d)


# ═════════════════════ ① 입력 데이터 ═════════════════════
def tab_inputs(d):
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
                      caption="소스: 01_데이터/lstm_eval의 y_true (실측). 1월 1~7일은 1월 8일 프로파일 반복."),
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


# ═════════════════════ ② 전 / 후 비교 ═════════════════════
def tab_compare(d):
    runs, auto = data.lb_alpha_runs(d["summary"])
    return html.Div([
        html.Div([
            html.Label("α 선택 (0 = 레이턴시 중심 ←→ 1 = 탄소 중심)"),
            dcc.RadioItems(id="lb-alpha", value=auto or runs[0], inline=True, className="radio-inline",
                           options=[{"label": f" α = {k.split('_')[1]}", "value": k} for k in runs]),
        ], className="controls"),
        html.Div(id="lb-cmp-top"),
        theme.hr(),
        theme.section("리전별 처리 job 수 — 전 vs 후", html.Div([
            html.Div([html.Label("월 (중복 선택)"),
                      dcc.Checklist(id="lb-f-months", inline=True, className="checks-inline",
                                    options=[{"label": f" {m}월", "value": m} for m in range(1, 13)], value=[])],
                     className="col-2"),
            html.Div([html.Label("시간대 (UTC)"),
                      dcc.RangeSlider(id="lb-f-hours", min=0, max=24, step=1, value=[0, 24],
                                      marks={h: str(h) for h in range(0, 25, 3)})], className="col-1"),
        ], className="row"),
            html.Div([html.Label("출발 리전 (중복 선택)"),
                      dcc.Checklist(id="lb-f-origin", inline=True, className="checks-inline",
                                    options=[{"label": f" {r}", "value": r} for r in R], value=[])]),
            html.Div(id="lb-cmp-filtered")),
    ])


@callback(Output("lb-cmp-top", "children"), Input("lb-alpha", "value"))
def compare_top(alpha_pick):
    d = data.lb_load_all()
    summary, slots, assigns = d["summary"], d["slots"], d["assigns"]
    _, auto = data.lb_alpha_runs(summary)
    base_m = summary["baseline"]["metrics"]
    M = summary[alpha_pick]["metrics"]

    d_carbon = (M["total_carbon_kg"] / base_m["total_carbon_kg"] - 1) * 100
    kpis = theme.kpi_row(
        theme.kpi("총 탄소 배출", f"{M['total_carbon_kg']:,.0f} kg", f"{d_carbon:+.1f}% vs baseline",
                  "good" if d_carbon < 0 else "bad"),
        theme.kpi("평균 네트워크 지연", f"{M['avg_latency_ms']:.1f} ms",
                  f"{M['avg_latency_ms'] - base_m['avg_latency_ms']:+.1f} ms", "bad"),
        theme.kpi("홈 리전 처리 비율", f"{M['home_ratio'] * 100:.1f} %", f"{(M['home_ratio'] - 1) * 100:+.1f} %p"),
        theme.kpi("드롭된 job", f"{M['dropped']}", "전량 처리" if M["dropped"] == 0 else "확인 필요",
                  "good" if M["dropped"] == 0 else "bad"),
    )

    # 시간대별 배출률
    sb, sa = slots["baseline"], slots[alpha_pick]
    em = theme.base_fig(height=380, legend=dict(orientation="h", y=1.12),
                        xaxis_title="시각 (UTC)", yaxis_title="배출률 (kg CO₂/h)")
    em.add_trace(go.Scatter(x=data.lb_ts(sb.time_s), y=sb.emission_g_per_h / 1000, name="baseline (전)",
                            mode="lines", line=dict(color=theme.BASELINE_GRAY, width=1.5)))
    em.add_trace(go.Scatter(x=data.lb_ts(sa.time_s), y=sa.emission_g_per_h / 1000, name="탄소 인지 LB (후)",
                            mode="lines", line=dict(color=theme.ACCENT, width=1.5)))

    rm = summary[alpha_pick]["routing_matrix"]
    rmf = theme.base_fig(height=380, yaxis_autorange="reversed", xaxis_title="처리 리전", yaxis_title="출발 리전")
    rmf.add_trace(go.Heatmap(z=rm, x=R, y=R, colorscale=theme.BLUE_SEQ, showscale=False,
                             hovertemplate="%{y} → %{x}: %{z}개<extra></extra>"))

    # 누적 배출
    cum = theme.base_fig(height=360, legend=dict(orientation="h", y=1.12),
                         xaxis_title="시각 (UTC)", yaxis_title="누적 배출 (kg CO₂)")
    cum_runs = [("baseline", "baseline (전)", theme.BASELINE_GRAY, "solid"),
                (alpha_pick, "탄소 인지 LB (후)", theme.ACCENT, "solid")]
    if auto and alpha_pick != auto:
        cum_runs.append((auto, "α=auto 참고", theme.INK, "dot"))
    for name, lbl, color, dash_ in cum_runs:
        a = assigns[name].sort_values("submit_time")
        cum.add_trace(go.Scatter(x=data.lb_ts(a.submit_time), y=a.carbon_g.cumsum() / 1000.0, name=lbl,
                                 mode="lines", line=dict(color=color, width=2, dash=dash_)))

    # 시간별 절감량 (+ auto 슬롯 α)
    asel = assigns[alpha_pick]
    bh = (assigns["baseline"].assign(h=(assigns["baseline"].submit_time // 3600).astype(int))
          .groupby("h").carbon_g.sum())
    ah = asel.assign(h=(asel.submit_time // 3600).astype(int)).groupby("h").carbon_g.sum()
    saved = (bh.subtract(ah, fill_value=0.0) / 1000.0).sort_index()
    sv = theme.base_fig(height=340, legend=dict(orientation="h", y=1.12),
                        xaxis_title="시각 (UTC)", yaxis_title="절감량 (kg CO₂/h)",
                        yaxis2=dict(overlaying="y", side="right", range=[-0.05, 1.05], title="α", showgrid=False))
    sv.add_trace(go.Scatter(x=data.lb_ts(saved.index.to_numpy() * 3600.0), y=saved.values, name="절감량 (kg/h)",
                            mode="lines", line=dict(color=theme.ACCENT, width=1.2),
                            hovertemplate="%{x|%m-%d %H시}: %{y:.1f} kg<extra></extra>"))
    is_auto = M.get("alpha_mode") == "auto" and "alpha" in slots[alpha_pick].columns
    if is_auto:
        sa_a = slots[alpha_pick].dropna(subset=["alpha"])
        sv.add_trace(go.Scatter(x=data.lb_ts(sa_a.time_s), y=sa_a.alpha, name="슬롯 α", mode="lines", yaxis="y2",
                                line=dict(color=theme.MUTED, width=1, dash="dot"),
                                hovertemplate="α=%{y:.1f}<extra></extra>"))

    auto_block = None
    if is_auto:
        aa = slots[alpha_pick][slots[alpha_pick].alpha.notna()]
        af = theme.base_fig(height=280, xaxis_title="시각 (UTC)", yaxis_title="α", yaxis_range=[-0.05, 1.05])
        af.add_trace(go.Scatter(x=data.lb_ts(aa.time_s), y=aa.alpha, mode="lines+markers",
                                line=dict(color=theme.ACCENT, width=1.5), marker=dict(size=4, color=theme.ACCENT),
                                hovertemplate="%{x|%m-%d %H시}: α=%{y:.2f}<extra></extra>"))
        auto_block = theme.section(
            "슬롯별 자동 선택 α (파레토 무릎점)", theme.graph("lb-fig-alpha", af),
            theme.caption(f"매 슬롯(1시간) α 후보 11개(0~1, 0.1 간격)의 (평균 지연, 예상 배출) 파레토 곡선에서 "
                          f"무릎점을 자동 선택. 평균 α = {M['alpha']:.2f}. 평가 가중치 w 없이 곡선의 기하학만 사용."),
            theme.details("Q. auto의 α는 어떤 원리로 계산되나요?", theme.md(
                "매 1시간 슬롯마다 다음 4단계를 반복합니다:\n\n"
                "1. **재료 수집** — 그 시간에 제출된 job들 + 리전별 탄소강도. 탄소강도는 **LSTM이 1시간 전에 "
                "발행한 예측값(y_pred)** 을 사용합니다 — 즉 실시간 운영과 같은 조건(미래를 모름). 탄소 회계·성적 "
                "평가는 별도로 **실측값(y_true)** 으로 정산하므로 예측 오차의 비용이 결과에 정직하게 반영됩니다.\n"
                "2. **후보 곡선 그리기** — α 후보 11개(0, 0.1, …, 1)마다 ILP 배정을 각각 계산해 (평균 지연, 예상 "
                "배출) 점 11개를 찍음. 이게 '이 시간의 지연↔탄소 교환 곡선'.\n"
                "3. **무릎점 선택** — 두 축을 각각 0~1로 정규화(단위 맞추기용, 가중치 아님)한 뒤, 이상점 (0,0)에서 "
                "**유클리드 거리 √(x²+y²)가 최소**인 점을 채택: α\\* = argmin √(x_α² + y_α²). 곡선이 '급격한 개선 → "
                "미미한 개선'으로 꺾이는 코너가 수학적으로 이 지점입니다 (다목적 최적화의 이상점 최소 거리법).\n"
                "4. **적용** — 그 α의 배정을 확정하고, 다음 슬롯에서 1번부터 다시.\n\n"
                "부가 규칙: 드롭이 최소인 후보들 안에서만 선택, 거리 동률이면 작은 α(지연 우선).")),
            theme.details("Q. 왜 α가 왔다갔다 하나요? — 0인 슬롯도, 1에 가까운 슬롯도 있음", theme.md(
                "α는 미리 정해두는 튜닝 값이 아니라 **매 시간 새로 내리는 결정의 결과**입니다. 매 슬롯 \"지금 job을 "
                "옮기면 지연 1ms당 탄소를 얼마나 살 수 있나\"라는 **교환 비율**이 달라지고, 무릎점은 그 비율이 "
                "급락하는 지점이라 시간마다 다르게 나오는 게 정상입니다.\n\n"
                "**α가 1에 가까운 시간** — \"지금 옮기면 많이 벌린다\":\n"
                "- 리전 간 탄소 격차가 큼 (예: 프랑스는 새벽 원자력 잉여로 ~50 g/kWh, 인도는 ~700 g/kWh)\n"
                "- 깨끗한 리전에 용량 여유가 있음\n- 배치에 옮길 가치가 큰 job(장기 실행)이 포함됨\n\n"
                "**α = 0인 시간** — \"이번 시간은 옮길 이유가 없다\":\n"
                "- 리전 간 격차가 작아 옮겨도 얻는 게 거의 없음\n- 배치의 job들이 이미 깨끗한 리전에서 출발\n"
                "- 깨끗한 리전 용량이 앞 슬롯의 장기 job들로 이미 차 있음\n"
                "- 배치가 작아 선택지가 '안 옮김 vs 대륙 간 대량 이동' 둘뿐(계단형 곡선) → 중간 거래가 없어 "
                "보수적으로 '안 옮김'을 택함\n\n"
                "즉 이 진동은 노이즈가 아니라 **탄소강도 지형의 시간 변화를 따라가는 신호**입니다. 고정 α는 이 차이를 "
                "무시하고 매시간 같은 강도로 밀어붙이기 때문에, 격차가 없는 시간에 지연만 낭비합니다 — auto가 "
                "파레토 곡선 위쪽(★)에 있는 이유가 바로 이것입니다.")))

    return html.Div([
        kpis,
        html.Div([
            html.Div(theme.section("시간대별 배출률 — 전(baseline) vs 후", theme.graph("lb-fig-em", em)), className="col-3"),
            html.Div(theme.section("라우팅 행렬 (출발 → 처리)", theme.graph("lb-fig-rm", rmf),
                                   caption="baseline은 대각선 100%. 대각선 밖 = 탄소를 위해 이동한 job."), className="col-2"),
        ], className="row"),
        theme.section("누적 탄소 배출 — 실시간 관점", theme.graph("lb-fig-cum", cum),
                      caption="매 시각의 결정이 쌓여 벌어지는 격차. 시간을 되감지 않고 읽을 수 있는, 실시간 운영 그대로의 그림."),
        theme.section("시간별 절감량 — baseline 대비", theme.graph("lb-fig-sv", sv),
                      caption="0보다 위 = baseline보다 덜 배출한 시간, 아래 = 더 배출한 시간(예측이 빗나간 슬롯 등). "
                              "회색 점선 = auto의 슬롯 α — α가 높은 시간에 절감이 커지는지를 한 그림에서 확인. "
                              "같은 데이터가 results/hourly_savings.csv 로도 저장된다."),
        auto_block,
    ])


@callback(Output("lb-cmp-filtered", "children"),
          Input("lb-alpha", "value"), Input("lb-f-months", "value"),
          Input("lb-f-hours", "value"), Input("lb-f-origin", "value"))
def compare_filtered(alpha_pick, months, hours, origins):
    d = data.lb_load_all()
    slots, assigns, jobs = d["slots"], d["assigns"], d["jobs"]
    h_lo, h_hi = hours or (0, 24)

    asel = assigns[alpha_pick].copy()
    asel["h"] = (asel.submit_time // 3600).astype(int)
    asel["ts"] = data.lb_ts(asel.submit_time)
    asel["hod"] = asel["ts"].dt.hour
    asel["month"] = asel["ts"].dt.month

    filt = asel[(asel.hod >= h_lo) & (asel.hod < h_hi)]
    if months:
        filt = filt[filt.month.isin(months)]
    if origins:
        filt = filt[filt.origin.isin(origins)]

    hint = None
    if origins and len(origins) == 1:
        off = UTC_OFFSET[origins[0]]
        hint = theme.caption(f"💡 {origins[0]} 현지 시각 = UTC{off:+g}h → 현지 낮(8~20시) ≈ "
                             f"UTC {(8 - off) % 24:g}~{(20 - off) % 24:g}시. 시간대 슬라이더로 이 구간을 잡으면 "
                             f"'그 리전의 낮'을 보는 셈이다.")
    conv = pd.DataFrame([{
        "리전": r, "UTC 오프셋": f"UTC{UTC_OFFSET[r]:+g}",
        f"선택 구간 (UTC {h_lo}~{h_hi}시)의 현지 시각":
            f"{(h_lo + UTC_OFFSET[r]) % 24:g}시 ~ {(h_hi + UTC_OFFSET[r]) % 24:g}시",
        "현지 낮 (8~20시) ≈ UTC": f"{(8 - UTC_OFFSET[r]) % 24:g}~{(20 - UTC_OFFSET[r]) % 24:g}시",
    } for r in R])

    parts = [hint, theme.details("🕐 UTC ↔ 리전 현지 시각 대조표",
                                 theme.caption("모든 그래프·필터의 축은 UTC 하나로 통일되어 있고, 이 표가 리전별 현지 시각으로 번역해 준다."),
                                 theme.table(conv, page_size=8))]

    if filt.empty:
        parts.append(theme.notice(f"필터 조건에 맞는 job이 없습니다. 현재 데이터 범위: "
                                  f"{asel.ts.min():%Y-%m-%d} ~ {asel.ts.max():%Y-%m-%d}", "info"))
    else:
        ok = filt[~filt.dropped]
        bmap = assigns["baseline"].set_index("job_name").carbon_g
        base_kg = filt.job_name.map(bmap).sum() / 1000.0
        after_kg = filt.carbon_g.sum() / 1000.0
        parts.append(theme.kpi_row(
            theme.kpi("선택 구간 job", f"{len(filt):,}개"),
            theme.kpi("탄소 (후)", f"{after_kg:,.1f} kg",
                      f"{(after_kg / base_kg - 1) * 100:+.1f}% vs baseline" if base_kg > 0 else None, "good"),
            theme.kpi("평균 지연 (후)", f"{ok.latency_ms.mean():.1f} ms" if len(ok) else "—"),
            theme.kpi("이동 job", f"{int((ok.origin != ok.assigned).sum()):,}개"),
        ))
        hod_cnt = filt.groupby("hod").size().reindex(range(24), fill_value=0)
        hf = theme.base_fig(height=180, xaxis_title="선택 구간의 시간대(UTC) 분포", yaxis_title="job 수", showlegend=False)
        hf.add_trace(go.Bar(x=list(range(24)), y=hod_cnt.values, marker_color=theme.ACCENT,
                            hovertemplate="UTC %{x}시: %{y}개<extra></extra>"))
        parts.append(theme.graph("lb-fig-hod", hf))

    before = filt.origin.value_counts().reindex(R, fill_value=0)
    after = filt[~filt.dropped].assigned.value_counts().reindex(R, fill_value=0)
    bf = theme.base_fig(height=340, barmode="group", bargap=0.25, legend=dict(orientation="h", y=1.15),
                        yaxis_title="처리 job 수")
    bf.add_trace(go.Bar(x=R, y=before.values, name="baseline (전 = 출발 리전)", marker_color=theme.BASELINE_GRAY))
    bf.add_trace(go.Bar(x=R, y=after.values, name="탄소 인지 LB (후)", marker_color=theme.ACCENT))
    parts.append(theme.graph("lb-fig-before-after", bf))
    parts.append(theme.caption(f"필터 적용: {len(filt):,}개 / 전체 {len(asel):,}개 (미선택 = 전체). 시간 필터는 전부 UTC 기준. "
                               "탄소강도가 낮은 리전으로 부하가 이동하는 정도가 α에 따라 달라진다."))

    # job별 배정 내역
    alpha_by_h = {}
    if "alpha" in slots[alpha_pick].columns:
        sa = slots[alpha_pick]
        alpha_by_h = {int(t // 3600): a for t, a in zip(sa.time_s, sa.alpha) if pd.notna(a)}
    view = filt.sort_values("submit_time")
    tbl = jobs.set_index("job_name").loc[view.job_name].reset_index()
    tbl["α"] = view.h.map(alpha_by_h).values
    tbl["배정"] = view.assigned.fillna("(드롭)").values
    parts.append(theme.section(
        "job별 배정 내역 — jobs.csv + 그 시각의 α + 배정 리전",
        theme.caption("행 = job 하나: 언제 제출됐고, 그 슬롯의 α가 얼마였고, 그래서 어디로 배정됐는지. 위 필터가 그대로 적용된다."),
        theme.notice(f"{len(tbl):,}행 중 앞 {SHOW_MAX:,}행만 표시합니다. 전체는 아래 CSV로 받으세요.", "info")
        if len(tbl) > SHOW_MAX else None,
        theme.table(tbl.head(SHOW_MAX), page_size=25),
        html.Button(f"⬇️ 전체 {len(tbl):,}행 CSV 다운로드 (Excel 호환)", id="lb-download-btn", n_clicks=0,
                    className="btn", style={"marginTop": "0.5rem"}),
    ))
    return html.Div(parts)


@callback(Output("lb-download", "data"), Input("lb-download-btn", "n_clicks"),
          State("lb-alpha", "value"), State("lb-f-months", "value"),
          State("lb-f-hours", "value"), State("lb-f-origin", "value"), prevent_initial_call=True)
def download_assignments(n, alpha_pick, months, hours, origins):
    if not n:
        return dash.no_update
    d = data.lb_load_all()
    slots, assigns, jobs = d["slots"], d["assigns"], d["jobs"]
    h_lo, h_hi = hours or (0, 24)
    asel = assigns[alpha_pick].copy()
    asel["h"] = (asel.submit_time // 3600).astype(int)
    ts = data.lb_ts(asel.submit_time)
    asel["hod"], asel["month"] = ts.dt.hour, ts.dt.month
    filt = asel[(asel.hod >= h_lo) & (asel.hod < h_hi)]
    if months:
        filt = filt[filt.month.isin(months)]
    if origins:
        filt = filt[filt.origin.isin(origins)]
    alpha_by_h = {}
    if "alpha" in slots[alpha_pick].columns:
        sa = slots[alpha_pick]
        alpha_by_h = {int(t // 3600): a for t, a in zip(sa.time_s, sa.alpha) if pd.notna(a)}
    view = filt.sort_values("submit_time")
    tbl = jobs.set_index("job_name").loc[view.job_name].reset_index()
    tbl["α"] = view.h.map(alpha_by_h).values
    tbl["배정"] = view.assigned.fillna("(드롭)").values
    return dcc.send_data_frame(tbl.to_csv, f"jobs_routed_{alpha_pick}.csv", index=False, encoding="utf-8-sig")


# ═════════════════════ ③ α 스윕 · 모드 비교 ═════════════════════
def tab_sweep(d):
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
    for key, title, desc in [("alpha_0", "🏠 지역(레이턴시) 중심", "α=0 — 항상 가장 가까운 리전"),
                             ("alpha_0.5", "⚖️ 균형", "α=0.5 — 탄소·지연 절충"),
                             ("alpha_1", "🌱 탄소 중심", "α=1 — 항상 가장 깨끗한 리전")]:
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
    for name in ["baseline"] + runs:
        m = summary[name]["metrics"]
        rows.append({
            "run": name, "모드": m["mode"],
            "α": ("—" if m["mode"] != "ilp" else f"auto (평균 {m['alpha']:g})"
                  if m.get("alpha_mode") == "auto" else f"{m['alpha']:g}"),
            "총탄소 (kg)": f"{m['total_carbon_kg']:,.1f}", "평균지연 (ms)": f"{m['avg_latency_ms']:.1f}",
            "p95지연 (ms)": f"{m['p95_latency_ms']:.0f}", "홈리전": f"{m['home_ratio'] * 100:.1f}%",
            "드롭": m["dropped"], "탄소절감 (vs baseline)": f"{saving_pct(m):.1f}%",
        })

    return html.Div([
        theme.section("파레토 곡선 — 사후 평가 (1년 집계)",
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
                          html.Div(theme.details("Q. 곡선이 왜 이런 모양인가요? — 무릎점이 생기는 이유", theme.md(
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
                              "나온다 — 이 별이 곡선 위에 있다는 것 자체가 시변 α의 존재 증명."), open_=True),
                                   className="col-1"),
                      ], className="row")),
        theme.hr(),
        theme.section("세 가지 운영 모드", html.Div(mode_cards, className="row")),
        theme.hr(),
        theme.section("전체 결과 표", theme.table(pd.DataFrame(rows), page_size=10),
                      caption="고정 α run들은 auto의 비교 기준. auto = 매 슬롯 파레토 무릎점 α 자동 선택."),
    ])


# ═════════════════════ ④ 실시간 라우팅 (LSTM 서빙 데모) ═════════════════════
def tab_realtime(_d):
    t_min, t_max = data.rt_t_range()
    marks = {t: (data.RT_BASE + pd.Timedelta(hours=t)).strftime("%m-%d") for t in range(t_min, t_max + 1, 24 * 30)}
    return html.Div([
        theme.caption("①~③탭은 사전 계산된 1년치(2025) 결과지만, 이 탭은 매 프레임 실제 LSTM 모델(torch)이 2026 데모 "
                      "데이터로 24시간 예측을 새로 계산하고 ILP가 그 자리에서 배정한다. ▶ 재생을 누르면 1시간 슬롯씩 자동 진행."),
        dcc.Interval(id="lb-rt-tick", interval=2000, n_intervals=0, disabled=True),
        html.Div([
            html.Div([html.Label(f"슬롯 시각 t (시간) — t=0 ↔ 2026-01-01 00:00 UTC, LSTM은 이력 168h 이후({t_min})부터 "
                                 f"데모 데이터 끝-24h({t_max})까지"),
                      dcc.Slider(id="lb-rt-t", min=t_min, max=t_max, step=1, value=200, marks=marks,
                                 tooltip={"placement": "bottom", "always_visible": True})], className="col-3"),
            html.Div([html.Label("α (탄소↔지연)"),
                      dcc.Dropdown(id="lb-rt-alpha", clearable=False, searchable=False, value="auto",
                                   options=[{"label": a, "value": a} for a in ["auto", "0", "0.25", "0.5", "0.75", "1"]])],
                     className="col-1"),
            html.Div([html.Label("재생 배속"),
                      dcc.Dropdown(id="lb-rt-speed", clearable=False, searchable=False, value="1×",
                                   options=[{"label": k, "value": k} for k in RT_SPEEDS])], className="col-1"),
            html.Div([html.Label(" "), html.Button("▶ 재생", id="lb-rt-play", n_clicks=0,
                                                    className="btn btn-primary", style={"width": "100%"})],
                     className="col-1"),
        ], className="row", style={"alignItems": "flex-end"}),
        dcc.Loading(html.Div(id="lb-rt-body"), type="dot", delay_show=200),
    ])


@callback(Output("lb-rt-tick", "disabled"), Output("lb-rt-play", "children"),
          Input("lb-rt-play", "n_clicks"), State("lb-rt-tick", "disabled"), prevent_initial_call=True)
def rt_toggle(_n, disabled):
    playing = disabled  # 눌렀으니 반전
    return (not playing), ("⏸ 일시정지" if playing else "▶ 재생")


@callback(Output("lb-rt-tick", "interval"), Input("lb-rt-speed", "value"))
def rt_speed(speed):
    return RT_SPEEDS.get(speed, 2000)


@callback(Output("lb-rt-t", "value"), Output("lb-rt-tick", "disabled", allow_duplicate=True),
          Output("lb-rt-play", "children", allow_duplicate=True),
          Input("lb-rt-tick", "n_intervals"), State("lb-rt-t", "value"), State("lb-rt-t", "max"),
          prevent_initial_call=True)
def rt_advance(_n, t, t_max):
    if t is None or t >= t_max:
        return dash.no_update, True, "▶ 재생"
    return t + 1, dash.no_update, dash.no_update


@callback(Output("lb-rt-body", "children"), Input("lb-rt-t", "value"), Input("lb-rt-alpha", "value"))
def rt_render(t, alpha):
    t = int(t or 200)
    res = data.realtime_route_slot(t, alpha)
    s = res["summary"]
    now = data.RT_BASE + pd.Timedelta(hours=t)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
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
    if not adf.empty:
        moved = adf[adf.origin != adf.assigned]
        assign_block = html.Div([theme.caption(f"{len(adf)}개 중 {len(moved)}개가 홈 리전 밖으로 이동"),
                                 theme.table(adf, page_size=15)])
    else:
        assign_block = theme.caption("이 슬롯에 제출된 job이 없습니다 — 예측만 발행됨.")

    return html.Div([
        html.H2(f"🕐 {now.year}년 {now.month}월 {now.day}일({weekdays[now.dayofweek]}) {now:%H:%M} UTC · t={t}"),
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
def rt_download(n, t, alpha):
    if not n:
        return dash.no_update
    res = data.realtime_route_slot(int(t), alpha)
    return dict(content=json.dumps(res, ensure_ascii=False, indent=2), filename=f"route_t{int(t)}.json")
