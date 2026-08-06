"""신규 메인 화면 (작성 중).

날짜/시간 선택 로직은 interface/views/final.py의 사이드바 로직(BASE_TIME 기준
WINDOW_START~WINDOW_END 구간, session_state 기반 day/hour)을 그대로 가져와
상단에 바로 조작 가능한 위젯으로 배치한다.

_date_col / _time_col / _play_col: app.py가 화면 전환 드롭다운과 한 줄에 놓으려고
미리 만들어 건네주는 칸(placeholder column)이다. app.py를 거치지 않고 이 파일
단독 실행 시에는 전달되지 않으므로, 없으면 이 파일이 직접 칸을 만든다.
(재생/정지 버튼의 라벨을 안 바꾸는 게 중요 — 아래 주석 참고)
"""

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PLAY_INTERVAL_SEC = 1.0
LB_BASELINE_COLOR = "#898781"
LB_ACCENT_COLOR = "#2a78d6"
LB_DIFF_AXIS_MAX = 50000  # "CAST 적용 전후 탄소 차이" y축 고정 상한 (실측 최댓값 근처로 설정)
MAP_ROUTE_COLOR = "#2e7d32"

# 화살표(리전 간 job 이동)를 그릴 때 쓰는 대표 좌표 — 지도 색칠(구역)과는 별개.
MAP_REGION_COORD = {
    "US-CAL-CISO": (-113, 41), "US-TEX-ERCO": (-94, 39), "US-NY-NYIS": (-78, 40),
    "FR": (2, 47), "DE": (10, 51), "KR": (127, 37), "IN": (78, 22), "JP": (139, 37),
}

# 태평양/호주/남미/아프리카 대부분을 잘라내고 8개 리전이 있는 띠만 보여준다.
MAP_LON_RANGE = [-130, 145]
MAP_LAT_RANGE = [10, 68]

# 24시간 리전별 탄소 그래프(main_col)와 동일한 8색 팔레트(값만 복제 — 왼쪽 코드는 안 건드림).
MAP_REGION_COLORS = {
    "US-CAL-CISO": "#1565c0", "US-TEX-ERCO": "#6baed6", "US-NY-NYIS": "#c62828",
    "FR": "#f4a6a6", "DE": "#2e7d32", "KR": "#81c784", "IN": "#ef6c00", "JP": "#f9c74f",
}
# 미국을 서부/중부/동부로 크게 3분할 (표준 시간대 기준 근사치).
MAP_US_STATES = {
    "US-CAL-CISO": ["WA", "OR", "CA", "NV", "ID", "MT", "WY", "UT", "CO", "AZ", "NM"],
    "US-TEX-ERCO": ["AL", "AR", "IL", "IA", "KS", "LA", "MN", "MS", "MO", "NE", "ND",
                    "OK", "SD", "TX", "WI", "TN"],
    "US-NY-NYIS": ["CT", "DE", "FL", "GA", "IN", "KY", "ME", "MD", "MA", "MI", "NH",
                   "NJ", "NY", "NC", "OH", "PA", "RI", "SC", "VT", "VA", "WV"],
}

# 표/타임라인용 job 데이터 소스 (final.py와 동일).
MAP_LOOKBACK_H = 31  # 현재 실행 중일 수 있는 job을 찾기 위한 뒤돌아보기(최대 L_max+duration=30, +1 여유)
MAP_TASK_TYPE = {
    5: "결제 · API 응답", 4: "사용자 요청·조회", 3: "알림 · 상태 갱신",
    2: "배치 집계·리포트", 1: "로그 · 모델 학습",
}
MAP_WAIT_COLOR = "#c9c9c9"
MAP_SHIFT_COLOR = "#2e7d32"
MAP_SUBMIT_COLOR = "#e08600"

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

MAP_JOBS_CSV = os.path.join(_REPO_ROOT, "load_balancer", "01_데이터", "jobs.csv")
MAP_ASSIGN_CSV = os.path.join(_REPO_ROOT, "load_balancer", "02_프레임워크",
                              "results", "assign_alpha_auto.csv")

