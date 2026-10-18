"""4회차 A[2] — 배출계수 기준 민감도. 받은 자료는 직접(direct) 기준으로 보인다(원자력·재생을 0 으로 셈).
배정은 그대로 두고, 무탄소 전원에 전과정 배출을 더한 근사 계열로 채점만 다시 한다:
  C_lca(h) = C_direct(h) + 12 g × 원자력 몫(h) + 30 g × 재생 몫(h)
  원자력 몫 = (cfe_pct − re_pct)/100, 재생 몫 = re_pct/100 (lstm_source/data/carbon_intensity_test_2025.csv).
  12 g 은 원자력, 30 g 은 풍력(11)·수력(24)·태양광(41~48) 의 중앙값 사이를 어림한 값 — 화석 전원의 상류 배출은 넣지 않았다(보수적).
    ./.venv/bin/python -m scheduler.lca_rescore main/joint main/joint_a1 ...
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from interface import carbon_2025
from scheduler import capacity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "scheduler", "data", "v2")
NUC_G, RE_G = 12.0, 30.0


def lca_actual(actual):
    df = pd.read_csv(os.path.join(ROOT, "lstm_source", "data", "carbon_intensity_test_2025.csv"), parse_dates=["timestamp"])
    df["h"] = ((df.timestamp - carbon_2025.BASE_TIME).dt.total_seconds() / 3600).round().astype(int)
    out = {}
    for r, a in actual.items():
        s = df[df.region == r].set_index("h")
        add = np.zeros(len(a))
        idx = s.index[(s.index >= 0) & (s.index < len(a))]
        nuc = (s.loc[idx, "cfe_pct"] - s.loc[idx, "re_pct"]).clip(lower=0) / 100
        add[idx] = NUC_G * nuc.values + RE_G * s.loc[idx, "re_pct"].values / 100
        out[r] = a + add
    return out


def main():
    data = carbon_2025.load_2025()
    Wd = capacity._Windows(data["actual"], data["pred24"])
    Wl = capacity._Windows(lca_actual(data["actual"]), data["pred24"])
    for name in sys.argv[1:]:
        st = json.load(open(os.path.join(V2, name, "stats.json")))
        d = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
        d = d[d.submit_time >= st["score_from"]]
        b_d = sum(Wd.actual_mean(o, s, x) * x for o, s, x in zip(d.origin, d.submit_time, d.duration)) / 1000
        b_l = sum(Wl.actual_mean(o, s, x) * x for o, s, x in zip(d.origin, d.submit_time, d.duration)) / 1000
        e_l = sum(Wl.actual_mean(r, s, x) * x for r, s, x in zip(d.region, d.scheduled_start, d.duration)) / 1000
        assert abs(b_d - st["baseline_kg"]) < 0.5
        print(f"{name}: 직접 {st['savings_pct']:.2f}% → 전과정 근사 {100 * (1 - e_l / b_l):.2f}%  (기준 {b_d:,.1f} → {b_l:,.1f} kg, 결과 {st['total_carbon_kg']:,.1f} → {e_l:,.1f} kg)")


if __name__ == "__main__":
    main()
