"""Dash 앱 조립 — 상단 내비게이션 + Dash Pages 컨테이너."""

import os

import dash
from dash import Dash, Input, Output, dcc, html

from interface.dashboard import data

_HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(_HERE, "pages")
ASSETS_DIR = os.path.join(_HERE, "assets")


def create_app(warm_up: bool = True):
    """Dash 앱을 조립한다. warm_up=False 면 백그라운드 사전 로딩(LSTM·job·검증)을 건너뛴다 (테스트용)."""
    app = Dash(
        __name__,
        use_pages=True,
        pages_folder=PAGES_DIR,
        assets_folder=ASSETS_DIR,
        suppress_callback_exceptions=True,   # 페이지마다 다른 컴포넌트를 쓰므로 필요
        title="CAST",
        update_title=None,
    )

    pages = sorted(dash.page_registry.values(), key=lambda p: p.get("order", 99))
    def _nav_id(page):
        return "nav-" + (page["path"].strip("/").replace("/", "-") or "home")

    nav_links = [
        dcc.Link(p["name"], href=p["path"], id=_nav_id(p), className="nav-link")
        for p in pages
    ]

    app.layout = html.Div([
        dcc.Location(id="url"),
        html.Div([
            dcc.Link([
                html.Span("CAST", className="brand-name"),
                html.Span("Carbon-Aware Spatio-Temporal Scheduler", className="brand-sub"),
            ], href="/", className="brand"),
            html.Nav(nav_links, className="nav", id="nav"),
        ], className="topbar"),
        html.Div(dash.page_container, className="page"),
    ])

    @app.callback(
        [Output(_nav_id(p), "className") for p in pages],
        Input("url", "pathname"),
    )
    def _highlight(pathname):
        pathname = pathname or "/"
        return ["nav-link active" if p["path"] == pathname else "nav-link" for p in pages]

    if warm_up:
        data.warm_up_async()
    return app
