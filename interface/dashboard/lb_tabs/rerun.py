"""'실험 다시 실행' 블록 — run_experiments 를 백그라운드 프로세스로 띄우고 로그를 폴링한다."""

import time

from dash import Input, Output, callback, ctx, dcc, html

from interface.dashboard import data, theme


def render() -> html.Details:
    return theme.details("🔄 실험 다시 실행 (α 스윕, 약 40분)", html.Div([
        theme.caption("baseline + 고정 α 5개 + α=auto 를 1년치 전체로 다시 돌려 results/ 와 routed/ 를 "
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
    msg = ("완료 — 결과가 갱신되었습니다 (탭을 다시 선택하면 반영)." if kind == "ok"
           else f"실패 (returncode={st['returncode']})")
    return html.Div([theme.notice(msg, kind), html.Pre(st["log_tail"], className="mono")]), True
