# -*- coding: utf-8 -*-
"""그림 4 — 공간 이동이 실제로 만든 리전 간 흐름 (2026-09-24 신설).

사용자: "공간이동은 다른 논문들이 공간이동을 하는 그런 아키텍처를 따와서 그리는 게
낫지 않아??"  참고 문헌(CASPER Fig.3a 'CAS Balancing')은 리전을 두 줄로 놓고 출발
리전에서 도착 리전으로 화살표를 그어 재배치를 보인다. 그 관례를 따르되, 도식이
아니라 **실측 배정 행렬**을 그린다 — 우리에게는 146,000건이 실제로 어디로 갔는지가
있으므로 개념도를 그릴 이유가 없다.

자료: load_balancer/framework/results/summary.json 의 alpha_auto.routing_matrix
      (8×8, 합 146,000). 무릎점 자동 선택으로 돌린 1년치 결과다.

읽는 법: 위가 출발, 아래가 도착. 선 굵기가 건수이고, 홈에 남은 몫은 굵은 세로선이다.
        프랑스와 캘리포니아로 몰리고 인도는 거의 비는 것이 한눈에 보인다.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler")
from interface.regions import REGIONS, REGION_LABELS

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
SUM = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/load_balancer/framework/results/summary.json"
INK, GRAY = "#000000", "#999999"
SHORT = {"US-CAL-CISO": "캘리포니아", "US-TEX-ERCO": "텍사스", "US-NY-NYIS": "뉴욕",
         "FR": "프랑스", "DE": "독일", "KR": "한국", "IN": "인도", "JP": "일본"}


def main():
    M = np.array(json.load(open(SUM))["alpha_auto"]["routing_matrix"], dtype=float)
    n = len(REGIONS)
    tot = M.sum()
    recv = M.sum(axis=0)

    fig, ax = plt.subplots(figsize=(215 / 72.0, 132 / 72.0), dpi=300)
    xs = np.arange(n)
    yt, yb = 1.0, 0.0

    # 이동한 몫만 곡선으로 — 홈에 남은 것(대각)은 따로 표시한다
    mx = M[~np.eye(n, dtype=bool)].max()
    for i in range(n):
        for j in range(n):
            if i == j or M[i, j] < 400:          # 400건 미만은 선이 보이지도 않는다
                continue
            lw = 0.25 + 2.3 * (M[i, j] / mx)
            ax.plot([xs[i], xs[j]], [yt, yb], color=INK, lw=lw,
                    alpha=0.55, solid_capstyle="round", zorder=2)

    # 홈 유지분 — 세로 막대
    for i in range(n):
        keep = M[i, i]
        if keep <= 0:
            continue
        ax.plot([xs[i], xs[i]], [yt, yb], color=GRAY,
                lw=0.25 + 2.3 * (keep / mx), alpha=0.9, zorder=1)

    # 도착 리전 — 받은 양에 비례한 사각형
    for j in range(n):
        h = 0.055 + 0.20 * (recv[j] / recv.max())
        ax.add_patch(plt.Rectangle((xs[j] - 0.34, yb - h), 0.68, h,
                                   facecolor=INK if recv[j] > tot * 0.2 else "white",
                                   edgecolor=INK, lw=0.8, zorder=4))
        # 2026-09-24: 라벨을 상자마다 다른 높이에 두니 키 큰 상자에서는 글자가
        # 상자 아래 테두리에 얹혔고, 검은 상자에서는 검은 글자가 묻혔다(지면 확인).
        # 가장 큰 상자보다 아래의 한 줄에 모두 맞춘다 — 열 위치가 상자를 가리킨다.
        ax.text(xs[j], yb - 0.255 - 0.05, f"{recv[j]/tot*100:.0f}%", ha="center",
                va="top", fontsize=6.2,
                fontweight="bold" if recv[j] > tot * 0.2 else "normal")

    for i in range(n):
        ax.add_patch(plt.Rectangle((xs[i] - 0.34, yt), 0.68, 0.055,
                                   facecolor="white", edgecolor=INK, lw=0.8, zorder=4))
        ax.text(xs[i], yt + 0.11, SHORT[REGIONS[i]], ha="left", fontsize=6.2,
                rotation=32, rotation_mode="anchor")

    ax.text(-0.85, yt + 0.02, "출발", fontsize=6.2, ha="right", va="bottom")
    ax.text(-0.85, yb - 0.02, "도착", fontsize=6.2, ha="right", va="top")
    ax.set_xlim(-1.15, n + 0.15)
    ax.set_ylim(-0.46, 1.62)
    ax.axis("off")
    # 2026-09-24 b6 배분(그림 10장 통합 점검): "선 굵기 = 옮긴 작업 수"는 캡션
    # ("선 굵기가 옮긴 작업 수다")과 그대로 겹쳤다 — 뺀다. 회색 세로선·아래
    # 사각형의 뜻은 캡션에 없어 남긴다.
    fig.text(0.015, 0.012,
             "400건 미만은 선을 생략함 · 회색 세로선 = 홈에 남은 몫\n"
             "아래 사각형 = 리전이 받은 비율",
             fontsize=6.2)
    fig.tight_layout(rect=(0, 0.105, 1, 1), pad=0.3)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig4_routing" + e))
    print("wrote fig4_routing — 프랑스 %.1f%%, 캘리포니아 %.1f%%, 인도 %.1f%%"
          % (recv[3] / tot * 100, recv[0] / tot * 100, recv[6] / tot * 100))


if __name__ == "__main__":
    main()
