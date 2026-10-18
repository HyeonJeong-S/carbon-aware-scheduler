"""3회차 A[8]·C[5] — 전송 에너지 출발지 귀속 손익분기(GB)와 '전송이 계산보다 큰' 옮긴 작업의 몫.
전송 탄소 = GB × 0.06 kWh/GB × 출발 리전의 시작 시각 실측 강도(작업 길이 평균). 1 kW 상수 회계(duration 은 시간 단위라 계산 에너지 = d kWh).
    ./.venv/bin/python scheduler/transfer_breakeven.py <CAST 실행> <시간만 실행>   예: azure/joint azure/time_only
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from interface import carbon_2025
from scheduler import capacity

V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "v2")
KWH_PER_GB = 0.06


def load(name):
    st = json.load(open(os.path.join(V2, name, "stats.json")))
    df = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
    return st, df[df.submit_time >= st["score_from"]]


def main():
    cast, tonly = sys.argv[1], sys.argv[2]
    data = carbon_2025.load_2025()
    actual = data["actual"]
    W = capacity._Windows(actual, data["pred24"])     # actual_mean 만 쓴다(예측은 자리만 채움)
    st, df = load(cast)
    st_t, _ = load(tonly)
    base = st["baseline_kg"]
    mv = df[df.region != df.origin]
    inten_o = np.array([W.actual_mean(o, s, d) for o, s, d in zip(mv.origin, mv.scheduled_start, mv.duration)])
    per_gb = float((inten_o * KWH_PER_GB).sum() / 1000)            # kg per GB/작업
    kg = st["total_carbon_kg"]; kg_t = st_t["total_carbon_kg"]
    print(f"{cast}: 채점 {len(df):,} 옮김 {len(mv):,}({100*len(mv)/len(df):.1f}%)  kg {kg:,.1f}  시간만 kg {kg_t:,.1f}  GB당 {per_gb:,.1f} kg")
    print(f"  손익분기: 시간만과 같아지는 GB {(kg_t - kg)/per_gb:.1f}, 절감 0 이 되는 GB {(base - kg)/per_gb:.1f}")
    short = mv[mv.duration < KWH_PER_GB]                             # 1 GB 전송 에너지 > 계산 에너지
    print(f"  1 GB 전송이 계산보다 큰 옮긴 작업: {len(short):,}건 = 옮긴 작업의 {100*len(short)/len(mv):.1f}%, 옮긴 작업 배출의 {100*short.carbon_emitted.sum()/mv.carbon_emitted.sum():.2f}%")


if __name__ == "__main__":
    main()
