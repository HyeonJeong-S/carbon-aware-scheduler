"""예측기 변형 — 전부 capacity._Windows 의 pred24 규약(열 j = 실측(h+1+j))을 따른다.

  oracle(actual)                 완전예지
  sn24(actual)                   24시간 seasonal naive: pred[h][j] = actual[h+1+j−24]
  frozen_daily(pred)             하루 한 번(00시 발행)만 쓰는 LSTM — 정확도는 LSTM, 매시 안 바뀜
  jittered_oracle(actual, pred)  오라클 + 매시 새로 뽑는 가우시안 잡음, 리전별 MAE 를 LSTM 과 맞춤
  mix(actual, pred, lam)         oracle + λ·(pred − oracle): λ=0 오라클, λ=1 LSTM — 예측 품질 다이얼

쓰임: 2단계가 "모두가 같은 골을 보면" 쏠리는지(통계 감사 2026-10-16, 정리.txt [80])를 가르는 대조.
"""
import math

import numpy as np

HORIZON = 24


def oracle(actual, horizon=HORIZON):
    out = {}
    for r, arr in actual.items():
        n = len(arr)
        idx = np.arange(n)[:, None] + 1 + np.arange(horizon)[None, :]
        out[r] = arr[np.minimum(idx, n - 1)].astype(float)
    return out


def sn24(actual, horizon=HORIZON):
    out = {}
    for r, arr in actual.items():
        n = len(arr)
        idx = np.arange(n)[:, None] + 1 + np.arange(horizon)[None, :] - 24
        out[r] = arr[np.clip(idx, 0, n - 1)].astype(float)
    return out


def frozen_daily(pred, horizon=HORIZON):
    """시각 h 의 예측을 그날 00시(h0) 발행분에서 가져온다. 대상 T = h+1+j 가 h0 발행의 24시간
    범위를 넘으면 다음날 00시 발행분에서 이어 쓴다."""
    out = {}
    for r, src in pred.items():
        n = src.shape[0]
        q = np.zeros_like(src)
        for h in range(n):
            h0 = 24 * (h // 24)
            for j in range(horizon):
                k = h + 1 + j - h0 - 1
                if k < horizon:
                    q[h, j] = src[min(h0, n - 1), k]
                else:
                    q[h, j] = src[min(h0 + 24, n - 1), k - horizon]
        out[r] = q
    return out


def lstm_mae(actual, pred, horizon=HORIZON):
    """리전별 LSTM 전 지평 MAE (pred24 규약으로 직접 계산)."""
    out = {}
    for r, p in pred.items():
        a = actual[r]
        n = min(len(a), p.shape[0])
        T = np.arange(n)[:, None] + 1 + np.arange(horizon)[None, :]
        ok = len(a) > T
        out[r] = float(np.mean(np.abs(p[:n][ok] - a[np.minimum(T, len(a) - 1)][ok])))
    return out


def jittered_oracle(actual, pred, seed=0, horizon=HORIZON):
    """가우시안 잡음의 표준편차 sd 를 MAE = sd·√(2/π) 가 LSTM 의 리전별 MAE 와 같도록 둔다."""
    rng = np.random.default_rng(seed)
    orc = oracle(actual, horizon)
    maes = lstm_mae(actual, pred, horizon)
    out = {}
    for r in orc:
        sd = maes[r] / math.sqrt(2 / math.pi)
        q = orc[r] + rng.normal(0, sd, orc[r].shape)
        out[r] = np.maximum(q, 0.0)
    return out


def mix(actual, pred, lam, horizon=HORIZON):
    orc = oracle(actual, horizon)
    out = {}
    for r in orc:
        n = min(orc[r].shape[0], pred[r].shape[0])
        out[r] = orc[r][:n] + lam * (pred[r][:n] - orc[r][:n])
    return out


def build(name, actual, pred_lstm, seed=0):
    """run_v2 --forecast 문자열 → pred24 배열.

    "기본|리전=예측기[,리전=예측기]" 꼴이면 기본 예측기 위에 리전별 예측기를 덮어쓴다
    (예: "lstm|US-CAL-CISO=sn24" — 캘리포니아만 기상 입력이 없는 SN-24, 나머지는 LSTM. 심사 M6 대조)."""
    if "|" in name:
        base_name, ov = name.split("|", 1)
        out = dict(build(base_name, actual, pred_lstm, seed))
        for item in ov.split(","):
            r, fname = item.split("=")
            if r not in out:
                raise ValueError(f"모르는 리전: {r}")
            out[r] = build(fname, actual, pred_lstm, seed)[r]
        return out
    if name == "lstm":
        return pred_lstm
    if name == "oracle":
        return oracle(actual)
    if name == "sn24":
        return sn24(actual)
    if name == "lstm_daily":
        return frozen_daily(pred_lstm)
    if name.startswith("noisy_oracle"):
        s = int(name.split(":")[1]) if ":" in name else seed
        return jittered_oracle(actual, pred_lstm, seed=s)
    if name.startswith("mix"):
        return mix(actual, pred_lstm, float(name[3:]))
    raise ValueError(f"모르는 예측기: {name}")
