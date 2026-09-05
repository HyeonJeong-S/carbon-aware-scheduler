"""LSTM 경계 — 더미 백엔드는 결정적이고 계약 형식을 지키며, 모델이 있으면 실제 LSTM 이 응답한다."""

import importlib.util

import numpy as np
import pytest

from interface import carbon_forecast_api as api
from interface.regions import REGIONS


def test_dummy_series_is_deterministic_and_positive():
    a = api.generate_master_series(100)
    b = api.generate_master_series(100)
    assert set(a) == set(REGIONS)
    for r in REGIONS:
        assert len(a[r]) == 100
        assert a[r] == b[r]
        assert min(a[r]) >= 5


def test_get_forecast_contract_with_dummy_backend():
    fc = api.get_forecast(t_hour=10, horizon=24, prefer_lstm=False)
    assert set(fc) == set(REGIONS)
    assert all(len(v) == 24 for v in fc.values())
    assert api.last_backend() == "dummy"


def test_slice_pads_past_end_with_last_value():
    master = {r: [1.0, 2.0, 3.0] for r in REGIONS}
    out = api._slice_master(master, t_hour=1, horizon=5)
    assert out["KR"] == [2.0, 3.0, 3.0, 3.0, 3.0]


def test_dummy_slice_matches_master_series():
    master = api.generate_master_series(50)
    fc = api.get_forecast(t_hour=7, horizon=24, master_series=master, prefer_lstm=False)
    assert fc["FR"] == master["FR"][7:31]


@pytest.mark.slow
@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch 미설치 — 더미로 폴백")
def test_real_lstm_answers_inside_live_window():
    assert api.init_lstm(carbon_csv=api.LSTM_DATA_CSV), api.status()["error"]
    fc = api.get_forecast(t_hour=180, horizon=24)      # 2026-01-08 12:00 — 워밍업 이후
    assert api.last_backend() == "lstm"
    assert set(fc) == set(REGIONS)
    for r in REGIONS:
        vals = np.asarray(fc[r])
        assert vals.shape == (24,)
        assert np.all(np.isfinite(vals)) and vals.min() > 0


@pytest.mark.slow
@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch 미설치")
def test_real_lstm_falls_back_before_warmup():
    api.init_lstm(carbon_csv=api.LSTM_DATA_CSV)
    api.get_forecast(t_hour=10, horizon=24)            # 168h 이력이 없는 시점
    assert api.last_backend() == "dummy"
