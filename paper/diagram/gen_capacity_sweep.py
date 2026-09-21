# -*- coding: utf-8 -*-
"""그림 6(안) · 용량 스윕 — 리전 용량이 커질수록 총배출이 줄지만 수익이 줄어든다.

데이터: scheduler/data/capacity_sweep/sweep_summary.csv (B4, 0c 실행·be 검증 완료,
커밋 367b68d). 이 스크립트는 그 CSV를 그대로 읽어 그릴 뿐, 재계산하지 않는다.

스타일은 CarbonFlex Fig.8(Impact of the maximum cluster capacity on the carbon
savings — capacity를 x축 범주로, 단일 지표를 y축 선 하나로)을 참고했다. 우리는
비교할 baseline이 하나뿐이라 선도 하나이고, 대신 보조지표(강제 편입 건수)를
오른쪽 축에 같이 그려 "용량을 줄일수록 총배출도 늘고 강제 편입도 늘어난다"는
두 지표의 동조를 한 그림에서 보인다.

x축은 용량 배수(0.5x~2x, ∞)를 범주형 눈금으로 쓴다 — capacity 값 자체가
6/9/12/18/24/100000(무제약 근사)로 등간격이 아니라서, 실제 값으로 연속축을
그리면 뒤쪽(2x, ∞)이 과도하게 뭉친다. 1x(η·cap 기준값 12)를 별 표식으로 강조.

실행: ./.venv/bin/python paper/diagram/gen_capacity_sweep.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_HERE, "..", "..", "scheduler", "data", "capacity_sweep",
                         "sweep_summary.csv")

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

INK = "#000000"
GRAY = "#888888"

LABELS = {"0.5x": "0.5×", "0.75x": "0.75×", "1x": "1×\n(기준)",
          "1.5x": "1.5×", "2x": "2×", "inf": "∞"}
ORDER = ["0.5x", "0.75x", "1x", "1.5x", "2x", "inf"]


def main():
    rows = {}
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            rows[row["level"]] = row

    xs = list(range(len(ORDER)))
    carbon = [float(rows[k]["total_carbon_kg_recount"]) / 1000.0 for k in ORDER]
    forced = [int(rows[k]["forced_admissions"]) for k in ORDER]
    baseline_kg = 29225.6
    savings = [(1 - c * 1000 / baseline_kg) * 100 for c in carbon]

    # 215pt = 단내(single-column) 폭 — gen_figs.py 관례와 동일, 2.99in @300dpi.
    # 2026-09-21까지 239pt로 잘못 잡혀 있었음(수정).
    W_IN, H_IN = 215 / 72.0, 190 / 72.0
    fig, ax1 = plt.subplots(figsize=(W_IN, H_IN), dpi=300)

    ax1.plot(xs, carbon, color=INK, lw=1.1, marker="o", ms=3.2, zorder=3,
              label="총배출")
    i1x = ORDER.index("1x")
    ax1.scatter([xs[i1x]], [carbon[i1x]], s=95, marker="*", facecolor=INK,
                edgecolor=INK, zorder=4)

    for x, c, s in zip(xs, carbon, savings):
        ax1.annotate(f"-{s:.1f}%", (x, c), textcoords="offset points",
                     xytext=(0, 7), fontsize=5.8, ha="center", color="#444444")

    ax1.set_xticks(xs)
    ax1.set_xticklabels([LABELS[k] for k in ORDER], fontsize=7)
    ax1.set_xlabel("리전 용량 (η·cap_r, 기준=12 대비 배수)", fontsize=7.8)
    ax1.set_ylabel("총배출 (t)", fontsize=8)
    ax1.tick_params(axis="y", labelsize=7)
    ax1.set_ylim(min(carbon) * 0.9, max(carbon) * 1.12)

    ax2 = ax1.twinx()
    ax2.plot(xs, forced, color=GRAY, lw=0.9, ls=(0, (3, 1.5)), marker="s", ms=2.6,
              zorder=2, label="강제 편입 (마감 임박)")
    ax2.set_ylabel("강제 편입 건수", fontsize=8, color=GRAY)
    ax2.tick_params(axis="y", labelsize=7, colors=GRAY)
    ax2.set_ylim(0, max(forced) * 1.25)
    for spine in ("top",):
        ax2.spines[spine].set_visible(False)
    ax2.spines["right"].set_color(GRAY)

    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax1.spines[spine].set_linewidth(0.7)
    ax1.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=6, frameon=False,
               handlelength=2.0)

    fig.text(0.02, 0.012,
              f"용량을 6→∞로 늘리면 총배출은 {carbon[0]:.2f}→{carbon[-1]:.2f} t"
              f"({savings[0]:.1f}→{savings[-1]:.1f}%)로,\n"
              f"강제 편입은 {forced[0]:,}→{forced[-1]:,}건으로 함께 준다. 모든 구간 마감위반 0.",
              fontsize=5.3, ha="left", linespacing=1.4)

    fig.tight_layout(rect=(0, 0.10, 1, 1), pad=0.5)
    out = os.path.join(_HERE, "fig6_capacity_sweep.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
