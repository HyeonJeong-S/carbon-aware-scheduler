"""로드밸런서 — 탄소 인지 ILP 라우팅 (1년 실데이터 · Azure 8리전).

탭 4개는 interface/dashboard/lb_tabs/ 에 하나씩 있고, 여기서는 조립만 한다.
    inputs   ① 입력 데이터        compare  ② 전 / 후 비교
    sweep    ③ α 스윕 · 모드 비교   realtime ④ 실시간 라우팅 (LSTM 라이브)
"""

import dash
from dash import Input, Output, callback, dcc, html

from interface.dashboard import data, theme
from interface.dashboard.lb_tabs import compare, inputs, realtime, rerun, sweep

dash.register_page(__name__, path="/load-balancer", name="로드밸런서", order=2)

TABS = {"t1": ("① 입력 데이터", inputs.render), "t2": ("② 전 / 후 비교", compare.render),
        "t3": ("③ α 스윕 · 모드 비교", sweep.render), "t4": ("④ 실시간 라우팅 (LSTM)", realtime.render)}


def layout(**_):
    if not data.lb_results_available():
        return html.Div([
            html.H1("로드밸런서"),
            theme.notice("결과가 없습니다. 아래 '실험 다시 실행'을 누르거나 터미널에서 "
                         "`python -m load_balancer.framework.run_experiments` 를 실행하세요 (약 40분).", "warn"),
            rerun.render(),
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
        ], style={"display": "flex", "justifyContent": "space-between", "gap": "2rem", "alignItems": "flex-start"}),
        dcc.Tabs(id="lb-tabs", value="t1", className="tabs", children=[
            dcc.Tab(label=label, value=key, className="tab", selected_className="tab--selected")
            for key, (label, _) in TABS.items()
        ]),
        dcc.Loading(html.Div(id="lb-tab-body"), type="dot", delay_show=300),
        theme.hr(),
        rerun.render(),
        dcc.Download(id="lb-download"),
        dcc.Download(id="lb-rt-download"),
    ])


@callback(Output("lb-tab-body", "children"), Input("lb-tabs", "value"))
def render_tab(tab):
    return TABS[tab][1](data.lb_load_all())
