"""6회차 A[2] — 인도 자료의 단절 확인과, 인도를 뺀 예측 지표.
(1) 리전별 하루 변동(최댓값−최솟값) 월평균, 2024-07 ~ 2025-12 (학습·검증·시험 파일을 이어서)
(2) forecast_checks 의 MAE·최저 시각 이동을 전체 / 인도 제외 / 인도만 으로
    ./.venv/bin/python -m scheduler.india_check
"""
import os

import pandas as pd

from interface import carbon_2025
from scheduler import forecast_checks as fc
from scheduler import forecasters

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    D = os.path.join(ROOT, "lstm_source", "data")
    df = pd.concat([pd.read_csv(os.path.join(D, f), parse_dates=["timestamp"]) for f in
                    ["carbon_intensity_val_2024.csv", "carbon_intensity_test_2025.csv"]])
    df["day"] = df.timestamp.dt.floor("D")
    rng = df.groupby(["region", "day"]).carbon_intensity.agg(lambda s: s.max() - s.min()).reset_index()
    rng["month"] = rng.day.dt.to_period("M")
    tab = rng.groupby(["month", "region"]).carbon_intensity.mean().unstack().round(0)
    print("하루 변동(최댓값−최솟값) 월평균, gCO2/kWh"); print(tab.loc["2024-07":"2025-06"].to_string())
    d = carbon_2025.load_2025(); actual, lstm = d["actual"], d["pred24"]
    preds = {"lstm": lstm, "sn24": fc.sn(actual, 24), "oracle": forecasters.oracle(actual)}
    for lab, keep in [("전체", list(actual)), ("인도 제외", [r for r in actual if r != "IN"]), ("인도만", ["IN"])]:
        a = {r: actual[r] for r in keep}
        for name, p in preds.items():
            pp = {r: p[r] for r in keep}
            print(f"{lab:6s} {name:7s} MAE day8+ {fc.mae(a, pp, 168):.2f} | 최저 시각 이동 {100 * fc.shift_rate(pp, 168, False):.1f}%")


if __name__ == "__main__":
    main()
