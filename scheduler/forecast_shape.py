"""모의 심사 [11]: 예측기별 '곡선 모양' 지표 — 배정이 보는 것은 값의 오차가 아니라 순서라는 주장의 수치 근거.
각 발행 시각 h(채점 창 day 8+)와 리전에 대해 향후 24시간 창에서
  (a) 스피어만 순위상관 ρ_s(예측, 실측)
  (b) 최저 시각 적중률: argmin(예측) == argmin(실측)
  (c) 납작함 비: (max−min)(예측) / (max−min)(실측)
를 재고 리전 평균·전체 평균을 낸다. 예측기: lstm, sn24, oracle(=1, 검산), lstm_daily, noisy_oracle:0, mix0.25/0.5/0.75.
    ./.venv/bin/python scheduler/forecast_shape.py [--forecasts lstm,sn24,oracle] [--score-from 168]
"""
import argparse
import json

import numpy as np
from scipy.stats import spearmanr

from interface import carbon_2025
from scheduler import forecasters


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--forecasts", default="lstm,sn24,oracle,lstm_daily,noisy_oracle:0,mix0.25,mix0.5,mix0.75"); ap.add_argument("--score-from", type=int, default=168)
    a = ap.parse_args()
    data = carbon_2025.load_2025(); actual, lstm = data["actual"], data["pred24"]
    H = 24; res = {}
    for name in a.forecasts.split(","):
        pred = forecasters.build(name, actual, lstm, seed=0)
        rows = {}
        for r, arr in actual.items():
            n = len(arr); p = pred[r]
            hs = range(a.score_from, min(n - H - 1, p.shape[0]))
            T = np.arange(1, H + 1)
            sp, hit, flat = [], [], []
            for h in hs:
                y = arr[h + T]; q = p[h, :H]
                if np.ptp(y) < 1e-9 or np.ptp(q) < 1e-9: continue
                sp.append(spearmanr(q, y).correlation); hit.append(int(np.argmin(q) == np.argmin(y))); flat.append(np.ptp(q) / np.ptp(y))
            rows[r] = dict(spearman=float(np.mean(sp)), min_hit=float(np.mean(hit)), flat_ratio=float(np.median(flat)), n=len(sp))
        res[name] = dict(by_region=rows, spearman=float(np.mean([v["spearman"] for v in rows.values()])),
                         min_hit=float(np.mean([v["min_hit"] for v in rows.values()])), flat_ratio=float(np.mean([v["flat_ratio"] for v in rows.values()])))
        print(f"{name:14s} 스피어만 {res[name]['spearman']:.3f}  최저시각 적중 {100*res[name]['min_hit']:.1f}%  납작함(중앙값 비) {res[name]['flat_ratio']:.3f}  | "
              + " ".join(f"{r.split('-')[-1][:3]} {v['spearman']:.2f}/{100*v['min_hit']:.0f}%/{v['flat_ratio']:.2f}" for r, v in rows.items()), flush=True)
    json.dump(res, open("scheduler/data/v2/analysis/forecast_shape.json", "w"), indent=1)
    print("저장 scheduler/data/v2/analysis/forecast_shape.json")

if __name__ == "__main__":
    main()
