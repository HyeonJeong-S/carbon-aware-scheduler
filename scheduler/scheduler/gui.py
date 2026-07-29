"""탄소 인식 time-shift 스케줄러를 브라우저에서 테스트하는 Streamlit GUI.

실행:
    streamlit run scheduler/gui.py

레이아웃:
    - 왼쪽 사이드바: 시뮬레이션 실행 + 시점(일자/시각) 조절 + 자동 재생
    - 오른쪽 메인: 지도(나라별 실행 job 수) + 현재 실행 중 job 목록 +
      요청→실행(time-shift) 타임라인. 시점을 바꾸거나 자동재생하면 즉시 갱신.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scheduler import carbon_forecast, data_loader, metrics, simulator
from scheduler.config import MODES, ZONE_LABELS, ZONE_TO_ISO3

st.set_page_config(page_title="탄소 인식 스케줄러", layout="wide", initial_sidebar_state="expanded")

# ── 시각 스타일 (로드밸런서 대시보드와 통일된 팔레트) ──
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"
BASELINE_GRAY, CARBON_BLUE, OURS_GREEN = "#898781", "#2a78d6", "#1baf7a"
PLOT_LAYOUT = dict(
    font=dict(family="system-ui, -apple-system, sans-serif", color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
    hovermode="closest", showlegend=False,
)


def _style_axes(fig):
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig

_SCHED_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_SCHED_ROOT)

JOB_DIR = os.path.join(_SCHED_ROOT, "data", "job")
ROUTED_CSV_PATH = os.path.join(JOB_DIR, "jobs_routed_alpha_auto.csv")
JOBS_CSV_PATH = os.path.join(JOB_DIR, "jobs.csv")

# 2025년 1년치: 로드밸런서와 같은 job 목록 + 같은 배정 결과를 그대로 사용
YEAR_JOBS_CSV = os.path.join(_REPO_ROOT, "load_balancer", "01_데이터", "jobs.csv")
YEAR_ASSIGN_CSV = os.path.join(_REPO_ROOT, "load_balancer", "02_프레임워크",
                               "results", "assign_alpha_auto.csv")
USING_YEAR = os.path.exists(YEAR_JOBS_CSV) and os.path.exists(YEAR_ASSIGN_CSV)
USING_ROUTED = os.path.exists(ROUTED_CSV_PATH)

# 시뮬레이션 t=0 이 가리키는 실제 시각 — 모두 UTC(협정 세계시) 기준.
# 2025년 1년치: 로드밸런서·LSTM eval_records와 동일한 축.
YEAR_BASE_TIME = pd.Timestamp("2025-01-01 00:00:00")
# 7일치 폴백: jobs.csv 생성 규약(README_jobs.md)의 t=0.
WEEK_BASE_TIME = pd.Timestamp("2026-01-01 00:00:00")

COLOR_SHIFT = "#2e7d32"       # 실행 구간(초록)
COLOR_WAIT = "#c9c9c9"        # 요청~실행 대기(점선 회색)
COLOR_SUBMIT = "#e08600"      # 요청 시각 마커(주황)
PLAY_INTERVAL_SEC = 0.6

# 나라별 대략적 중심 좌표 (lon, lat) — 지도 위 job 개수 숫자 위치
CENTROIDS = {
    "USA": (-98, 39), "FRA": (2, 47), "DEU": (10, 51),
    "KOR": (128, 36), "IND": (79, 22), "JPN": (138, 37),
}


def load_jobs():
    """2025년 1년치(로드밸런서와 동일 데이터)를 우선 사용."""
    if USING_YEAR:
        return data_loader.load_jobs_with_assignment(YEAR_JOBS_CSV, YEAR_ASSIGN_CSV), "year"
    if USING_ROUTED:
        return data_loader.load_routed_jobs_csv(ROUTED_CSV_PATH), "week"
    return data_loader.load_jobs_csv(JOBS_CSV_PATH), "week"


def run_simulation():
    jobs, scope = load_jobs()
    st.session_state["data_scope"] = scope
    sim_horizon = max(j["deadline"] for j in jobs) + 24
    # 탄소 회계는 실측 시계열로 해야 한다. 예측(LSTM)으로 판단하고 채점은 더미로 하면
    # 판단 기준과 채점 기준이 어긋나 절감률이 음수로 나온다.
    carbon_series, is_real = carbon_forecast.load_actual_series(int(sim_horizon) + 48)
    results = simulator.run_all_modes(
        jobs, carbon_series, modes=["carbon_lb_immediate", "carbon_lb_timeshift"]
    )
    st.session_state["results_by_mode"] = results
    st.session_state["carbon_series"] = carbon_series
    st.session_state["carbon_is_real"] = is_real
    st.session_state["horizon_hours"] = sim_horizon
    st.session_state["n_jobs_run"] = len(jobs)


def running_jobs(results, t):
    return [r for r in results
            if r["scheduled_start"] <= t < r["scheduled_start"] + r["duration"]]


def country_job_counts(jobs_at_t):
    counts = {}
    for r in jobs_at_t:
        iso = ZONE_TO_ISO3.get(r["region"], r["region"])
        counts[iso] = counts.get(iso, 0) + 1
    return counts


def sim_base():
    """시뮬레이션 t=0 에 대응하는 실제 시각 (UTC).

    2025년 1년치는 로드밸런서·LSTM과 같은 2025-01-01 00:00 UTC 기준,
    7일치 폴백 데이터는 job 생성 규약대로 2026-01-01 00:00 UTC 기준.
    """
    if st.session_state.get("data_scope") == "year":
        return YEAR_BASE_TIME
    return WEEK_BASE_TIME


def to_utc(h):
    """시뮬레이션 시각(시간 단위) -> 실제 UTC datetime."""
    return sim_base() + pd.Timedelta(hours=float(h))


def fmt_dt(h):
    """시뮬레이션 시각 -> 'YYYY-MM-DD HH:MM' (UTC)."""
    return to_utc(h).strftime("%Y-%m-%d %H:%M")


def fmt_date(h):
    """시뮬레이션 시각 -> 'YYYY-MM-DD' (UTC)."""
    return to_utc(h).strftime("%Y-%m-%d")


def draw_map(counts, color):
    fig = go.Figure()
    iso3 = list(counts.keys())
    # 빈 상태에서도 지도(지리) 형태를 유지하기 위해 항상 scattergeo 트레이스를 둔다.
    pts = [(CENTROIDS[c][0], CENTROIDS[c][1], counts[c]) for c in iso3 if c in CENTROIDS]
    if iso3:
        fig.add_trace(go.Choropleth(
            locations=iso3, locationmode="ISO-3", z=[1] * len(iso3),
            colorscale=[[0, color], [1, color]], showscale=False,
            marker_line_color="white", marker_line_width=0.6, hoverinfo="location",
        ))
    fig.add_trace(go.Scattergeo(
        lon=[p[0] for p in pts], lat=[p[1] for p in pts],
        text=[str(p[2]) for p in pts], mode="text",
        textfont=dict(size=18, color="white", family="Arial Black"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=175, dragmode=False,
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                 showcoastlines=True, coastlinecolor="#d0d0d0",
                 showland=True, landcolor="#f2f2f2", projection_type="natural earth"),
    )
    return fig


def _clip(x0, x1, lo=0.0, hi=24.0):
    a, b = max(x0, lo), min(x1, hi)
    return (a, b) if b > a else None


def draw_timeline(jobs_at_t, t, day_start):
    """선택한 날(0~24시) 기준으로 요청(주황◆)→대기(점선)→실행(초록)을 job별로 표시.

    x축은 항상 그 날의 0~24시로 고정. 전날 요청/시작한 부분은 왼쪽 끝(0시)에서 잘림.
    """
    js = sorted(jobs_at_t, key=lambda r: r["scheduled_start"])[:15]
    fig = go.Figure()
    for r in js:
        jid = r["job_id"]
        sub = r["submit_time"] - day_start
        start = r["scheduled_start"] - day_start
        fin = start + r["duration"]
        wseg = _clip(sub, start)
        if wseg:  # 대기 구간
            fig.add_trace(go.Scatter(
                x=list(wseg), y=[jid, jid], mode="lines",
                line=dict(color=COLOR_WAIT, width=3, dash="dot"),
                showlegend=False, hoverinfo="skip"))
        eseg = _clip(start, fin)
        if eseg:  # 실행 구간
            fig.add_trace(go.Scatter(
                x=list(eseg), y=[jid, jid], mode="lines",
                line=dict(color=COLOR_SHIFT, width=9),
                showlegend=False, hoverinfo="text",
                hovertext=f"{jid}<br>요청 {fmt_dt(r['submit_time'])}"
                          f"<br>실행 {fmt_dt(r['scheduled_start'])}"))
        if 0 <= sub <= 24:  # 요청 마커 (그 날 안에 요청된 경우만)
            fig.add_trace(go.Scatter(
                x=[sub], y=[jid], mode="markers",
                marker=dict(color=COLOR_SUBMIT, size=9, symbol="diamond"),
                showlegend=False, hoverinfo="text",
                hovertext=f"요청 {fmt_dt(r['submit_time'])}"))
    fig.add_vline(x=t - day_start, line=dict(color="#d33", width=1.5, dash="dash"))
    fig.update_layout(
        height=210, margin=dict(l=0, r=0, t=8, b=0),
        yaxis=dict(autorange="reversed", title=None), plot_bgcolor="white",
    )
    fig.update_xaxes(range=[0, 24], tickvals=list(range(0, 25, 3)),
                     title="시각 (시, UTC)", gridcolor="#eee")
    return fig


def carbon_up_to(results, t):
    return sum(r["carbon_emitted"] for r in results if r["scheduled_start"] <= t)


TABLE_COLS = ["job_id", "k", "지역", "요청", "실행 시작", "종료 예정",
              "즉시실행(gCO₂)", "time-shift(gCO₂)", "절감(gCO₂)"]


def jobs_table(jobs_at_t, t, imm_by_id):
    """imm_by_id: {job_id: 즉시실행 시 배출량}.

    즉시실행(gCO₂)  : 안 미루고 요청 즉시 실행했을 때의 배출량
    time-shift(gCO₂): 실제로 time-shift 해서 실행한 배출량(=실제 배출)
    절감(gCO₂)      : 즉시실행 - time-shift (시간 이동으로 아낀 양)
    실행 중 job이 없어도 컬럼(헤더)은 항상 유지해 레이아웃이 흔들리지 않게 한다.
    """
    rows = []
    for r in jobs_at_t:
        region = r["region"]
        finish = r["scheduled_start"] + r["duration"]
        shift_c = r["carbon_emitted"]
        imm_c = imm_by_id.get(r["job_id"], shift_c)
        rows.append({
            "job_id": r["job_id"],
            "k": r["k"],
            "지역": f"{region} ({ZONE_LABELS.get(region, region)})",
            "요청": fmt_dt(r["submit_time"]),
            "실행 시작": fmt_dt(r["scheduled_start"]),
            "종료 예정": fmt_dt(finish),
            "즉시실행(gCO₂)": round(imm_c, 1),
            "time-shift(gCO₂)": round(shift_c, 1),
            "절감(gCO₂)": round(imm_c - shift_c, 1),
        })
    df = pd.DataFrame(rows, columns=TABLE_COLS)
    if not df.empty:
        df = df.sort_values("절감(gCO₂)", ascending=False).reset_index(drop=True)
    return df


# ─────────────────────── 사이드바 ───────────────────────
# 페이지에 들어오면 (로드밸런서처럼) 자동으로 1년치 시뮬레이션이 준비되어 있게 한다.
if st.session_state.get("results_by_mode") is None:
    with st.spinner("2025년 1년치 시뮬레이션 실행 중… (최초 1회)"):
        run_simulation()
    st.session_state["playing"] = False

with st.sidebar:
    st.header("시뮬레이션 설정")

    scope = st.session_state.get("data_scope")
    n_jobs = st.session_state.get("n_jobs_run", 0)
    days = int(st.session_state.get("horizon_hours", 0)) // 24
    st.caption(f"{'2025년 1년치' if scope == 'year' else '7일치'} · job {n_jobs:,}개 · {days}일")
    st.caption(carbon_forecast.backend_info())

    if st.button("다시 실행", width="stretch"):
        with st.spinner("실행 중..."):
            run_simulation()
        st.session_state["playing"] = False

    st.caption("이 페이지는 2025년 1년치 시뮬레이션 **검증 결과**만 보여줍니다. "
               "시점별 지도·타임라인은 '최종' 페이지에 있습니다.")


# ─────────────────────── 메인 ───────────────────────
st.title("스케줄러 검증 — 2025년 1년치 결과")

results_by_mode = st.session_state.get("results_by_mode")
if results_by_mode is None:
    st.error("시뮬레이션 결과를 만들지 못했습니다. 왼쪽의 '다시 실행'을 눌러주세요.")
    st.stop()

immediate = results_by_mode["carbon_lb_immediate"]
shifted = results_by_mode["carbon_lb_timeshift"]

comparison = metrics.compare_modes(results_by_mode)
total_imm = comparison["carbon_lb_immediate"]["total_carbon"]
total_shift = comparison["carbon_lb_timeshift"]["total_carbon"]
overall_pct = (1 - total_shift / total_imm) * 100 if total_imm else 0.0
avg_delay = comparison["carbon_lb_timeshift"]["avg_delay"]
n_jobs = comparison["carbon_lb_timeshift"]["n_jobs"]
slo_viol = comparison["carbon_lb_timeshift"]["slo_violation_rate"]
saved_total = total_imm - total_shift

# ── 핵심 검증 지표 (KPI) ──
m1, m2, m3, m4 = st.columns(4)
m1.metric("time-shift 절감률", f"{overall_pct:.1f}%", "즉시실행 대비")
m2.metric("절감한 탄소", f"{saved_total/1e6:,.2f} tCO₂", f"{saved_total:,.0f} g")
m3.metric("평균 지연", f"{avg_delay:.2f} h")
m4.metric("SLO(마감) 위반율", f"{slo_viol*100:.2f}%",
          "정상" if slo_viol == 0 else "위반 발생", delta_color="off")

st.divider()

col_l, col_r = st.columns([1, 1])

# ── (좌) 비교군별 총 탄소 배출 — 스타일 막대 ──
with col_l:
    st.subheader("비교군별 총 탄소 배출량")
    modes_order = ["simple_lb_immediate", "carbon_lb_immediate", "carbon_lb_timeshift"]
    modes_order = [m for m in modes_order if m in comparison]
    labels = {"simple_lb_immediate": "단순 LB", "carbon_lb_immediate": "탄소 LB",
              "carbon_lb_timeshift": "탄소 LB + time-shift (ours)"}
    colors = {"simple_lb_immediate": BASELINE_GRAY, "carbon_lb_immediate": CARBON_BLUE,
              "carbon_lb_timeshift": OURS_GREEN}
    vals = [comparison[m]["total_carbon"] / 1e6 for m in modes_order]
    names = [labels[m] for m in modes_order]
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h", marker_color=[colors[m] for m in modes_order],
        text=[f"{v:,.1f} tCO₂" for v in vals], textposition="auto",
        hovertemplate="%{y}: %{x:.2f} tCO₂<extra></extra>"))
    fig.update_layout(**PLOT_LAYOUT, height=300, xaxis_title="총 탄소 배출 (tCO₂)")
    _style_axes(fig)
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(f"job {n_jobs:,}개 · 탄소 회계는 2025년 실측값 기준")

# ── (우) 중요도(k)별 지연·절감 — 이중축 스타일 막대 ──
with col_r:
    st.subheader("중요도(k)별 지연·절감")
    imm_by_id = {r["job_id"]: r["carbon_emitted"] for r in immediate}
    agg = {}
    for r in shifted:
        d = agg.setdefault(r["k"], {"n": 0, "delay": 0.0, "saved": 0.0, "viol": 0})
        d["n"] += 1
        d["delay"] += r["delay"]
        d["saved"] += imm_by_id.get(r["job_id"], r["carbon_emitted"]) - r["carbon_emitted"]
        d["viol"] += 0 if r["slo_satisfied"] else 1
    ks = sorted(agg, reverse=True)
    kx = [f"k={k}" for k in ks]
    delays = [agg[k]["delay"] / agg[k]["n"] if agg[k]["n"] else 0 for k in ks]
    saves = [agg[k]["saved"] / 1e6 for k in ks]
    fig2 = go.Figure()
    fig2.add_bar(x=kx, y=delays, name="평균 지연(h)", marker_color=CARBON_BLUE,
                 yaxis="y", hovertemplate="%{x} 평균지연 %{y:.2f}h<extra></extra>")
    fig2.add_bar(x=kx, y=saves, name="절감(tCO₂)", marker_color=OURS_GREEN,
                 yaxis="y2", hovertemplate="%{x} 절감 %{y:.2f} tCO₂<extra></extra>")
    fig2.update_layout(
        font=PLOT_LAYOUT["font"], paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=30, b=10), height=300,
        barmode="group", legend=dict(orientation="h", y=1.15),
        xaxis=dict(gridcolor=GRID, zeroline=False),
        yaxis=dict(title="평균 지연(h)", gridcolor=GRID, zeroline=False),
        yaxis2=dict(title="절감(tCO₂)", overlaying="y", side="right", showgrid=False))
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
    st.caption("k=5(급함)은 지연 ≈0, k=1(여유)일수록 많이 미뤄 탄소를 아낌 (설계 의도)")

st.divider()

# ── 상세: 비교군 집계표 · 리전 배정 분포 · 다운로드 ──
with st.expander("상세 수치 · 리전 배정 분포 · 결과 CSV"):
    cdf = pd.DataFrame(comparison).T
    cdf.index = [MODES[m] for m in cdf.index]
    st.dataframe(
        cdf[["n_jobs", "total_carbon", "avg_delay", "slo_violation_rate"]].style.format({
            "n_jobs": "{:,.0f}", "total_carbon": "{:,.0f}",
            "avg_delay": "{:.3f}", "slo_violation_rate": "{:.4f}"}), width="stretch")

    counts = pd.Series([r["region"] for r in shifted]).value_counts()
    reg_fig = go.Figure(go.Bar(
        x=[f"{r}" for r in counts.index], y=counts.values, marker_color=CARBON_BLUE,
        hovertemplate="%{x}: %{y:,} job<extra></extra>"))
    reg_fig.update_layout(**PLOT_LAYOUT, height=260, yaxis_title="배정 job 수")
    _style_axes(reg_fig)
    st.plotly_chart(reg_fig, width="stretch", config={"displayModeBar": False})

    detail_df = pd.DataFrame(shifted)
    st.download_button(
        "결과 CSV 다운로드", detail_df.to_csv(index=False).encode("utf-8"),
        file_name="scheduler_validation_2025.csv", mime="text/csv")
