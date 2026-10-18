"""7회차 A[1] — 대칭 한계 배출 대리. 모든 리전·시각에 화석 몫의 강도 C/(1−CFE) 를 쓴다(출발지·목적지·기준 모두 같은 계열).
1−CFE 는 FLOOR(기본 0.05) 아래로 내리지 않는다(무탄소 전원이 거의 전부인 시각의 발산을 막음). 배정은 그대로 두고 채점만 다시 한다.
    ./.venv/bin/python -m scheduler.fossil_rescore main/joint ...      (FLOOR=0.1 로 바꿔 민감도)
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
FLOOR = float(os.environ.get("FLOOR", 0.05))


def fossil_actual(actual):
    df = pd.read_csv(os.path.join(ROOT, "lstm_source", "data", "carbon_intensity_test_2025.csv"), parse_dates=["timestamp"])
    df["h"] = ((df.timestamp - carbon_2025.BASE_TIME).dt.total_seconds() / 3600).round().astype(int)
    out = {}
    for r, a in actual.items():
        s = df[df.region == r].set_index("h")
        frac = np.full(len(a), np.nan)
        idx = s.index[(s.index >= 0) & (s.index < len(a))]
        frac[idx] = np.maximum(1 - s.loc[idx, "cfe_pct"].values / 100, FLOOR)
        frac = pd.Series(frac).ffill().bfill().values
        out[r] = a / frac
    return out


def main():
    data = carbon_2025.load_2025()
    W = capacity._Windows(fossil_actual(data["actual"]), data["pred24"])
    for name in sys.argv[1:]:
        st = json.load(open(os.path.join(V2, name, "stats.json")))
        d = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
        d = d[d.submit_time >= st["score_from"]]
        b = sum(W.actual_mean(o, s, x) * x for o, s, x in zip(d.origin, d.submit_time, d.duration))
        e = sum(W.actual_mean(r, s, x) * x for r, s, x in zip(d.region, d.scheduled_start, d.duration))
        print(f"{name}: 평균 계수 {st['savings_pct']:.2f}% → 화석 몫 대리(floor {FLOOR}) {100 * (1 - e / b):.2f}%")


if __name__ == "__main__":
    main()
