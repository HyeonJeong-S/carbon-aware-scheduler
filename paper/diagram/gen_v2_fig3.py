# -*- coding: utf-8 -*-
"""v2 그림 3 — 예측 한 구간(v1 gen_figs_data.fig_forecast 그대로) + 24시간 seasonal naive 를 회색 점선으로 덧그린다.
"LSTM 은 SN-24 와 대등(4승 4패)"을 한 장면으로 보이기 위함(92 그림 계획 D-3). 서식·구간(CAL, t0=5400)은 v1 과 같다.
    ./.venv/bin/python paper/diagram/gen_v2_fig3.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from interface import carbon_2025                      # noqa: E402

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({"axes.unicode_minus": False, "axes.linewidth": 0.8,
                     "xtick.direction": "in", "ytick.direction": "in",
                     "xtick.major.width": 0.8, "ytick.major.width": 0.8,
                     "xtick.major.size": 2.6, "ytick.major.size": 2.6})
INK, GRAY = "#000000", "#7a7a7a"
COL = 215 / 72.0
LAB, TICK, NOTE = 8.2, 7.1, 6.6


def main():
    data = carbon_2025.load_2025()
    r, t0 = "US-CAL-CISO", 5400
    act = np.asarray(data["actual"][r])
    pred = np.concatenate([[act[t0]], data["pred24"][r][t0][:23]])        # 열0 = h+1 규약 보정 (v1 과 같음)
    sn24 = np.concatenate([[act[t0]], act[t0 + 1 - 24:t0 + 24 - 24]])     # 어제 같은 시각
    hist, fut = act[t0 - 168:t0], act[t0:t0 + 24]
    mae_l, mae_s = float(np.abs(fut - pred).mean()), float(np.abs(fut - sn24).mean())
    SHOW = 48
    hist = hist[-SHOW:]
    fig, ax = plt.subplots(figsize=(COL, 116 / 72.0), dpi=500)
    ax.plot(np.arange(-SHOW, 0), hist, color=GRAY, lw=1.4)          # 92 비평: 실측은 입력·출력 구간에서 한 굵기
    ax.plot(np.arange(24), fut, color=GRAY, lw=1.4, label="Actual")
    ax.plot(np.arange(24), pred, color=INK, lw=1.3, ls=(0, (3.5, 1.6)), label="LSTM")
    ax.plot(np.arange(24), sn24, color=INK, lw=0.8, ls=(0, (1.0, 1.3)), label="SN-24h")   # 검정 가는 점선 — 회색 실측과 갈린다
    ax.axvline(0, color=INK, lw=0.8)
    ax.axvspan(-SHOW - 2, 0, color="#f2f2f2", zorder=0)
    ax.text(-SHOW / 2, 14, "Input (last 48 h)", ha="center", fontsize=7.0)
    ax.text(12, 14, "Output", ha="center", fontsize=7.0)
    ax.set_xlim(-SHOW - 2, 25); ax.set_ylim(0, 245)
    ax.set_yticks([0, 50, 100, 150, 200]); ax.set_xticks([-48, -36, -24, -12, 0, 12, 24])
    ax.set_xlabel("Hours since issue time (h)", fontsize=LAB)
    ax.set_ylabel("Carbon intensity (gCO₂/kWh)", fontsize=LAB)
    ax.tick_params(labelsize=TICK)
    ax.legend(fontsize=NOTE, frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.02),
              handlelength=1.7, columnspacing=1.0, handletextpad=0.5, borderaxespad=0)
    fig.tight_layout(pad=0.3)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "v2_fig3_forecast_curve" + e))
    print(f"wrote v2_fig3_forecast_curve  (이 구간 MAE: LSTM {mae_l:.1f}, SN-24 {mae_s:.1f})")


if __name__ == "__main__":
    main()
