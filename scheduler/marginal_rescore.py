"""5회차 A[1] — 한계 배출 상한 시나리오. 배정은 그대로 두고, 출발 리전이 아닌 프랑스로 옮겨 간 작업의 배출을
같은 시각 독일의 평균 탄소집약도로 센다(프랑스가 더 받은 부하만큼 이웃 망의 화석 발전이 돈다고 보는 거친 상한).
다른 작업과 기준 배출은 평균 계수 그대로.
    ./.venv/bin/python -m scheduler.marginal_rescore main/joint main/joint_a1 ...
"""
import json
import os
import sys

import pandas as pd

from interface import carbon_2025
from scheduler import capacity

V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "v2")
SINK, PROXY = "FR", "DE"


def main():
    data = carbon_2025.load_2025()
    W = capacity._Windows(data["actual"], data["pred24"])
    for name in sys.argv[1:]:
        st = json.load(open(os.path.join(V2, name, "stats.json")))
        d = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
        d = d[d.submit_time >= st["score_from"]]
        moved = (d.region == SINK) & (d.origin != SINK)
        e = d.carbon_emitted.copy()
        e[moved] = [W.actual_mean(PROXY, s, x) * x for s, x in zip(d.scheduled_start[moved], d.duration[moved])]
        kg = e.sum() / 1000
        print(f"{name}: 평균 계수 {st['savings_pct']:.2f}% → 한계 상한 시나리오 {100 * (1 - kg / st['baseline_kg']):.2f}%  (프랑스로 옮긴 작업 {moved.sum():,}건)")


if __name__ == "__main__":
    main()
