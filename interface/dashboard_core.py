"""메인 화면(지도/그래프/표/타임라인) 계산 로직 — UI 프레임워크 무관.

interface/dashboard/pages/main.py 가 이 모듈의 함수를 호출해 그림·표를 만든다.
데이터 로딩은 functools.lru_cache 로 프로세스 안에 한 번만 캐시된다.

시간축: 2026 라이브 데모 (t=0 ↔ 2026-01-01 00:00 UTC). LSTM 은 168h 워밍업 이후인
2026-01-08 부터, 날씨 리전의 미래 24h 날씨가 있는 2026-07-19 23:00 까지 실제 모델로 응답한다.
"""

import functools
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

PLAY_INTERVAL_SEC = 1.0
LB_BASELINE_COLOR = "#898781"
LB_ACCENT_COLOR = "#2a78d6"
# "CAST 적용 전후 누적 탄소" y축 고정 상한. 하루치 누적(적용 전)이 대략 7~9만이라
# 10만으로 잡아, 하루가 흐르는 동안 막대가 차오르는 게 보이게 한다.
LB_DIFF_AXIS_MAX = 100000
MAP_ROUTE_COLOR = "#2e7d32"

# 화살표(리전 간 job 이동)를 그릴 때 쓰는 대표 좌표 — 지도 색칠(구역)과는 별개.
MAP_REGION_COORD = {
    "US-CAL-CISO": (-113, 41), "US-TEX-ERCO": (-94, 39), "US-NY-NYIS": (-78, 40),
    "FR": (2, 47), "DE": (10, 51), "KR": (127, 37), "IN": (78, 22), "JP": (139, 37),
}

# 태평양/호주/남미/아프리카 대부분을 잘라내고 8개 리전이 있는 띠만 보여준다.
MAP_LON_RANGE = [-130, 145]
MAP_LAT_RANGE = [10, 68]

# 24시간 리전별 탄소 그래프와 동일한 8색 팔레트.
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

# 표/타임라인용 job 데이터 소스.
MAP_LOOKBACK_H = 31  # 현재 실행 중일 수 있는 job을 찾기 위한 뒤돌아보기(최대 L_max+duration=30, +1 여유)
MAP_TASK_TYPE = {
    5: "결제 · API 응답", 4: "사용자 요청·조회", 3: "알림 · 상태 갱신",
    2: "배치 집계·리포트", 1: "로그 · 모델 학습",
}
MAP_WAIT_COLOR = "#c9c9c9"
MAP_SHIFT_COLOR = "#2e7d32"
MAP_SUBMIT_COLOR = "#e08600"

# 표의 '누적 절감량' 진행바 기준 고정 상한 (전체 job을 다 훑으면 너무 오래 걸려 고정값 사용).
MAP_SAVED_BAR_MAX = 600

