"""대시보드 — 서버 없이 앱을 조립하고, 어떤 백엔드 상태에서도 페이지 레이아웃이 만들어지는지 검증한다."""

import dash
import pytest

from interface import carbon_forecast_api as api
from interface.dashboard import data
from interface.dashboard.app import create_app


@pytest.fixture(scope="module")
def app():
    return create_app(warm_up=False)


@pytest.mark.parametrize("state", [
    {"status": "idle", "n_jobs": 0, "elapsed": None, "error": None},
    {"status": "running", "n_jobs": 0, "elapsed": None, "error": None},
    {"status": "error", "n_jobs": 0, "elapsed": 3.0, "error": "boom"},
    {"status": "done", "n_jobs": 146000, "elapsed": 42.4, "error": None},
])
def test_validation_detail_handles_every_state(state):
    text = data.validation_detail(state)
    assert isinstance(text, str) and text


def test_all_five_pages_registered(app):
    paths = {p["path"] for p in dash.page_registry.values()}
    assert paths == {"/", "/overview", "/load-balancer", "/lstm", "/scheduler"}


def test_overview_layout_builds_while_validation_running(app, monkeypatch):
    """검증이 아직 도는 중(elapsed=None)에 페이지를 열어도 500 이 나면 안 된다 (회귀)."""
    monkeypatch.setattr(data, "validation_state", lambda: {
        "status": "running", "n_jobs": 0, "elapsed": None, "error": None, "comparison": None})
    monkeypatch.setattr(data, "lb_results_available", lambda: False)
    monkeypatch.setattr(api, "status", lambda: {
        "ready": False, "error": "torch 없음", "placeholder_cfe_re": True,
        "forecastable_from": None, "history_end": None, "last_backend": None})
    monkeypatch.setattr(api, "backend_info", lambda: "더미")
    page = next(p for p in dash.page_registry.values() if p["path"] == "/overview")
    assert page["layout"]() is not None


def test_load_balancer_page_without_results_shows_hint(app, monkeypatch):
    monkeypatch.setattr(data, "lb_results_available", lambda: False)
    page = next(p for p in dash.page_registry.values() if p["path"] == "/load-balancer")
    layout = page["layout"]()
    assert "결과가 없습니다" in str(layout)
