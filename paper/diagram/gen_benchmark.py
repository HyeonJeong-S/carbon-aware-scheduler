# -*- coding: utf-8 -*-
"""그림 B — 탄소 절감 대 용량 위반. 선행 정책 재현 결과를 한 평면에 놓는다.

이 그림의 요지: **절감률만 보면 선행 방식이 이긴다.** 같은 평면에 용량 위반을
같이 그리면 그 절감이 무엇을 대가로 얻어졌는지 보인다. 왼쪽 위(적은 위반 ·
큰 절감)가 좋은 자리다.

데이터는 scheduler/prior_harness.py 의 score() 한 함수로만 채점된 값이다
(§5.7 식(16) 회계, 논문 표1을 전건 재현함을 확인).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
INK = "#000000"

# (라벨, 용량위반, 절감률%, 우리 것인가, 라벨 위치)
POINTS = [
    ("CICS",                 0,       13.76, False, (5, -7)),
    ("시간만",                24,      18.60, True,  (5, 1)),
    ("공간만",                0,       56.85, True,  (5, 2)),
    ("CAST",                 227,     63.03, True,  (-4, 5)),
    # "무제약"(표 1 의 ③)은 선행 정책이 아니라 본 연구 자신의 반사실 상한이다.
    # 캡션이 "★ 본 연구, ○ 선행 정책"이라고 했으므로 별로 그려야 맞다(fd 발견).
    ("무제약",                20208,   65.93, True,  (-3, -10)),
    ("Sukprasert 시간",       49356,   67.21, False, (-4, 4)),
    ("CASPER",               69310,   95.28, False, (-4, -11)),
    ("Sukprasert 공간+시간",  120186,  96.61, False, (-4, 4)),
]


def main():
    W_IN, H_IN = 215 / 72.0, 175 / 72.0     # 단내(215pt) — 전단은 자리가 없다
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=300)

    # 위반 0을 로그축에 올리려면 자리를 줘야 한다 — 0.5로 밀고 눈금에 0으로 표기
    def xpos(v):
        return max(v, 0.5)

    ours = [p for p in POINTS if p[3]]
    theirs = [p for p in POINTS if not p[3]]

    # 별표는 학술지 그림에서 드물다. 채운 원과 빈 원으로 구분한다 — 흑백에서
    # 가장 흔하고 확실한 방법이다(Sukprasert 등도 기본 도형만 쓴다).
    ax.scatter([xpos(p[1]) for p in theirs], [p[2] for p in theirs],
               s=24, facecolor="white", edgecolor=INK, lw=1.0, zorder=3)
    ax.scatter([xpos(p[1]) for p in ours], [p[2] for p in ours],
               s=26, facecolor=INK, edgecolor=INK, lw=1.0, zorder=4)

    for lab, v, sav, is_ours, (dx, dy) in POINTS:
        ax.annotate(lab, (xpos(v), sav), textcoords="offset points",
                    xytext=(dx, dy), fontsize=5.6,
                    ha="right" if dx < 0 else "left",
                    fontweight="bold" if is_ours else "normal", linespacing=1.25)

    ax.set_xscale("symlog", linthresh=1.0)
    ax.set_xlim(-0.2, 400000)
    ax.set_ylim(0, 108)
    ax.set_xticks([0, 1, 10, 100, 1000, 10000, 100000])
    # 아라비아 숫자와 한글 단위("100"과 "1천")를 섞으면 읽는 사람이 눈금을
    # 두 번 환산해야 한다(fd 지적). 자릿수를 한 체계로 통일한다.
    ax.set_xticklabels(["0", "1", "10", "$10^2$", "$10^3$", "$10^4$", "$10^5$"],
                       fontsize=6)
    ax.set_xlabel("용량 상한 위반 배정 (건)", fontsize=7)
    ax.set_ylabel("탄소 절감률 (%)", fontsize=7)
    ax.tick_params(labelsize=6)

    # 실현 가능 영역 표시 — 유효 상한을 지키는 쪽
    ax.axvspan(-0.2, 300, color="#f0f0f0", zorder=0)
    ax.annotate("상한을 지키는 영역", (0.9, 101), fontsize=5.4,
                color="#666666", ha="left")

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)

    fig.text(0.02, 0.012,
             "● 본 연구 · ○ 선행 정책 재현. 오른쪽으로 갈수록\n"
             "같은 절감을 더 큰 과부하로 산 것이다.",
             fontsize=5.2, ha="left", linespacing=1.4)

    fig.tight_layout(rect=(0, 0.13, 1, 1), pad=0.4)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig7_benchmark.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))
    print("wrote", out)


if __name__ == "__main__":
    main()
