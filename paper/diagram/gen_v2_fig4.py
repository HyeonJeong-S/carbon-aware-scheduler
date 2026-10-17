# -*- coding: utf-8 -*-
"""v2 그림 4 — 한 슬롯을 연다: 표 1 과 같은 작업(j_098510, 한국 출발, h=3499 = 2025-05-26 19:00 UTC)에 대해
α 열한 개가 고른 (리전, 시작 오프셋). 표식: ● 무릎점(α=0.5) 자리, ○ 그 밖의 α 자리. 같은 리전으로 간 α 는
표 1 의 띠 그대로 라벨 하나에 모았다(0 / 0.1–0.3 / 0.4–0.5 / 0.6–0.9 / 1). 배경 음영 = 그 슬롯의 예측 탄소집약도.
첫 판(작업 셋 × α 셋)은 표 1 과 다른 작업(j_098546)을 골라 92 비평에서 걸렸다 — 표 1 의 작업 하나만 그린다.
자료: v2_slot3499_full.json(배정)·v2_slot3499.json(표 1 의 작업 id). 서식은 v1(gen_figs_data) 상수.
    ./.venv/bin/python paper/diagram/gen_v2_fig4.py
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

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
SHORT = {"US-CAL-CISO": "California", "US-TEX-ERCO": "Texas", "US-NY-NYIS": "New York", "FR": "France",
         "DE": "Germany", "KR": "Korea", "IN": "India", "JP": "Japan"}


def main():
    r = json.load(open(os.path.join(HERE, "v2_slot3499_full.json")))
    job = json.load(open(os.path.join(HERE, "v2_slot3499.json")))["kr_jobs"][0]
    knee = r["alpha_chosen"]
    regions = list(r["pred_at_slot"].keys())
    cands = sorted(r["candidates"], key=lambda c: c["alpha"])
    # 리전이 바뀌거나 칸이 건너뛰면 띠를 끊는다 — 표 1 의 행과 같은 묶음
    bands = []
    for c in cands:
        reg, i = c["assign"][job]
        # 리전이 같아도 칸이 건너뛰면(α=0 의 i=0 과 0.1 의 i=6) 표 1 처럼 따로 띤다
        if bands and bands[-1]["reg"] == reg and min(abs(i - q) for q in bands[-1]["pos"]) <= 1:
            bands[-1]["alphas"].append(c["alpha"]); bands[-1]["pos"].add(i)
        else:
            bands.append({"reg": reg, "alphas": [c["alpha"]], "pos": {i}})
    P = np.array([r["pred_at_slot"][g] for g in regions])
    vmax = math.ceil(P.max() / 100) * 100
    cmap = LinearSegmentedColormap.from_list("ink", ["#ffffff", "#8c8c8c"])
    fig, ax = plt.subplots(figsize=(COL, 150 / 72.0), dpi=500)
    im = ax.imshow(P, cmap=cmap, aspect="auto", vmin=0, vmax=vmax, zorder=0,
                   extent=(-0.5, 23.5, len(regions) - 0.5, -0.5))
    knee_pos = cands[[c["alpha"] for c in cands].index(knee)]["assign"][job]
    for b in bands:
        y = regions.index(b["reg"])
        for i in sorted(b["pos"]):
            is_knee = (b["reg"], i) == tuple(knee_pos)
            ax.scatter([i], [y], marker="o", s=34 if is_knee else 20, facecolor=INK if is_knee else "white",
                       edgecolor=INK, lw=0.8, zorder=3)
        a0, a1 = min(b["alphas"]), max(b["alphas"])
        lab = f"{a0:g}" if a0 == a1 else f"{a0:g}–{a1:g}"
        if a0 <= knee <= a1:
            lab += " (knee)"
        ax.text(max(b["pos"]) + 0.8, y, lab, fontsize=NOTE, va="center", ha="left", zorder=4)
    ax.scatter([], [], marker="o", s=34, facecolor=INK, edgecolor=INK, lw=0.8, label="knee α")
    ax.scatter([], [], marker="o", s=20, facecolor="white", edgecolor=INK, lw=0.8, label="other α")
    ax.set_yticks(range(len(regions))); ax.set_yticklabels([SHORT[g] for g in regions], fontsize=TICK)
    ax.set_xticks([0, 6, 12, 18]); ax.tick_params(labelsize=TICK)
    ax.set_xlabel("Start offset $i$ (slots)", fontsize=LAB)
    ax.set_xlim(-0.5, 23.5); ax.set_ylim(len(regions) - 0.5, -0.5)
    ax.legend(fontsize=NOTE, frameon=False, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.02),
              handlelength=1.2, columnspacing=1.0, handletextpad=0.4, borderaxespad=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03, ticks=[0, vmax // 2, vmax])
    cb.ax.tick_params(labelsize=NOTE, width=0.6, length=2)
    cb.outline.set_linewidth(0.6)
    cb.set_label("Forecast (gCO₂/kWh)", fontsize=NOTE)
    fig.tight_layout(pad=0.3)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "v2_fig4_slot" + e))
    print("wrote v2_fig4_slot — 작업", job, "무릎점 α", knee, "띠",
          [(SHORT[b["reg"]], sorted(b["pos"]), f"{min(b['alphas']):g}–{max(b['alphas']):g}") for b in bands])


if __name__ == "__main__":
    main()