from interface import carbon_forecast_api as api  # noqa: E402
from interface import carbon_history  # noqa: E402
from interface.regions import REGIONS, REGION_LABELS, to_iso3  # noqa: E402
from scheduler.scheduler import _mean_carbon, compute_time_shift  # noqa: E402


def _discrete_colorscale(colors):
    """색 목록 -> plotly discrete colorscale (구간마다 색이 뚝뚝 끊기게)."""
    n = len(colors)
    scale = []
    for i, c in enumerate(colors):
        scale.append([i / n, c])
        scale.append([(i + 1) / n, c])
    return scale


@st.cache_resource(show_spinner=False)
def _load_baseline_region_lookup():
    """job_name -> 로드밸런서 baseline(carbon-aware 적용 전) 배정 리전(표준 코드).
    '적용 전' 시나리오(같은 job을 그 리전에서 즉시 실행했다면) 계산용."""
    import config as lb_config  # load_balancer/02_프레임워크/config.py
    from interface.regions import LB_TO_REGION

    df = pd.read_csv(lb_config.RESULTS_DIR / "assign_baseline.csv")
    df = df[~df.dropped]
    return dict(zip(df.job_name, df.assigned.map(LB_TO_REGION)))


def _map_fmt(h):
    return (BASE_TIME + pd.Timedelta(hours=float(h))).strftime("%Y-%m-%d %H:%M")


@st.cache_resource(show_spinner=False)
def _load_map_jobs():
    """표/타임라인용 job 목록 (final.py의 load_jobs()와 동일 소스/방식)."""
    from scheduler import data_loader
    jobs = data_loader.load_jobs_with_assignment(MAP_JOBS_CSV, MAP_ASSIGN_CSV)
    jobs.sort(key=lambda j: j["submit_time"])
    submit_h = np.array([j["submit_time"] for j in jobs])
    return jobs, submit_h


@st.cache_resource(show_spinner=False)
def _load_map_actual():
    """탄소 회계(즉시 vs time-shift)용 실측 탄소강도 시계열."""
    total = int((WINDOW_END - BASE_TIME).total_seconds() // 3600) + 48
    return carbon_history.load_actual_series(total)


@st.cache_data(show_spinner=False)
def _map_forecast_hour(h):
    """시각 h(정수)에 본 향후 24시간 LSTM 예측 (시각별로 캐시)."""
    return api.get_forecast(t_hour=int(h), horizon=24)


def _map_decide(job, actual):
    """job 하나의 time-shift 결정(스케줄러) + 즉시/실제 배출량(탄소 회계)."""
    origin = job["region"]
    region = job.get("carbon_region") or origin  # 로드밸런서가 정한 도착지
    fw = _map_forecast_hour(int(job["submit_time"]))
    start = compute_time_shift(dict(job, region=region), fw, job["submit_time"])
    dur = job["duration"]
    arr = actual[region]
    imm_c = _mean_carbon(arr, job["submit_time"], dur, len(arr)) * dur
    shift_c = _mean_carbon(arr, start, dur, len(arr)) * dur
    return {
        "job_id": job["id"], "k": job["k"], "origin": origin, "region": region,
        "submit_time": job["submit_time"], "duration": dur,
        "scheduled_start": start, "finish": start + dur,
        "imm_c": imm_c, "shift_c": shift_c, "saved": imm_c - shift_c,
    }


def _map_running_at(jobs, submit_h, actual, t_now):
    """t_now에 실행 중인 job들의 결정 목록."""
    lo = np.searchsorted(submit_h, t_now - MAP_LOOKBACK_H)
    hi = np.searchsorted(submit_h, t_now + 1e-6)
    out = []
    for job in jobs[lo:hi]:
        d = _map_decide(job, actual)
        if d["scheduled_start"] <= t_now < d["finish"]:
            out.append(d)
    return out


# 표의 '누적 절감량' 진행바 기준 고정 상한. 전체 job(14만여 개)을 훑어서 실제
# 최댓값을 구하면 몇 분씩 걸리고, 표본을 뽑아도 수~수십 초가 걸려서 그냥 고정값으로
# 잡았다 — 이보다 큰 절감량은 막대가 꽉 찬 채로 표시된다.
MAP_SAVED_BAR_MAX = 600


def _draw_timeline(running, t_now, day_start, height=280):
    """final.py의 draw_timeline()과 동일 — job별 요청·대기·실행(time-shift) 타임라인."""
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
                    line=dict(color=MAP_WAIT_COLOR, width=3, dash="dot"),
                    showlegend=False, hoverinfo="skip"))
        e0, e1 = max(start, 0), min(fin, 24)
        if e1 > e0:
            fig.add_trace(go.Scatter(x=[e0, e1], y=[jid, jid], mode="lines",
                line=dict(color=MAP_SHIFT_COLOR, width=9), showlegend=False,
                hoverinfo="text",
                hovertext=f"{jid}<br>요청 {_map_fmt(d['submit_time'])}"
                          f"<br>실행 {_map_fmt(d['scheduled_start'])}"))
        if 0 <= sub <= 24:
            fig.add_trace(go.Scatter(x=[sub], y=[jid], mode="markers",
                marker=dict(color=MAP_SUBMIT_COLOR, size=9, symbol="diamond"),
                showlegend=False, hoverinfo="text",
                hovertext=f"요청 {_map_fmt(d['submit_time'])}"))
    fig.add_vline(x=t_now - day_start, line=dict(color="#d33", width=1.5, dash="dash"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=8, b=0),
                      yaxis=dict(autorange="reversed", title=None), plot_bgcolor="white")
    fig.update_xaxes(range=[0, 24], tickmode="array", tickvals=list(range(0, 25)),
                     ticktext=[f"{h}" for h in range(25)],
                     title="시각 (시, UTC)", gridcolor="#eee")
    return fig


