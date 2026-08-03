"""통합 대시보드 진입점 — 3개 모듈 UI를 한 앱에서 본다.

실행:
    streamlit run interface/app.py

우측 상단 드롭다운으로 화면을 전환해서 볼 수 있다(코드 복제 없음). 기본 선택은 메인 화면.
    전체 개요  : interface/views/overview.py
    로드밸런서 : load_balancer/02_프레임워크/app.py
    LSTM       : interface/views/lstm_view.py
    스케줄러   : scheduler/scheduler/gui.py
    최종       : interface/views/final.py     (기존 통합 화면)
    메인 화면  : interface/views/main.py      (신규 메인 화면, 작성 중)
"""

import os
import runpy
import sys

import streamlit as st

st.set_page_config(page_title="Carbon-Aware Scheduler", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { display: none; }
    div.block-container {
        padding-top: 0.6rem; padding-bottom: 1rem;
        padding-left: 1.2rem; padding-right: 1.2rem;
        max-width: 100%;
    }
    section[data-testid="stSidebar"] div.block-container { padding-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_HERE)
LB_DIR = os.path.join(REPO_ROOT, "load_balancer", "02_프레임워크")
SCHED_DIR = os.path.join(REPO_ROOT, "scheduler")
LSTM_DIR = os.path.join(REPO_ROOT, "carbon-forecast-LSTM")

# 각 모듈이 자기 폴더 기준으로 import 하므로 경로를 모두 등록한다.
# SCHED_DIR을 앞에 둬야 scheduler 패키지가 정규 패키지로 잡힌다.
for _p in (SCHED_DIR, LB_DIR, LSTM_DIR, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 하위 페이지 스크립트도 st.set_page_config를 호출하는데,
# 한 앱에서는 진입점만 호출할 수 있으므로 무력화한다.
st.set_page_config = lambda *a, **k: None

PAGES = {
    "메인 화면": os.path.join(_HERE, "views", "main.py"),
    "전체 개요": os.path.join(_HERE, "views", "overview.py"),
    "로드밸런서": os.path.join(LB_DIR, "app.py"),
    "LSTM": os.path.join(_HERE, "views", "lstm_view.py"),
    "스케줄러": os.path.join(SCHED_DIR, "scheduler", "gui.py"),
    "최종": os.path.join(_HERE, "views", "final.py"),
}

_showing_main = st.session_state.get("nav_choice", list(PAGES)[0]) == "메인 화면"

_date_col = _time_col = _play_col = None
if _showing_main:
    # 메인 화면일 때만 날짜/시간/재생 칸 자리를 예약해 드롭다운과 한 줄에 우측 정렬한다.
    # 실제 위젯(session_state, date_input 등)은 main.py가 이 칸 안에 그린다.
    _, _date_col, _time_col, _play_col, _nav_col = st.columns([5, 1, 1, 1, 1])
else:
    _, _nav_col = st.columns([8, 1])

with _nav_col:
    choice = st.selectbox(
        "화면 선택",
        list(PAGES),
        key="nav_choice",
        label_visibility="collapsed",
    )

if choice == "메인 화면":
    # 메인 화면은 사이드바 없이 완전한 흰 화면으로 보여준다.
    st.markdown(
        '<style>section[data-testid="stSidebar"] { display: none; }</style>',
        unsafe_allow_html=True,
    )
else:
    with st.sidebar:
        st.markdown("### Carbon-Aware Scheduler")
        st.divider()

script = PAGES[choice]
if not os.path.exists(script):
    st.error(f"화면 스크립트를 찾을 수 없습니다: {script}")
else:
    # 각 모듈 앱이 자기 폴더를 기준으로 상대경로를 쓰는 경우가 있어 cwd를 맞춰준다.
    _cwd = os.getcwd()
    _init_globals = {"_date_col": _date_col, "_time_col": _time_col,
                      "_play_col": _play_col} if _showing_main else {}
    try:
        os.chdir(os.path.dirname(script))
        runpy.run_path(script, init_globals=_init_globals, run_name="__main__")
    finally:
        os.chdir(_cwd)