# final.py와 동일한 LSTM 라이브 유효 구간
BASE_TIME = pd.Timestamp("2026-01-01 00:00:00")
WINDOW_START = pd.Timestamp("2026-01-08 00:00:00")
WINDOW_END = pd.Timestamp("2026-07-19 23:00:00")
MIN_T = int((WINDOW_START - BASE_TIME).total_seconds() // 3600)
MAX_T = int((WINDOW_END - BASE_TIME).total_seconds() // 3600)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_LB_DIR = os.path.join(_REPO_ROOT, "load_balancer", "02_프레임워크")
_SCHED_DIR = os.path.join(_REPO_ROOT, "scheduler")
_LSTM_DIR = os.path.join(_REPO_ROOT, "carbon-forecast-LSTM")
# app.py와 완전히 동일한 순서로 등록해야 한다 — scheduler 패키지가 이 조합에서만
# (REPO_ROOT 하나만 넣으면 안 되고) 제대로 잡힌다.
for _p in (_SCHED_DIR, _LB_DIR, _LSTM_DIR, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MAP_JOBS_CSV = os.path.join(_REPO_ROOT, "load_balancer", "01_데이터", "jobs.csv")
MAP_ASSIGN_CSV = os.path.join(_REPO_ROOT, "load_balancer", "02_프레임워크",
                              "results", "assign_alpha_auto.csv")

from interface import carbon_forecast_api as api  # noqa: E402
from interface import carbon_history  # noqa: E402
from interface.regions import LB_TO_REGION, REGIONS, REGION_LABELS, to_iso3  # noqa: E402
from scheduler.scheduler import _mean_carbon, compute_time_shift  # noqa: E402


def t_now_of(picked_day, picked_hour):
    return int((pd.Timestamp(picked_day) - BASE_TIME).total_seconds() // 3600) + int(picked_hour)


def map_fmt(h):
    return (BASE_TIME + pd.Timedelta(hours=float(h))).strftime("%Y-%m-%d %H:%M")


def _discrete_colorscale(colors):
    """색 목록 -> plotly discrete colorscale (구간마다 색이 뚝뚝 끊기게)."""
    n = len(colors)
    scale = []
    for i, c in enumerate(colors):
        scale.append([i / n, c])
        scale.append([(i + 1) / n, c])
    return scale


@functools.lru_cache(maxsize=1)
def load_baseline_region_lookup():
    """job_name -> 로드밸런서 baseline(carbon-aware 적용 전) 배정 리전(표준 코드)."""
    import config as lb_config  # load_balancer/02_프레임워크/config.py

    df = pd.read_csv(lb_config.RESULTS_DIR / "assign_baseline.csv")
    df = df[~df.dropped]
    return dict(zip(df.job_name, df.assigned.map(LB_TO_REGION)))


@functools.lru_cache(maxsize=1)
def load_map_jobs():
    """표/타임라인용 job 목록."""
    from scheduler import data_loader
    jobs = data_loader.load_jobs_with_assignment(MAP_JOBS_CSV, MAP_ASSIGN_CSV)
    jobs.sort(key=lambda j: j["submit_time"])
    submit_h = np.array([j["submit_time"] for j in jobs])
    return jobs, submit_h


@functools.lru_cache(maxsize=1)
def load_map_actual():
    """탄소 회계(즉시 vs time-shift)용 실측 탄소강도 시계열."""
    total = int((WINDOW_END - BASE_TIME).total_seconds() // 3600) + 48
    return carbon_history.load_actual_series(total)


@functools.lru_cache(maxsize=None)
def map_forecast_hour(h):
    """시각 h(정수)에 본 향후 24시간 LSTM 예측 (시각별로 캐시)."""
    return api.get_forecast(t_hour=int(h), horizon=24)


def map_decide(job, actual):
    """job 하나의 time-shift 결정(스케줄러) + 즉시/실제 배출량(탄소 회계)."""
    origin = job["region"]
    region = job.get("carbon_region") or origin  # 로드밸런서가 정한 도착지
    fw = map_forecast_hour(int(job["submit_time"]))
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


def map_running_at(jobs, submit_h, actual, t_now):
    """t_now에 실행 중인 job들의 결정 목록."""
    lo = np.searchsorted(submit_h, t_now - MAP_LOOKBACK_H)
    hi = np.searchsorted(submit_h, t_now + 1e-6)
    out = []
    for job in jobs[lo:hi]:
        d = map_decide(job, actual)
        if d["scheduled_start"] <= t_now < d["finish"]:
            out.append(d)
    return out


def before_after_totals(running, actual):
    """CAST 적용 전(baseline 리전·즉시실행) vs 후(실제 shift_c) 탄소 총합."""
    baseline_region = load_baseline_region_lookup()
    before_total = 0.0
    after_total = 0.0
    for d in running:
        bregion = baseline_region.get(d["job_id"])
        if bregion is None:
            continue
        arr = actual[bregion]
        dur = d["duration"]
        before_total += _mean_carbon(arr, d["submit_time"], dur, len(arr)) * dur
        after_total += d["shift_c"]
    return before_total, after_total


@functools.lru_cache(maxsize=None)
def _hour_bucket_totals(hour):
    """제출시각이 [hour, hour+1)인 job들의 CAST 적용 전/후 배출량 합.

    누적 그래프는 시각이 1시간 흐를 때마다 이 버킷 하나만 더하면 되므로,
    시간대별로 캐시해두면 재생 중에도 매번 하루치를 다시 훑지 않는다.
    """
    jobs, submit_h = load_map_jobs()
    actual = load_map_actual()
    baseline_region = load_baseline_region_lookup()

    lo = np.searchsorted(submit_h, hour)
    hi = np.searchsorted(submit_h, hour + 1)
    before = after = 0.0
    for job in jobs[lo:hi]:
        bregion = baseline_region.get(job["id"])
        if bregion is None:
            continue
        d = map_decide(job, actual)
        arr = actual[bregion]
        dur = d["duration"]
        before += _mean_carbon(arr, d["submit_time"], dur, len(arr)) * dur
        after += d["shift_c"]
    return before, after


def cumulative_totals(t_now, day_start):
    """day_start~t_now에 제출된 job들의 **누적** 배출량 (CAST 적용 전 / 후).

    '지금 실행 중인 job'만 보는 before_after_totals()와 달리 시각이 흐를수록
    단조 증가한다. 두 막대가 정확히 같은 job 집합을 대상으로 하므로(제출 기준),
    차이가 곧 CAST가 그날 그 시점까지 아낀 양이다.
    """
    before = after = 0.0
    for h in range(int(day_start), int(t_now) + 1):
        b, a = _hour_bucket_totals(h)
        before += b
        after += a
    return before, after


def draw_timeline(running, t_now, day_start, height=280):
    """job별 요청·대기·실행(time-shift) 타임라인."""
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
                hovertext=f"{jid}<br>요청 {map_fmt(d['submit_time'])}"
                          f"<br>실행 {map_fmt(d['scheduled_start'])}"))
        if 0 <= sub <= 24:
            fig.add_trace(go.Scatter(x=[sub], y=[jid], mode="markers",
                marker=dict(color=MAP_SUBMIT_COLOR, size=9, symbol="diamond"),
                showlegend=False, hoverinfo="text",
                hovertext=f"요청 {map_fmt(d['submit_time'])}"))
    fig.add_vline(x=t_now - day_start, line=dict(color="#d33", width=1.5, dash="dash"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=8, b=0),
                      yaxis=dict(autorange="reversed", title=None), plot_bgcolor="white")
    fig.update_xaxes(range=[0, 24], tickmode="array", tickvals=list(range(0, 25)),
                     ticktext=[f"{h}" for h in range(25)],
                     title="시각 (시, UTC)", gridcolor="#eee")
    return fig


def map_arc(lon0, lat0, lon1, lat1, n=48, bump=0.1):
    """완만한 호(arc) 좌표."""
    t = np.linspace(0, 1, n)
    ease = np.sin(np.pi * t) ** 1.4  # 양 끝을 더 완만하게, 가운데만 살짝 부풀린 곡선
    lon = lon0 + (lon1 - lon0) * t
    lat = lat0 + (lat1 - lat0) * t + ease * abs(lon1 - lon0) * bump
    return lon, lat


def draw_map(routes=None, region_counts=None, height=560):
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
            lon, lat = map_arc(*MAP_REGION_COORD[o], *MAP_REGION_COORD[a])
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


def draw_forecast_chart(t_now):
    """24시간 리전별 탄소 예측 그래프."""
    forecast = api.get_forecast(t_hour=t_now, horizon=24)
    fdf = pd.DataFrame(forecast)
    fdf = fdf[[r for r in REGIONS if r in fdf.columns]]

    palette = ["#1565c0", "#6baed6", "#c62828", "#f4a6a6", "#2e7d32",
               "#81c784", "#ef6c00", "#f9c74f"]
    fig = go.Figure()
    for i, col in enumerate(fdf.columns):
        fig.add_trace(go.Scatter(
            x=list(range(len(fdf))), y=fdf[col], mode="lines", name=col,
            line=dict(width=2, color=palette[i % len(palette)]),
            hovertemplate=f"{col}<br>" + "+%{x}h: %{y:.0f} gCO₂/kWh<extra></extra>"))
    fig.update_layout(
        height=260, margin=dict(l=0, r=0, t=8, b=80), plot_bgcolor="white",
        legend=dict(orientation="h", x=0, y=-0.32, yanchor="top", font=dict(size=10)),
    )
    fig.update_xaxes(title=dict(text="t 시간 후 (h)", standoff=10), gridcolor="#eee", dtick=2)
    fig.update_yaxes(title="gCO₂/kWh", gridcolor="#eee")
    return fig


def draw_lb_diff_chart(before_total, after_total):
    """CAST 적용 전후 누적 탄소 막대그래프 (그날 0시부터 현재까지 쌓인 값)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["CAST 적용 전", "CAST 적용 후"], y=[before_total, after_total],
        marker_color=[LB_BASELINE_COLOR, LB_ACCENT_COLOR], width=0.35,
        text=[f"{before_total:,.0f}", f"{after_total:,.0f}"], textposition="outside",
        hovertemplate="%{x}<br>%{y:.0f} gCO₂<extra></extra>"))
    if before_total > 0:
        fig.add_annotation(
            x=1, y=after_total, yshift=26, showarrow=False,
            text=f"−{(before_total - after_total) / before_total * 100:.0f}%",
            font=dict(color=LB_ACCENT_COLOR, size=13))
    fig.update_layout(
        height=230, margin=dict(l=0, r=0, t=8, b=30), plot_bgcolor="white",
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(title="누적 탄소 배출량 (gCO₂)", gridcolor="#eee",
                     range=[0, LB_DIFF_AXIS_MAX])
    return fig