def _map_arc(lon0, lat0, lon1, lat1, n=48, bump=0.1):
    """final.py와 동일한 방식의 완만한 호(arc) 좌표 (부드러운 곡선을 위해 점 수를 늘림)."""
    t = np.linspace(0, 1, n)
    ease = np.sin(np.pi * t) ** 1.4  # 양 끝을 더 완만하게, 가운데만 살짝 부풀린 곡선
    lon = lon0 + (lon1 - lon0) * t
    lat = lat0 + (lat1 - lat0) * t + ease * abs(lon1 - lon0) * bump
    return lon, lat


def _draw_map(routes=None, region_counts=None, height=560):
    """8개 리전을 색칠한 세계지도 (미국은 주 단위 3분할, 나머지는 국가 단위)
    + routes={(출발region, 배정region): 건수}가 있으면 이동 화살표를,
    + region_counts={region: 실행 중 job 수}가 있으면 리전 위에 숫자를 함께 그린다."""
    fig = go.Figure()

    us_regions = list(MAP_US_STATES)
    us_locations, us_z, us_text = [], [], []
    for i, r in enumerate(us_regions):
        for state in MAP_US_STATES[r]:
            us_locations.append(state)
            us_z.append(i + 0.5)
            us_text.append(REGION_LABELS.get(r, r))
    fig.add_trace(go.Choropleth(
        locations=us_locations, z=us_z, locationmode="USA-states",
        colorscale=_discrete_colorscale([MAP_REGION_COLORS[r] for r in us_regions]),
        zmin=0, zmax=len(us_regions), showscale=False,
        marker_line_color="white", marker_line_width=0.5,
        text=us_text, hoverinfo="text"))

    other_regions = [r for r in REGIONS if r not in MAP_US_STATES]
    fig.add_trace(go.Choropleth(
        locations=[to_iso3(r) for r in other_regions],
        z=[i + 0.5 for i in range(len(other_regions))],
        locationmode="ISO-3",
        colorscale=_discrete_colorscale([MAP_REGION_COLORS[r] for r in other_regions]),
        zmin=0, zmax=len(other_regions), showscale=False,
        marker_line_color="white", marker_line_width=0.5,
        text=[REGION_LABELS.get(r, r) for r in other_regions], hoverinfo="text"))

    if routes:
        wmax = max(routes.values())
        _dest_vec = {}  # dest region -> [가중 평균 진입 방향(lon, lat) 누적]
        for (o, a), n in routes.items():
            if o not in MAP_REGION_COORD or a not in MAP_REGION_COORD:
                continue
            lon, lat = _map_arc(*MAP_REGION_COORD[o], *MAP_REGION_COORD[a])
            fig.add_trace(go.Scattergeo(
                lon=lon, lat=lat, mode="lines",
                line=dict(width=0.8 + 1.6 * (n / wmax), color=MAP_ROUTE_COLOR),
                opacity=0.45,
                hovertext=f"{REGION_LABELS.get(o, o)} → {REGION_LABELS.get(a, a)} : {n}개",
                hoverinfo="text", showlegend=False))

            dlon, dlat = lon[-1] - lon[-3], lat[-1] - lat[-3]
            norm = float(np.hypot(dlon, dlat)) or 1.0
            v = _dest_vec.setdefault(a, [0.0, 0.0])
            v[0] += n * dlon / norm
            v[1] += n * dlat / norm

        # 목적지 하나당 화살촉 하나만: 들어오는 선들의 가중 평균 방향으로 표시.
        _tip_lon, _tip_lat, _tip_angle = [], [], []
        for a, (vlon, vlat) in _dest_vec.items():
            mag = float(np.hypot(vlon, vlat))
            if mag < 1e-6:
                continue
            vlon, vlat = vlon / mag, vlat / mag
            lon0, lat0 = MAP_REGION_COORD[a]
            _tip_lon.append(lon0 - vlon * 4.5)
            _tip_lat.append(lat0 - vlat * 4.5)
            _tip_angle.append(float(np.degrees(np.arctan2(vlon, vlat)) % 360))
        if _tip_lon:
            fig.add_trace(go.Scattergeo(
                lon=_tip_lon, lat=_tip_lat, mode="markers",
                marker=dict(symbol="triangle-up", size=9, color=MAP_ROUTE_COLOR,
                            angle=_tip_angle, angleref="up",
                            line=dict(width=0)),
                opacity=0.85, hoverinfo="skip", showlegend=False))

    if region_counts:
        pts = [(MAP_REGION_COORD[r][0], MAP_REGION_COORD[r][1], region_counts[r])
               for r in region_counts if r in MAP_REGION_COORD and region_counts[r] > 0]
        if pts:
            fig.add_trace(go.Scattergeo(
                lon=[p[0] for p in pts], lat=[p[1] for p in pts],
                mode="markers+text",
                marker=dict(size=20, color="rgba(20,20,20,0.65)",
                            line=dict(color="white", width=1)),
                text=[str(p[2]) for p in pts], textposition="middle center",
                textfont=dict(size=12, color="white", family="Arial Black"),
                hoverinfo="skip", showlegend=False))

    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), dragmode=False,
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False, showcoastlines=True,
                 coastlinecolor="#d0d0d0", showland=True, landcolor="#f5f5f5",
                 showocean=True, oceancolor="#eaf2f8", projection_type="natural earth",
                 lonaxis=dict(range=MAP_LON_RANGE), lataxis=dict(range=MAP_LAT_RANGE)))
    return fig

