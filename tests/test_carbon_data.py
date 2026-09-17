"""탄소 데이터 로딩 — LSTM 입력 이력, 실측 시계열, 2025 eval_records 복원 규약."""

import numpy as np
import pandas as pd
import pytest

from interface import carbon_2025, carbon_history
from interface.regions import REGIONS


def test_history_from_master_series_marks_placeholder():
    master = {r: [400.0, 300.0, 200.0] for r in REGIONS}
    df, placeholder = carbon_history.load_history(master_series=master)
    assert placeholder is True
    assert set(df.columns) >= {"timestamp", "region", "carbon_intensity", "cfe_pct", "re_pct"}
    assert len(df) == 3 * len(REGIONS)
    # 탄소강도가 낮을수록 청정 비중이 높다는 단조 가정
    kr = df[df.region == "KR"].sort_values("timestamp")
    assert list(kr.cfe_pct) == sorted(kr.cfe_pct)


def test_history_with_measured_cfe_re_is_not_placeholder(tmp_path):
    p = tmp_path / "hist.csv"
    pd.DataFrame({"timestamp": ["2026-01-01 00:00:00"] * 2, "region": ["Korea", "FR"],
                  "carbon_intensity": [400.0, 30.0], "cfe_pct": [30.0, 95.0], "re_pct": [10.0, 20.0]}
                 ).to_csv(p, index=False)
    df, placeholder = carbon_history.load_history(carbon_csv=str(p))
    assert placeholder is False
    assert set(df.region) == {"KR", "FR"}          # LB 표기도 표준 코드로


def test_history_without_any_source_raises():
    with pytest.raises(FileNotFoundError):
        carbon_history.load_history(carbon_csv="/nowhere.csv")


def test_actual_series_forward_fills_gaps(tmp_path):
    p = tmp_path / "actual.csv"
    rows = []
    for r in REGIONS:
        rows += [{"timestamp": "2026-01-01 00:00:00", "region": r, "carbon_intensity": 100.0},
                 {"timestamp": "2026-01-01 03:00:00", "region": r, "carbon_intensity": 400.0}]
    pd.DataFrame(rows).to_csv(p, index=False)
    series = carbon_history.load_actual_series(6, carbon_csv=str(p))
    assert series["KR"] == [100.0, 100.0, 100.0, 400.0, 400.0, 400.0]


def test_actual_series_returns_none_when_missing_regions(tmp_path):
    p = tmp_path / "partial.csv"
    pd.DataFrame({"timestamp": ["2026-01-01 00:00:00"], "region": ["KR"], "carbon_intensity": [1.0]}
                 ).to_csv(p, index=False)
    assert carbon_history.load_actual_series(3, carbon_csv=str(p)) is None


def test_warmup_repeats_first_valid_day_profile():
    arr = np.full(72, np.nan)
    arr[48:72] = np.arange(24)                    # 첫 유효일 = 3일째 (실데이터는 1월 8일)
    out = carbon_2025._fill_warmup(arr)
    assert list(out[:24]) == list(range(24))      # 1일째 = 첫 유효일 프로파일
    assert list(out[24:48]) == list(range(24))    # 2일째도 반복
    assert not np.isnan(out).any()


def test_ffill_fills_interior_gaps_only():
    arr = np.array([1.0, np.nan, np.nan, 4.0, np.nan])
    assert list(carbon_2025._ffill(arr)) == [1.0, 1.0, 1.0, 4.0, 4.0]


@pytest.mark.slow
def test_eval_records_2025_cover_full_year_for_all_regions():
    data = carbon_2025.load_2025()
    assert set(data["actual"]) == set(REGIONS)
    assert data["n_hours"] >= 365 * 24
    fc = carbon_2025.forecast_at(data, t_hour=500)
    assert all(len(v) == 24 for v in fc.values())
    assert fc["KR"][0] == pytest.approx(float(data["actual"]["KR"][500]))   # index 0 = 현재 실측
