"""② 전 / 후 비교 — α 선택 → KPI · 배출률 · 라우팅 행렬 · 누적 배출 · 시간별 절감 · 슬롯 α,
그리고 월/시간대/출발 리전 필터 → 리전별 처리 수 · job별 배정 내역 · CSV 다운로드."""

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from interface.dashboard import data, theme
from interface.dashboard.lb_tabs.common import UTC_OFFSET, R

SHOW_MAX = 5000   # 표에 그리는 최대 행 — 그 이상은 CSV 로

_AUTO_QA_HOW = (
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
    "부가 규칙: 드롭이 최소인 후보들 안에서만 선택, 거리 동률이면 작은 α(지연 우선)."
)
_AUTO_QA_WHY = (
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
    "파레토 곡선 위쪽(★)에 있는 이유가 바로 이것입니다."
)


def render(d: dict) -> html.Div:
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


# ── α 선택에 따라 바뀌는 상단 ──────────────────────────────────
@callback(Output("lb-cmp-top", "children"), Input("lb-alpha", "value"))
def compare_top(alpha_pick):
    d = data.lb_load_all()
    summary, slots, assigns = d["summary"], d["slots"], d["assigns"]
    _, auto = data.lb_alpha_runs(summary)
    base_m = summary["baseline"]["metrics"]
    m = summary[alpha_pick]["metrics"]

    d_carbon = (m["total_carbon_kg"] / base_m["total_carbon_kg"] - 1) * 100
    kpis = theme.kpi_row(
        theme.kpi("총 탄소 배출", f"{m['total_carbon_kg']:,.0f} kg", f"{d_carbon:+.1f}% vs baseline",
                  "good" if d_carbon < 0 else "bad"),
        theme.kpi("평균 네트워크 지연", f"{m['avg_latency_ms']:.1f} ms",
                  f"{m['avg_latency_ms'] - base_m['avg_latency_ms']:+.1f} ms", "bad"),
        theme.kpi("홈 리전 처리 비율", f"{m['home_ratio'] * 100:.1f} %", f"{(m['home_ratio'] - 1) * 100:+.1f} %p"),
        theme.kpi("드롭된 job", f"{m['dropped']}", "전량 처리" if m["dropped"] == 0 else "확인 필요",
                  "good" if m["dropped"] == 0 else "bad"),
    )

    sb, sa = slots["baseline"], slots[alpha_pick]
    em = theme.base_fig(height=380, legend=dict(orientation="h", y=1.12),
                        xaxis_title="시각 (UTC)", yaxis_title="배출률 (kg CO₂/h)")
    em.add_trace(go.Scatter(x=data.lb_ts(sb.time_s), y=sb.emission_g_per_h / 1000, name="baseline (전)",
                            mode="lines", line=dict(color=theme.BASELINE_GRAY, width=1.5)))
    em.add_trace(go.Scatter(x=data.lb_ts(sa.time_s), y=sa.emission_g_per_h / 1000, name="탄소 인지 LB (후)",
                            mode="lines", line=dict(color=theme.ACCENT, width=1.5)))

    rmf = theme.base_fig(height=380, yaxis_autorange="reversed", xaxis_title="처리 리전", yaxis_title="출발 리전")
    rmf.add_trace(go.Heatmap(z=summary[alpha_pick]["routing_matrix"], x=R, y=R, colorscale=theme.BLUE_SEQ,
                             showscale=False, hovertemplate="%{y} → %{x}: %{z}개<extra></extra>"))

    cum = theme.base_fig(height=360, legend=dict(orientation="h", y=1.12),
                         xaxis_title="시각 (UTC)", yaxis_title="누적 배출 (kg CO₂)")
    cum_runs = [("baseline", "baseline (전)", theme.BASELINE_GRAY, "solid"),
                (alpha_pick, "탄소 인지 LB (후)", theme.ACCENT, "solid")]
    if auto and alpha_pick != auto:
        cum_runs.append((auto, "α=auto 참고", theme.INK, "dot"))
    for name, lbl, color, dash_style in cum_runs:
        a = assigns[name].sort_values("submit_time")
        cum.add_trace(go.Scatter(x=data.lb_ts(a.submit_time), y=a.carbon_g.cumsum() / 1000.0, name=lbl,
                                 mode="lines", line=dict(color=color, width=2, dash=dash_style)))

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
    is_auto = m.get("alpha_mode") == "auto" and "alpha" in slots[alpha_pick].columns
    if is_auto:
        sa_a = slots[alpha_pick].dropna(subset=["alpha"])
        sv.add_trace(go.Scatter(x=data.lb_ts(sa_a.time_s), y=sa_a.alpha, name="슬롯 α", mode="lines", yaxis="y2",
                                line=dict(color=theme.MUTED, width=1, dash="dot"),
                                hovertemplate="α=%{y:.1f}<extra></extra>"))

    auto_block = _auto_alpha_block(slots[alpha_pick], m) if is_auto else None

    return html.Div([
        kpis,
        html.Div([
            html.Div(theme.section("시간대별 배출률 — 전(baseline) vs 후", theme.graph("lb-fig-em", em)),
                     className="col-3"),
            html.Div(theme.section("라우팅 행렬 (출발 → 처리)", theme.graph("lb-fig-rm", rmf),
                                   caption="baseline은 대각선 100%. 대각선 밖 = 탄소를 위해 이동한 job."),
                     className="col-2"),
        ], className="row"),
        theme.section("누적 탄소 배출 — 실시간 관점", theme.graph("lb-fig-cum", cum),
                      caption="매 시각의 결정이 쌓여 벌어지는 격차. 시간을 되감지 않고 읽을 수 있는, 실시간 운영 그대로의 그림."),
        theme.section("시간별 절감량 — baseline 대비", theme.graph("lb-fig-sv", sv),
                      caption="0보다 위 = baseline보다 덜 배출한 시간, 아래 = 더 배출한 시간(예측이 빗나간 슬롯 등). "
                              "회색 점선 = auto의 슬롯 α — α가 높은 시간에 절감이 커지는지를 한 그림에서 확인. "
                              "같은 데이터가 results/hourly_savings.csv 로도 저장된다."),
        auto_block,
    ])


