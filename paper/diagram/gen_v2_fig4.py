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
LAB, TICK, NOTE = 8.2, 7.1, 7.1
# 10-18(82 점검4 E [4]): NOTE 6.6 → 7.1. 215 pt 설계가 단폭 195.6 pt 에 0.91배로 들어가 칸 라벨이 인쇄 6.0 pt(대문자 높이로 5.8)였다.
SHORT = {"US-CAL-CISO": "California", "US-TEX-ERCO": "Texas", "US-NY-NYIS": "New York", "FR": "France",
         "DE": "Germany", "KR": "Korea", "IN": "India", "JP": "Japan"}


DASH = object()   # 엔대시 자리표


def label_parts(ax, x, y, parts):
    """글자 조각을 기준선에 맞춰 이어 붙인다. DASH 자리만 Helvetica 엔대시."""
    from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
    kids = [TextArea("–" if q is DASH else q, textprops=dict(fontsize=NOTE, **({"family": "Helvetica"} if q is DASH else {})))
            for q in parts]
    box = HPacker(children=kids, align="baseline", pad=0, sep=0.4)
    ab = AnnotationBbox(box, (x, y), xycoords="data", box_alignment=(0, 0.5), frameon=False, pad=0, zorder=4)
    ax.add_artist(ab)


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
    # 10-18(84 점검3 [2]): 흰색 → #8c8c8c 로는 눈금 600 도 중간 회색이라 한 행 안의 차이가 인쇄에서 안 보였다 →
    # 흰색 → 진회색 #333333(0.2)으로 넓혔다. vmax 는 그대로(자료 최댓값 인도 555 를 100 단위로 올린 600 — 눈금 0·300·600).
    cmap = LinearSegmentedColormap.from_list("ink", ["#ffffff", "#333333"])
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
        # 10-18(89 점검 [12]): 표 1 과 같은 표기 — 소수 한 자리(0.0·1.0)와 엔대시. Apple SD Gothic Neo 의 엔대시는
        # 하이픈과 같은 모양이라 대시 한 글자만 Helvetica 로 찍는다(숫자는 그림의 다른 글자와 같은 서체).
        parts = [f"{a0:.1f}"] if a0 == a1 else [f"{a0:.1f}", DASH, f"{a1:.1f}"]
        if a0 <= knee <= a1:
            # 10-18(87 점검2 [9]): "(knee)" 만 붙이면 0.4·0.5 둘 다 무릎점처럼 읽혔다 — 무릎점 α 를 밝힌다
            parts[-1] += f" (knee at {knee:.1f})" if a0 != a1 else " (knee)"
        # 10-18(84 점검3 [2]): 색만으로는 한국 352 → 329(7%)처럼 작은 차이가 안 보여, 고른 칸의 예측값(gCO₂/kWh, pred_at_slot 그대로)을
        # α 범위 뒤 "·" 다음에 적는다. 칸이 둘이면 왼쪽 칸부터 "58, 80". 렌더: 한국 i=0 라벨("0.0 · 352")이 i=6 ○ 에 닿지 않게
        # 점과 라벨 사이를 0.8 → 0.72 칸으로(0.65 는 PDF 에서 ○ 와 글자 틈 약 1 pt 라 조금 늘림) 줄이고 "·" 양옆은 가는 빈칸(U+2009).
        # 10-18(82 점검4 E [4]): 글자 7.1 pt 로 키우니 "0.0 · 352" 가 i=6 ○ 에 닿았다 → "·" 를 따로 조각으로 떼어 가는 빈칸(U+2009,
        # 이 서체에 없어 대체 서체 폭 약 1.4 pt) 대신 조각 사이 간격(sep 0.4 pt)만 둔다. 라벨이 약 2 pt 짧아진다.
        parts += ["·", ", ".join(f"{P[y][i]:.0f}" for i in sorted(b["pos"]))]
        # 무릎점 ●(s 34, 반지름 약 0.52 칸)은 0.65 면 라벨이 닿아 0.8 그대로
        label_parts(ax, max(b["pos"]) + (0.8 if a0 <= knee <= a1 else 0.72), y, parts)
    ax.scatter([], [], marker="o", s=34, facecolor=INK, edgecolor=INK, lw=0.8, label="knee α")
    ax.scatter([], [], marker="o", s=20, facecolor="white", edgecolor=INK, lw=0.8, label="other α")
    ax.set_yticks(range(len(regions))); ax.set_yticklabels([SHORT[g] for g in regions], fontsize=TICK)
    ax.set_xticks([0, 6, 12, 18]); ax.tick_params(labelsize=TICK)
    ax.tick_params(axis="y", length=0, pad=3.5)   # 10-18(87 점검2 [9]): 행 이름 눈금 표식이 i=0 의 ○ 에 닿았다 — 행 이름만으로 충분
    ax.set_xlabel("Start offset $i$ (slots)", fontsize=LAB)
    # 10-18(87 점검2 [9]): i=0 의 ○(France 1.0, Korea 0.0)가 왼쪽 축선·눈금에 걸렸다. 왼쪽만 넓히면 흰 띠가 "0 gCO₂" 칸처럼
    # 읽히므로 네 변 모두 같은 흰 여백(약 2.6 pt: 가로 0.45 칸, 세로 0.2 행)을 두어 액자 여백으로 읽히게 한다. 칸 위치·색은 그대로.
    ax.set_xlim(-0.95, 23.95); ax.set_ylim(len(regions) - 0.3, -0.7)
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
          [(SHORT[b["reg"]], sorted(b["pos"]), f"{min(b['alphas']):.1f}–{max(b['alphas']):.1f}") for b in bands])


if __name__ == "__main__":
    main()
