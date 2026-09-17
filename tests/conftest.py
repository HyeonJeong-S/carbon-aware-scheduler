"""공통 fixture — 작은 합성 데이터로 빠르게 도는 단위 테스트가 기본이고,
실데이터(146k job · LSTM 모델)를 쓰는 테스트는 `slow` 마커로 분리한다."""

import numpy as np
import pandas as pd
import pytest

from interface.regions import REGIONS


@pytest.fixture
def flat_forecast():
    """모든 리전이 24시간 내내 같은 값 — 탄소 차이가 없는 예측."""
    return {r: [300.0] * 24 for r in REGIONS}


@pytest.fixture
def valley_forecast():
    """모든 리전이 t+6h 에 가장 깨끗하고(50), 나머지는 500."""
    series = [500.0] * 24
    series[6] = 50.0
    return {r: list(series) for r in REGIONS}


def make_job(**kw):
    """스케줄러 job dict (시간 단위: 시). deadline 은 submit + L_max + duration 규약."""
    job = {"id": "j_test", "submit_time": 0.0, "duration": 1.0, "k": 1, "L_max": 12.0,
           "region": "KR", "carbon_region": None}
    job.update(kw)
    job.setdefault("deadline", job["submit_time"] + job["L_max"] + job["duration"])
    return job


@pytest.fixture
def jobs_csv(tmp_path):
    """jobs.csv 규약(초 단위, LB 표기 리전)으로 된 작은 파일."""
    df = pd.DataFrame({
        "job_name": ["j_000001", "j_000002", "j_000003"],
        "submit_time": [3600.0, 7200.0, 7260.0],
        "duration": [1800.0, 60.0, 3600.0],
        "region": ["Korea", "US_West", "France"],
        "k": [1, 5, 2],
        "L_max": [43200.0, 2.0, 7200.0],
        "submit_local_hour": [10.0, 18.0, 3.0],
        "band": ["day", "day", "night"],
    })
    p = tmp_path / "jobs.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def rng():
    return np.random.default_rng(0)
