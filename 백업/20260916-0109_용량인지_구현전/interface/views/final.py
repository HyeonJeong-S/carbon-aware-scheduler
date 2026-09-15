"""최종 통합 화면 — LSTM 라이브 연결 데모 (2026-01-08 ~ 2026-07-19).

LSTM 담당자가 학습·설계한 유효 구간(2026-01-08 ~ 2026-07-19)에서,
실제 LSTM 예측으로 스케줄러의 time-shift를 라이브로 돌려 보여준다.

  · 세계지도  : 그 시점에 job이 실행 중인 나라 + 로드밸런서 이동(origin→assigned) 화살표
  · job 표    : 지금 실행 중인 job의 요청/실행 시각과 즉시실행 대비 절감
  · 타임라인  : 요청 → 대기 → 실행(time-shift) 을 job별로

성능: 146,000개(1년) 전체를 라이브 LSTM으로 돌리면 매우 느리므로,
     고른 시점 주변 '창(window)'의 job만 그때그때 계산한다(시각별 예측은 캐시).
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PLAY_INTERVAL_SEC = 1.0

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_REPO_ROOT, os.path.join(_REPO_ROOT, "scheduler")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from interface import carbon_forecast_api, carbon_history
from interface.regions import REGION_LABELS, to_iso3
from scheduler.scheduler import _mean_carbon, compute_time_shift

# LSTM 라이브 유효 구간 (담당자 설계 기준)
BASE_TIME = pd.Timestamp("2026-01-01 00:00:00")   # t=0 (carbon_intensity_demo.csv 기준)
WINDOW_START = pd.Timestamp("2026-01-08 00:00:00")  # 168h 워밍업 이후
WINDOW_END = pd.Timestamp("2026-07-19 23:00:00")
LOOKBACK_H = 30   # 현재 실행 중일 수 있는 job을 찾기 위한 뒤돌아보기(최대 L_max+duration)

JOBS_CSV = os.path.join(_REPO_ROOT, "load_balancer", "01_데이터", "jobs.csv")
ASSIGN_CSV = os.path.join(_REPO_ROOT, "load_balancer", "02_프레임워크",
                          "results", "assign_alpha_auto.csv")

REGION_COORD = {
    "US-CAL-CISO": (-120, 37), "US-TEX-ERCO": (-99, 31), "US-NY-NYIS": (-74, 41),
    "FR": (2, 47), "DE": (10, 51), "KR": (127, 37), "IN": (78, 22), "JP": (139, 37),
}
COUNTRY_COORD = {"USA": (-98, 39), "FRA": (2, 47), "DEU": (10, 51),
                 "KOR": (128, 36), "IND": (79, 22), "JPN": (138, 37)}
ROUTE_COLOR = "#2e7d32"
SHIFT_COLOR = "#2e7d32"
WAIT_COLOR = "#c9c9c9"
SUBMIT_COLOR = "#e08600"


# ─────────────────────── 데이터 (캐시) ───────────────────────
@st.cache_resource(show_spinner=False)
def load_jobs():
    """146k job + 로드밸런서 배정. submit_h 오름차순 + numpy 인덱스."""
    from scheduler import data_loader
    jobs = data_loader.load_jobs_with_assignment(JOBS_CSV, ASSIGN_CSV)
    jobs.sort(key=lambda j: j["submit_time"])
    submit_h = np.array([j["submit_time"] for j in jobs])
    return jobs, submit_h


@st.cache_resource(show_spinner=False)
def load_actual():
    """2026 실측 탄소강도 (탄소 회계용). {region: [시간별 값]}."""
    total = int((WINDOW_END - BASE_TIME).total_seconds() // 3600) + 48
    return carbon_history.load_actual_series(total)


@st.cache_data(show_spinner=False)
def forecast_hour(h):
    """시각 h(정수)에 본 향후 24시간 LSTM 예측. 시각별로 캐시된다."""
    return carbon_forecast_api.get_forecast(t_hour=int(h), horizon=24)


def decide(job, actual):
    """job 하나의 time-shift 결정 + 즉시/실제 배출량 계산."""
    region = job.get("carbon_region") or job["region"]
    fw = forecast_hour(int(job["submit_time"]))
    j2 = dict(job, region=region)
    start = compute_time_shift(j2, fw, job["submit_time"])
    dur = job["duration"]
    arr = actual[region]
    imm_c = _mean_carbon(arr, job["submit_time"], dur, len(arr)) * dur
    shift_c = _mean_carbon(arr, start, dur, len(arr)) * dur
    return {
        "job_id": job["id"], "k": job["k"], "region": region,
        "submit_time": job["submit_time"], "duration": dur,
        "scheduled_start": start, "finish": start + dur,
        "imm_c": imm_c, "shift_c": shift_c, "saved": imm_c - shift_c,
    }


def running_at(jobs, submit_h, actual, t_now):
    """t_now 에 실행 중인 job들의 결정 목록."""
    lo = np.searchsorted(submit_h, t_now - LOOKBACK_H)
    hi = np.searchsorted(submit_h, t_now + 1e-6)
    out = []
    for job in jobs[lo:hi]:
        d = decide(job, actual)
        if d["scheduled_start"] <= t_now < d["finish"]:
            out.append(d)
    return out


# ─────────────────────── 그리기 ───────────────────────
def fmt(h):
    return (BASE_TIME + pd.Timedelta(hours=float(h))).strftime("%Y-%m-%d %H:%M")


def _arc(lon0, lat0, lon1, lat1, n=24, bump=0.18):
    t = np.linspace(0, 1, n)
    lon = lon0 + (lon1 - lon0) * t
    lat = lat0 + (lat1 - lat0) * t + np.sin(np.pi * t) * abs(lon1 - lon0) * bump
    return lon, lat


def draw_map(running, height=560):
    fig = go.Figure()
    # 도착 나라 강조
    iso = {}
    for d in running:
        c = to_iso3(d["region"])
        iso[c] = iso.get(c, 0) + 1
    if iso:
        fig.add_trace(go.Choropleth(
            locations=list(iso), locationmode="ISO-3", z=list(iso.values()),
            colorscale=[[0, "#e8f5e9"], [1, "#2e7d32"]], showscale=False,
            marker_line_color="white", marker_line_width=0.5,
            hovertext=[f"{k}: {v} job 실행 중" for k, v in iso.items()], hoverinfo="text"))
    # 이동 화살표 (origin 리전 → assigned 리전), 경로별 집계
    routes = {}
    for d in running:
        job = _JOB_BY_ID.get(d["job_id"])
        o = job["region"] if job else d["region"]
        a = d["region"]
        if o != a:
            routes[(o, a)] = routes.get((o, a), 0) + 1
    wmax = max(routes.values()) if routes else 1
    for (o, a), n in routes.items():
        if o not in REGION_COORD or a not in REGION_COORD:
            continue
        lon, lat = _arc(*REGION_COORD[o], *REGION_COORD[a])
        fig.add_trace(go.Scattergeo(
            lon=lon, lat=lat, mode="lines",
            line=dict(width=1 + 5 * (n / wmax), color=ROUTE_COLOR), opacity=0.6,
            hovertext=f"{REGION_LABELS.get(o, o)} → {REGION_LABELS.get(a, a)} : {n}",
            hoverinfo="text", showlegend=False))
    # 나라 위 실행 job 수
    if iso:
        pts = [(COUNTRY_COORD[c][0], COUNTRY_COORD[c][1], iso[c]) for c in iso if c in COUNTRY_COORD]
        fig.add_trace(go.Scattergeo(
            lon=[p[0] for p in pts], lat=[p[1] for p in pts],
            text=[str(p[2]) for p in pts], mode="text",
            textfont=dict(size=18, color="white", family="Arial Black"),
            hoverinfo="skip", showlegend=False))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), dragmode=False,
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False, showcoastlines=True,
                 coastlinecolor="#d0d0d0", showland=True, landcolor="#f5f5f5",
                 showocean=True, oceancolor="#eaf2f8", projection_type="natural earth"))
    return fig


def draw_timeline(running, t_now, day_start, height=300):
    js = sorted(running, key=lambda d: d["scheduled_start"])[:15]
    fig = go.Figure()
    for d in js:
        jid = d["job_id"]
        sub = d["submit_time"] - day_start
        start = d["scheduled_start"] - day_start
        fin = d["finish"] - day_start
        if start > sub + 1e-9:
            a0, a1 = max(sub, 0), min(start, 24)
            if a1 > a0:
                fig.add_trace(go.Scatter(x=[a0, a1], y=[jid, jid], mode="lines",
                    line=dict(color=WAIT_COLOR, width=3, dash="dot"),
                    showlegend=False, hoverinfo="skip"))
        e0, e1 = max(start, 0), min(fin, 24)
        if e1 > e0:
            fig.add_trace(go.Scatter(x=[e0, e1], y=[jid, jid], mode="lines",
                line=dict(color=SHIFT_COLOR, width=9), showlegend=False,
                hoverinfo="text",
                hovertext=f"{jid}<br>요청 {fmt(d['submit_time'])}<br>실행 {fmt(d['scheduled_start'])}"))
        if 0 <= sub <= 24:
            fig.add_trace(go.Scatter(x=[sub], y=[jid], mode="markers",
                marker=dict(color=SUBMIT_COLOR, size=9, symbol="diamond"),
                showlegend=False, hoverinfo="text", hovertext=f"요청 {fmt(d['submit_time'])}"))
    fig.add_vline(x=t_now - day_start, line=dict(color="#d33", width=1.5, dash="dash"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=8, b=0),
                      yaxis=dict(autorange="reversed", title=None), plot_bgcolor="white")
    fig.update_xaxes(range=[0, 24], tickmode="array", tickvals=list(range(0, 25)),
                     ticktext=[f"{h}" for h in range(25)],
                     title="시각 (시, UTC)", gridcolor="#eee")
    return fig


def draw_region_bar(running, height=220):
    """지금 실행 중 job을 리전별로 센 미니 막대."""
    cnt = {}
    for d in running:
        r = d["region"]
        cnt[r] = cnt.get(r, 0) + 1
    cnt = dict(sorted(cnt.items(), key=lambda x: -x[1]))
    fig = go.Figure(go.Bar(
        x=[REGION_LABELS.get(r, r) for r in cnt], y=list(cnt.values()),
        marker_color=ROUTE_COLOR, hovertemplate="%{x}: %{y}개<extra></extra>"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=8, b=0),
                      plot_bgcolor="white", showlegend=False,
                      yaxis_title="실행 중 job 수")
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(gridcolor="#eee")
    return fig


def draw_savings_bar(running, height=220):
    """절감 상위 job 미니 막대 (즉시실행 대비)."""
    top = sorted(running, key=lambda d: d["saved"], reverse=True)[:10]
    fig = go.Figure(go.Bar(
        x=[d["saved"] for d in top][::-1], y=[d["job_id"] for d in top][::-1],
        orientation="h", marker_color=SHIFT_COLOR,
        hovertemplate="%{y}: %{x:.0f} gCO₂ 절감<extra></extra>"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=8, b=0),
                      plot_bgcolor="white", showlegend=False,
                      xaxis_title="절감(gCO₂)")
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(gridcolor="#eee")
    return fig


# ─────────────────────── 화면 ───────────────────────
# 메인 컨테이너의 상단·좌우 여백 최소화 + 콘텐츠 최대폭 해제 (표가 넓게 쓰이도록)
st.markdown("""<style>
[data-testid='stMainBlockContainer']{
  padding-top:0.6rem; padding-left:1.2rem; padding-right:1.2rem; max-width:100%;
}
</style>""", unsafe_allow_html=True)

jobs, submit_h = load_jobs()
actual = load_actual()
_JOB_BY_ID = {j["id"]: j for j in jobs}

MAX_T = int((WINDOW_END - BASE_TIME).total_seconds() // 3600)
MIN_T = int((WINDOW_START - BASE_TIME).total_seconds() // 3600)

# 시점 선택 + 자동 재생 (사이드바)
with st.sidebar:
    st.divider()
    st.caption("LSTM 라이브 · 2026-01-08 ~ 2026-07-19 (UTC)")
    st.session_state.setdefault("fin_day", WINDOW_START.date())
    st.session_state.setdefault("fin_hour", 12)
    st.session_state.setdefault("fin_play", False)

    # 자동 재생: 위젯 생성 전에 1시간 전진
    if st.session_state["fin_play"]:
        cur = int((pd.Timestamp(st.session_state["fin_day"]) - BASE_TIME).total_seconds()
                  // 3600) + int(st.session_state["fin_hour"])
        nxt = cur + 1
        if nxt >= MAX_T:
            nxt, st.session_state["fin_play"] = MAX_T, False
        st.session_state["fin_day"] = (BASE_TIME + pd.Timedelta(hours=nxt)).date()
        st.session_state["fin_hour"] = int(nxt % 24)

    st.date_input("날짜 (UTC)", min_value=WINDOW_START.date(),
                  max_value=WINDOW_END.date(), key="fin_day")
    st.number_input("시각 (시, UTC)", 0, 23, key="fin_hour")

    pcol, scol = st.columns(2)
    if pcol.button("▶ 재생", width="stretch"):
        st.session_state["fin_play"] = True
        st.rerun()
    if scol.button("■ 정지", width="stretch"):
        st.session_state["fin_play"] = False
    if st.session_state["fin_play"]:
        st.caption(f"재생 중… {PLAY_INTERVAL_SEC:.0f}초마다 1시간 전진")

picked = st.session_state["fin_day"]
hour = st.session_state["fin_hour"]
t_now = int((pd.Timestamp(picked) - BASE_TIME).total_seconds() // 3600) + int(hour)
day_start = int((pd.Timestamp(picked) - BASE_TIME).total_seconds() // 3600)

with st.spinner("LSTM 예측으로 이 시점 스케줄 계산 중…"):
    running = running_at(jobs, submit_h, actual, t_now)

saved_now = sum(d["saved"] for d in running)

# 1) 지도 — 맨 위
st.plotly_chart(draw_map(running, height=340), width="stretch",
                config={"displayModeBar": False})

# 2) KPI (compact)
k1, k2, k3 = st.columns(3)
k1.metric("현재 시각(UTC)", fmt(t_now))
k2.metric("실행 중 job", f"{len(running)}개")
k3.metric("이 시점 절감", f"{saved_now:,.0f} gCO₂")

# 3) 표 — 전체 폭 (8개 컬럼 다 보이게)
rows = []
for d in sorted(running, key=lambda x: x["saved"], reverse=True):
    rows.append({
        "job_id": d["job_id"], "k": d["k"],
        "지역": REGION_LABELS.get(d["region"], d["region"]),
        "요청": fmt(d["submit_time"])[5:], "실행": fmt(d["scheduled_start"])[5:],
        "즉시(gCO₂)": round(d["imm_c"], 0), "shift(gCO₂)": round(d["shift_c"], 0),
        "절감(gCO₂)": round(d["saved"], 0)})
tbl = pd.DataFrame(rows, columns=["job_id", "k", "지역", "요청", "실행",
                                  "즉시(gCO₂)", "shift(gCO₂)", "절감(gCO₂)"])
bar_max = float(tbl["절감(gCO₂)"].max()) if not tbl.empty and tbl["절감(gCO₂)"].max() > 0 else 1.0
st.dataframe(tbl, width="stretch", height=175, hide_index=True, column_config={
    "절감(gCO₂)": st.column_config.ProgressColumn("절감(gCO₂)", format="%.0f",
                                                min_value=0, max_value=bar_max)})

# 4) 타임라인 — 전체 폭 (그 날 0~24시)
st.caption("요청◆ · · 대기 ── 실행 · 빨강=현재 (그 날 0~24시 UTC)")
st.plotly_chart(draw_timeline(running, t_now, day_start, height=230),
                width="stretch", config={"displayModeBar": False})

# ── 자동 재생 루프 ──
if st.session_state.get("fin_play"):
    time.sleep(PLAY_INTERVAL_SEC)
    st.rerun()
