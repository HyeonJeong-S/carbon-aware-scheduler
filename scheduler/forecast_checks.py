"""1회차 숫자 검증 D[26] 대응 — 원고의 예측 숫자를 저장된 스크립트로 다시 낸다(이전엔 즉석 계산이라 출처가 없었다).
  (1) 전 지평 MAE: LSTM / 직전값(persistence) / 24시간 전 값(SN-24) / 168시간 전 값(SN-168). 시험 연도 2025 전체와 평가 구간(day 8+) 두 가지.
  (2) 예측 최저 시각이 발행마다 옮겨 가는 비율: 리전마다, 연속한 두 발행 h−1, h 에서 24시간 창 안 최저 '목표 시각(절대)'이 다른 비율.
      창이 한 시간 밀리므로 같은 절대 시각이 두 창에 모두 있을 때만 센다(직전 창의 최저 시각이 지금 창 밖으로 나간 경우는 뺀다).
    ./.venv/bin/python scheduler/forecast_checks.py
"""
import json

import numpy as np

from interface import carbon_2025
from scheduler import forecasters

H = 24

def persistence(actual):
    return {r: np.repeat(a[:, None], H, axis=1).astype(float) for r, a in actual.items()}

def sn(actual, lag):
    out = {}
    for r, a in actual.items():
        n = len(a); idx = np.arange(n)[:, None] + 1 + np.arange(H)[None, :] - lag
        out[r] = a[np.clip(idx, 0, n - 1)].astype(float)
    return out

def mae(actual, pred, lo):
    errs = []
    for r, a in actual.items():
        p = pred[r]; n = min(len(a), p.shape[0])
        T = np.arange(n)[:, None] + 1 + np.arange(H)[None, :]
        ok = (len(a) > T) & (np.arange(n)[:, None] >= lo)
        errs.append(np.abs(p[:n] - a[np.minimum(T, len(a) - 1)])[ok])
    return float(np.mean(np.concatenate(errs)))

def shift_rate(pred, lo, conditional):
    """conditional=False: 연속 두 발행의 절대 최저 시각이 다른 비율(창이 밀려 나간 경우도 셈).
    conditional=True: 직전 최저 시각이 지금 창 안에 남아 있을 때만 셈."""
    tot = moved = 0
    for r, p in pred.items():
        am = np.argmin(p[:, :H], axis=1) + np.arange(p.shape[0]) + 1     # 절대 목표 시각
        for h in range(max(lo, 1), p.shape[0]):
            prev = am[h - 1]
            if conditional and prev < h + 1:
                continue
            tot += 1; moved += int(am[h] != prev)
    return moved / tot if tot else float("nan")

def main():
    d = carbon_2025.load_2025(); actual, lstm = d["actual"], d["pred24"]
    preds = {"lstm": lstm, "persistence": persistence(actual), "sn24": sn(actual, 24), "sn168": sn(actual, 168), "oracle": forecasters.oracle(actual)}
    res = {}
    for name, p in preds.items():
        res[name] = dict(mae_year=mae(actual, p, 0), mae_day8=mae(actual, p, 168), shift_day8=shift_rate(p, 168, False), shift_day8_cond=shift_rate(p, 168, True))
        print(f"{name:12s} MAE 2025 전체 {res[name]['mae_year']:.2f} | day8+ {res[name]['mae_day8']:.2f} | 최저 시각 이동 {100*res[name]['shift_day8']:.1f}% (창 안 조건부 {100*res[name]['shift_day8_cond']:.1f}%)")
    json.dump(res, open("scheduler/data/v2/analysis/forecast_checks.json", "w"), indent=1)

if __name__ == "__main__":
    main()