# final.py와 동일한 LSTM 라이브 유효 구간
BASE_TIME = pd.Timestamp("2026-01-01 00:00:00")
WINDOW_START = pd.Timestamp("2026-01-08 00:00:00")
WINDOW_END = pd.Timestamp("2026-07-19 23:00:00")
MAX_T = int((WINDOW_END - BASE_TIME).total_seconds() // 3600)

st.session_state.setdefault("main_day", WINDOW_START.date())
st.session_state.setdefault("main_hour", 12)
st.session_state.setdefault("main_play", False)

# 재생 버튼이 st.rerun()을 부르면, 그 재실행 직후(우리 코드가 시작되기도 전에)
# Streamlit이 number_input/date_input 값을 마운트 시점 기본값으로 되돌려버리는
# 문제가 있다 — 정지 버튼은 rerun을 안 불러서 안 겪지만 재생은 run_every를 바로
# 적용하려면 rerun이 필요해서 겪는다. 그래서 클릭 직전 값을 저장해뒀다가,
# 스크립트 맨 위(위젯 그리기 전)에서 강제로 복원한다.
if "_main_restore" in st.session_state:
    st.session_state["main_day"], st.session_state["main_hour"] = \
        st.session_state.pop("_main_restore")

date_col = globals().get("_date_col")
time_col = globals().get("_time_col")
play_col = globals().get("_play_col")
if date_col is None or time_col is None or play_col is None:
    _, date_col, time_col, play_col = st.columns([6, 1, 1, 1])

# 재생/정지를 final.py처럼 "라벨이 안 바뀌는 버튼 두 개"로 분리했다 — 버튼 하나를
# 라벨만 바꿔가며 재사용하면(토글 버튼) 같은 화면의 다른 위젯(number_input 등)
# 값이 재생/정지 클릭 순간 엉뚱한 기본값으로 되돌아가는 문제가 있었는데, final.py처럼
# 라벨이 고정된 버튼 두 개로 바꾸니 그 문제가 재현되지 않았다.
# 정지 버튼은 st.rerun()을 안 부르는 것도 중요하다 — "1시간 전진" 로직이 이미
# 이 코드보다 아래에 있어서, 그냥 다음 줄로 넘어가는 것만으로 정지가 즉시 반영된다.
with play_col:
    _pcol, _scol = st.columns(2)
    if _pcol.button("▶", key="main_play_btn", width="stretch"):
        st.session_state["_main_restore"] = (st.session_state["main_day"],
                                              st.session_state["main_hour"])
        st.session_state["main_play"] = True
        st.rerun()
    if _scol.button("■", key="main_stop_btn", width="stretch"):
        st.session_state["main_play"] = False

# 대시보드 본문 전체를 프래그먼트로 묶어서, 재생 중 자동 갱신이 앱 전체가 아니라
# 이 부분만 다시 그리게 한다 (전체 페이지 rerun이 만들던 깜빡임/순간 사라짐 방지).
# main_play가 켜져 있을 때만 run_every로 주기적으로 재실행되고, 꺼지면 멈춘다.
@st.fragment(run_every=PLAY_INTERVAL_SEC if st.session_state["main_play"] else None)
def _render_dashboard():
    # 자동 재생: 위젯 생성 전에 1시간 전진 (final.py의 fin_play 로직과 동일)
    if st.session_state["main_play"]:
        _cur_t = int((pd.Timestamp(st.session_state["main_day"]) - BASE_TIME).total_seconds()
                     // 3600) + int(st.session_state["main_hour"])
        _next_t = _cur_t + 1
        _hit_end = _next_t >= MAX_T
        if _hit_end:
            _next_t, st.session_state["main_play"] = MAX_T, False
        st.session_state["main_day"] = (BASE_TIME + pd.Timedelta(hours=_next_t)).date()
        st.session_state["main_hour"] = int(_next_t % 24)
        if _hit_end:
            # 재생이 끝에 도달해 자동으로 멈췄다는 걸 (프래그먼트 밖에 있는)
            # 재생/정지 버튼에도 반영하려면 앱 전체를 다시 실행해야 한다.
            st.rerun()

    with date_col:
        st.date_input("날짜 (UTC)", min_value=WINDOW_START.date(),
                        max_value=WINDOW_END.date(), key="main_day",
                        label_visibility="collapsed")
    with time_col:
        st.number_input("시각 (시, UTC)", 0, 23, key="main_hour",
                        label_visibility="collapsed")

    picked_day = st.session_state["main_day"]
    picked_hour = st.session_state["main_hour"]
    t_now = int((pd.Timestamp(picked_day) - BASE_TIME).total_seconds() // 3600) + int(picked_hour)

    # main_col(전/후 그래프)과 _spacer_col(지도/표/타임라인) 양쪽에서 다 쓰므로
    # 여기서 한 번만 계산한다 (안 그러면 무거운 스케줄러 계산이 두 번 돈다).
    _map_jobs, _map_submit_h = _load_map_jobs()
    _map_actual = _load_map_actual()
    _running = _map_running_at(_map_jobs, _map_submit_h, _map_actual, t_now)
    _saved_now = sum(d["saved"] for d in _running)

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] { gap: 0.1rem; }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] .cast-brand)
            > div[data-testid="stColumn"]:first-child {
            border-right: 2px solid #ccc;
            padding-right: 1.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    main_col, _spacer_col = st.columns([1, 3])

    with main_col:
        st.markdown(
            """
            <div class="cast-brand" style="display:flex; align-items:baseline; gap:0.9rem; margin:-0.8rem 0 1.2rem;">
              <span style="font-size:3.6rem; font-weight:800; letter-spacing:-0.02em; line-height:1;">CAST</span>
              <span style="font-size:0.95rem; color:#888;">Carbon-Aware Spatio-Temporal Scheduler</span>
            </div>
            <div style="height:1.5rem;"></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**24시간동안 리전별 탄소 그래프 (LSTM 예측값)**")
        forecast = api.get_forecast(t_hour=t_now, horizon=24)
        fdf = pd.DataFrame(forecast)
        fdf = fdf[[r for r in REGIONS if r in fdf.columns]]

        _palette = ["#1565c0", "#6baed6", "#c62828", "#f4a6a6", "#2e7d32",
                    "#81c784", "#ef6c00", "#f9c74f"]
        fig = go.Figure()
        for i, col in enumerate(fdf.columns):
            fig.add_trace(go.Scatter(
                x=list(range(len(fdf))), y=fdf[col], mode="lines", name=col,
                line=dict(width=2, color=_palette[i % len(_palette)]),
                hovertemplate=f"{col}<br>" + "+%{x}h: %{y:.0f} gCO₂/kWh<extra></extra>"))
        fig.update_layout(
            height=380, margin=dict(l=0, r=0, t=8, b=120), plot_bgcolor="white",
            legend=dict(orientation="h", x=0, y=-0.35, yanchor="top"),
        )
        fig.update_xaxes(title=dict(text="t 시간 후 (h)", standoff=10), gridcolor="#eee", dtick=2)
        fig.update_yaxes(title="gCO₂/kWh", gridcolor="#eee")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False},
                        key="forecast_chart")

        st.markdown("<div style='height:3rem;'></div>", unsafe_allow_html=True)

        st.markdown("**CAST 적용 전후 탄소 차이 그래프**")
        # 오른쪽과 동일하게 "지금 실행 중인" job(_running) 기준 — baseline(적용 전)
        # 리전에서 그 즉시 실행했다면 vs 실제로(carbon-aware 리전 + time-shift) 낸
        # 탄소를 같은 job들로 비교한다. baseline에서 드롭된 job은 양쪽 다 제외.
        _baseline_region = _load_baseline_region_lookup()
        _before_total = 0.0
        _after_total = 0.0
        for d in _running:
            _bregion = _baseline_region.get(d["job_id"])
            if _bregion is None:
                continue
            _arr = _map_actual[_bregion]
            _dur = d["duration"]
            _before_total += _mean_carbon(_arr, d["submit_time"], _dur, len(_arr)) * _dur
            _after_total += d["shift_c"]

        lb_fig = go.Figure()
        lb_fig.add_trace(go.Bar(
            x=["CAST 적용 전", "CAST 적용 후"], y=[_before_total, _after_total],
            marker_color=[LB_BASELINE_COLOR, LB_ACCENT_COLOR], width=0.35,
            hovertemplate="%{x}<br>%{y:.0f} gCO₂<extra></extra>"))
        lb_fig.update_layout(
            height=340, margin=dict(l=0, r=0, t=8, b=40), plot_bgcolor="white",
            showlegend=False,
        )
        lb_fig.update_xaxes(gridcolor="#eee")
        lb_fig.update_yaxes(title="총 탄소 배출량 (gCO₂)", gridcolor="#eee",
                            range=[0, LB_DIFF_AXIS_MAX])
        st.plotly_chart(lb_fig, width="stretch", config={"displayModeBar": False},
                        key="lb_diff_chart")
        st.caption(f"{_map_fmt(t_now)} UTC에 실행 중인 job 기준 — baseline 리전·즉시실행 vs "
                   "실제(carbon-aware 리전·time-shift) 탄소 비교")

    with _spacer_col:
        st.markdown(
            """
            <style>
            .st-key-map-chart div[data-testid="stPlotlyChart"] {
                border-radius: 32px !important; overflow: hidden !important;
            }
            .st-key-map-chart div[data-testid="stPlotlyChart"] > div {
                border-radius: 32px; overflow: hidden;
            }
            .st-key-map-chart {
                display: flex; align-items: center;
            }
            </style>
            <div style="height:2.6rem;"></div>
            """,
            unsafe_allow_html=True,
        )

        _region_counts = {}
        for d in _running:
            _region_counts[d["region"]] = _region_counts.get(d["region"], 0) + 1

        # 화살표는 "지금 실행 중인" job(_running, region_counts와 동일 기준)의 출발→도착만
        # 표시 — job이 뜨고 지면 화살표도 같이 뜨고 진다.
        _routes = {}
        for d in _running:
            o, a = d["origin"], d["region"]
            if o != a:
                _routes[(o, a)] = _routes.get((o, a), 0) + 1
        with st.container(key="map-chart"):
            st.plotly_chart(_draw_map(routes=_routes, region_counts=_region_counts, height=300),
                            width=1150, config={"displayModeBar": False}, key="map_chart_plot")

        st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

        k1, k2, k3 = st.columns(3)
        k1.metric("현재 시각(UTC)", _map_fmt(t_now))
        k2.metric("실행 중인 작업", f"{len(_running)}개")
        k3.metric("이 시점 절감", f"{_saved_now:,.0f} gCO₂")

        _SAVE_COL = "누적 절감량"
        _rows = [{
            "job_id": d["job_id"],
            "task_type": MAP_TASK_TYPE.get(d["k"], f"k={d['k']}"),
            "출발지": REGION_LABELS.get(d["origin"], d["origin"]),
            "도착지": REGION_LABELS.get(d["region"], d["region"]),
            "요청시각": _map_fmt(d["submit_time"])[5:],
            "실행시각": _map_fmt(d["scheduled_start"])[5:],
            _SAVE_COL: round(d["saved"], 0),
        } for d in sorted(_running, key=lambda x: x["saved"], reverse=True)]
        _tbl = pd.DataFrame(_rows, columns=["job_id", "task_type", "출발지", "도착지",
                                            "요청시각", "실행시각", _SAVE_COL])
        if _tbl.empty:
            _blank = pd.DataFrame([{c: "" for c in _tbl.columns}] * 5, columns=_tbl.columns)
            st.dataframe(_blank, width="stretch", height=213, hide_index=True, key="job_table")
        else:
            st.dataframe(_tbl, width="stretch", height=213, hide_index=True, key="job_table",
                        column_config={
                            _SAVE_COL: st.column_config.ProgressColumn(
                                _SAVE_COL, format="%.0f", min_value=0,
                                max_value=MAP_SAVED_BAR_MAX, color="#8bc34a")})

        st.caption("요청◆ · · 대기 ── 실행 · 빨강=현재 (그 날 0~24시 UTC)")
        st.plotly_chart(_draw_timeline(_running, t_now, t_now - picked_hour, height=280),
                        width="stretch", config={"displayModeBar": False}, key="timeline_chart")


_render_dashboard()