def _auto_alpha_block(slot_df: pd.DataFrame, m: dict) -> html.Div:
    aa = slot_df[slot_df.alpha.notna()]
    af = theme.base_fig(height=280, xaxis_title="시각 (UTC)", yaxis_title="α", yaxis_range=[-0.05, 1.05])
    af.add_trace(go.Scatter(x=data.lb_ts(aa.time_s), y=aa.alpha, mode="lines+markers",
                            line=dict(color=theme.ACCENT, width=1.5), marker=dict(size=4, color=theme.ACCENT),
                            hovertemplate="%{x|%m-%d %H시}: α=%{y:.2f}<extra></extra>"))
    return theme.section(
        "슬롯별 자동 선택 α (파레토 무릎점)", theme.graph("lb-fig-alpha", af),
        theme.caption(f"매 슬롯(1시간) α 후보 11개(0~1, 0.1 간격)의 (평균 지연, 예상 배출) 파레토 곡선에서 "
                      f"무릎점을 자동 선택. 평균 α = {m['alpha']:.2f}. 평가 가중치 w 없이 곡선의 기하학만 사용."),
        theme.details("Q. auto의 α는 어떤 원리로 계산되나요?", theme.md(_AUTO_QA_HOW)),
        theme.details("Q. 왜 α가 왔다갔다 하나요? — 0인 슬롯도, 1에 가까운 슬롯도 있음", theme.md(_AUTO_QA_WHY)))


# ── 필터에 따라 바뀌는 하단 ─────────────────────────────────────
def _filtered_frame(alpha_pick, months, hours, origins):
    """필터가 적용된 job 배정 프레임과 (필터 전 전체) 프레임을 돌려준다."""
    d = data.lb_load_all()
    h_lo, h_hi = hours or (0, 24)
    asel = d["assigns"][alpha_pick].copy()
    asel["h"] = (asel.submit_time // 3600).astype(int)
    ts = data.lb_ts(asel.submit_time)
    asel["hod"], asel["month"] = ts.dt.hour, ts.dt.month
    asel["ts"] = ts
    filt = asel[(asel.hod >= h_lo) & (asel.hod < h_hi)]
    if months:
        filt = filt[filt.month.isin(months)]
    if origins:
        filt = filt[filt.origin.isin(origins)]
    return d, asel, filt, (h_lo, h_hi)


def _assignment_table(d, alpha_pick, filt):
    slots, jobs = d["slots"], d["jobs"]
    alpha_by_h = {}
    if "alpha" in slots[alpha_pick].columns:
        sa = slots[alpha_pick]
        alpha_by_h = {int(t // 3600): a for t, a in zip(sa.time_s, sa.alpha) if pd.notna(a)}
    view = filt.sort_values("submit_time")
    tbl = jobs.set_index("job_name").loc[view.job_name].reset_index()
    tbl["α"] = view.h.map(alpha_by_h).values
    tbl["배정"] = view.assigned.fillna("(드롭)").values
    return tbl


@callback(Output("lb-cmp-filtered", "children"),
          Input("lb-alpha", "value"), Input("lb-f-months", "value"),
          Input("lb-f-hours", "value"), Input("lb-f-origin", "value"))
def compare_filtered(alpha_pick, months, hours, origins):
    d, asel, filt, (h_lo, h_hi) = _filtered_frame(alpha_pick, months, hours, origins)
    assigns = d["assigns"]

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

    parts = [hint, theme.details(
        "🕐 UTC ↔ 리전 현지 시각 대조표",
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
        hf = theme.base_fig(height=180, xaxis_title="선택 구간의 시간대(UTC) 분포", yaxis_title="job 수",
                            showlegend=False)
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

    tbl = _assignment_table(d, alpha_pick, filt)
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
    d, _, filt, _ = _filtered_frame(alpha_pick, months, hours, origins)
    tbl = _assignment_table(d, alpha_pick, filt)
    return dcc.send_data_frame(tbl.to_csv, f"jobs_routed_{alpha_pick}.csv", index=False, encoding="utf-8-sig")
