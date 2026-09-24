# -*- coding: utf-8 -*-
"""그림 8 — 다섯 방식의 총 배출량 (2026-09-24 재설계, 그림 번호는 §4.3 순서 기준).

사용자 지적: "위의 그림 너무 그 슬래시랑, 점점 되어있는 그래프가 너무 별로인데?"

이전 판의 문제
  · 막대 채움이 다섯 가지였다(흰색·빗금·점·검정·점선테두리). 채움이 무엇을 뜻하는지
    범례도 없어서, 다섯 가지 무늬가 아무 정보도 나르지 않고 눈만 어지럽혔다.
  · (a) 전체와 (b) 확대가 **같은 자료를 두 번** 그렸다. (b)는 (a)에서 ①만 뺀 것이다.
  · 세로로 길어 단내에서 자리를 많이 먹었다.

이 판
  · 한 패널. x축을 로그로 두면 29,225 와 9,958 이 한 그림에 들어간다 — 확대판이 필요 없다.
  · 채움은 두 가지뿐. **본 연구(④)만 채우고 나머지는 비운다.** 참고 문헌들(Sukprasert
    Fig.5b 등)이 쓰는 관례와 같다 — 강조는 하나에만.
  · 실현 불가능한 반사실(③)은 테두리를 점선으로 두어 "달성한 값이 아니다"를 표시한다.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from palette import INK, EXCEPT_GRAY  # 2026-09-24: 그림 전체 공용 회색 팔레트(palette.py)

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({
    "axes.unicode_minus": False, "axes.linewidth": 0.8,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
})

LIGHT = "#cccccc"  # 눈금선용 — 팔레트 대상 아님(정상/예외를 나타내는 회색이 아니다)

# (라벨, kg, 절감률, 본 연구인가, 실현 가능한가)
ROWS = [
    ("① 홈 리전 즉시 실행",        29225.6,  None, False, True),
    ("② 탄소 인지 공간 이동",      12609.8, 56.85, False, True),
    ("③′ 용량 사후 강제",          11873.0, 59.37, False, True),
    ("④ 온라인 용량 인지 (본 연구)", 10805.0, 63.03, True,  True),
    ("③ 무제약 반사실 상한",        9958.2, 65.93, False, False),
]


def main():
    fig, ax = plt.subplots(figsize=(215 / 72.0, 132 / 72.0), dpi=300)
    ys = range(len(ROWS))[::-1]
    for y, (lab, kg, pct, ours, feas) in zip(ys, ROWS):
        # 흑백에서 계열 구분은 무늬가 아니라 회색 농담으로 한다.
        # 본 연구는 검정, 실현 가능한 대조군은 흰색, 실현 불가능한 반사실은 회색
        # (2026-09-24 b6 배분: "정상 대비 예외" 단계 EXCEPT_GRAY — 그림 7의 상한
        # 도달과 같은 단계다. 예전엔 #bfbfbf였다).
        fc = INK if ours else ("white" if feas else EXCEPT_GRAY)
        ax.barh(y, kg, height=0.62, facecolor=fc, edgecolor=INK,
                linewidth=0.9, zorder=3)
        txt = f"{kg:,.0f}" + (f"  ({pct:.2f}%)" if pct else "")
        # 본 연구 값을 가리키는 세로 점선이 ③행 라벨의 첫 글자를 가로지른다.
        # 글자 뒤에 흰 바탕을 깔아 어느 막대에서든 선이 글자를 뚫지 않게 한다.
        ax.text(kg * 1.06, y, txt, va="center", fontsize=6.0,
                fontweight="bold" if ours else "normal", zorder=4,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.8))

    ax.axvline(10805.0, color=INK, lw=0.7, ls=(0, (1, 1.6)), zorder=2)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in ROWS], fontsize=6.4)
    for t, r in zip(ax.get_yticklabels(), ROWS):
        if r[3]:
            t.set_fontweight("bold")
    ax.set_xscale("log")
    ax.set_xlim(8200, 62000)
    ax.set_xticks([10000, 20000, 30000])
    ax.set_xticklabels(["10,000", "20,000", "30,000"], fontsize=6.5)
    # 로그축 부눈금이 "4x10^4" 같은 라벨을 덧붙여 축을 어지럽힌다 — 끈다
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.tick_params(axis="x", which="minor", length=1.6)
    ax.set_xlabel("총 배출량 (kg, 로그 눈금)", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(axis="x", color=LIGHT, lw=0.45, zorder=0)
    ax.set_axisbelow(True)
    # 2026-09-24 b6 배분(그림 10장 통합 점검): 이 각주 한 줄이 캡션("회색 막대(③)는
    # 용량 제약을 전혀 두지 않은 반사실이라 달성 가능한 값이 아니다")과 토씨까지
    # 같았다 — 뺀다. 이 그림엔 그 말고 다른 각주가 없어 그림 아래 여백이 그만큼 준다.
    fig.tight_layout(rect=(0, 0.03, 1, 1), pad=0.35)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig5_comparison" + e))
    print("wrote fig5_comparison")


if __name__ == "__main__":
    main()
