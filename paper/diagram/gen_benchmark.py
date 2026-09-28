# -*- coding: utf-8 -*-
"""그림 B — 탄소 절감 대 용량 위반. 선행 정책 재현 결과를 한 평면에 놓는다.

이 그림의 요지: **절감률만 보면 선행 방식이 이긴다.** 같은 평면에 용량 위반을
같이 그리면 그 절감이 무엇을 대가로 얻어졌는지 보인다. 왼쪽 위(적은 위반 ·
큰 절감)가 좋은 자리다.

데이터는 scheduler/prior_harness.py 의 score() 한 함수로만 채점된 값이다
(§5.7 식(16) 회계, 논문 표1을 전건 재현함을 확인).
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from palette import INK, BG_WASH  # 2026-09-24: 그림 전체 공용 회색 팔레트(palette.py)

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

# 2026-09-28(3d 배분, 용어 교차검증): 맨몸 라벨("무제약"·"시간만"·"공간만")이
# 표 2·표 4 어디에도 정의 없이 튀어나와 사용자가 "이게 뭐야"로 지적했다. 표 2·
# 표 4의 심볼(②③⑤)을 라벨 앞에 붙여 어느 표의 어느 행인지 되짚을 수 있게 한다.
# "CAST (ours)"는 사용자 지정 문자열이라 손대지 않고 번호만 앞에 붙인다
# (메모처리_20260924.txt:102, 2026-09-24 — "④를 붙이면 길어진다"는 이유로 한동안
# 번호 없이 뒀으나, 2026-09-28 캡션이 "번호는 표2·표4의 행 번호"라고 밝히면서
# 다른 세 라벨과 결을 맞출 필요가 다시 생겼다. 문자열 자체는 한 글자도 안 바꿨다).
# (라벨, 용량위반, 절감률%, 우리 것인가, 라벨 위치)
POINTS = [
    ("CICS",                 0,       13.76, False, (5, -7)),
    ("⑤ 시간만",              24,      18.60, True,  (5, 1)),
    ("Caspian",              3745,    30.51, False, (5, -8)),
    ("② 공간만",              0,       56.85, True,  (5, 2)),
    # 2026-09-28(3d 배분, 3차·확정): "CAST (ours)" 문자열은 사용자 지정(위 주석)이라
    # 그대로 두고 번호 "④"만 앞에 붙인다 — 문자열을 바꾸는 "④ 전체"안은 사용자
    # 지시를 덮어써서 기각됐다.
    # "④ CAST (ours)"는 "④ 전체"(4자)보다 훨씬 길어(13자) 옛 오프셋(-4)으로는
    # 닫는 괄호가 점선(음영 경계, x=227 세로 점선)에 거의 닿았다(8배 확대로 확인,
    # 간격 1px 미만) — 왼쪽으로 더 민다.
    ("④ CAST (ours)",         227,     63.03, True,  (-9, 5)),
    # "③ 시간 무제약"(표 4의 ③)은 선행 정책이 아니라 본 연구 자신의 반사실 상한이므로
    # 채운 원(본 연구)으로 그린다 — 캡션의 "● 본 연구, ○ 선행 정책"과 맞춘다.
    # 2026-09-28(3d 배분, 400% 재검토): 옛 오프셋(③ -10, Sukprasert 시간 -4)은 둘 다
    # 왼쪽으로 뻗어 "Sukprasert 시간" 글자가 ③ 점 위에 얹히고, ③ 라벨은 y=60 격자선을
    # 관통했다. ③은 점 바로 위(격자선 사이 빈 자리)로, Sukprasert 시간은 제 점 오른쪽
    # (빈 자리)으로 서로 반대 방향으로 벌렸다.
    # 2026-09-28(3d 배분, 2차): 라벨을 표4와 맞춰 "③ 무제약"→"③ 시간 무제약"으로
    # 늘렸다 — 글자가 길어져 오프셋을 다시 확인해야 한다(아래 렌더 확인).
    ("③ 시간 무제약",          20208,   65.93, True,  (-3, 9)),
    ("Sukprasert 시간",       49356,   67.21, False, (5, 4)),
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
                    xytext=(dx, dy), fontsize=6.2,
                    ha="right" if dx < 0 else "left",
                    fontweight="bold" if is_ours else "normal", linespacing=1.25)

    ax.set_xscale("symlog", linthresh=1.0)
    ax.set_xlim(-0.2, 400000)
    ax.set_ylim(0, 108)
    ax.set_xticks([0, 1, 10, 100, 1000, 10000, 100000])
    # 아라비아 숫자와 한글 단위("100"과 "1천")를 섞으면 읽는 사람이 눈금을
    # 두 번 환산해야 한다(fd 지적). 자릿수를 한 체계로 통일한다.
    # 2026-09-25: "1, 10, 10²"처럼 두 표기가 섞여 있었다 — 거듭제곱 하나로 통일.
    ax.set_xticklabels(["0", "$10^0$", "$10^1$", "$10^2$", "$10^3$", "$10^4$", "$10^5$"],
                       fontsize=6)
    ax.set_xlabel("용량 상한 위반 배정 (건)", fontsize=7)
    ax.set_ylabel("탄소 절감률 (%)", fontsize=7)
    ax.tick_params(labelsize=6)

    # 2026-09-24: "상한을 지키는 영역"은 과장이었다 — 이 음영 안에 본 연구의
    # 위반 227건이 들어 있다. 본문도 용량을 소프트 제약이라고 밝히므로
    # 그림만 "지킨다"고 말하면 안 된다. 경계값을 그대로 적는다.
    # 2026-09-25: "위반 300건 이하" 음영을 뺐다. 300 에 근거가 없고 본 연구(227)가
    # 딱 들어가는 값이라 유리하게 고른 경계로 읽힐 수 있다(그림 비판 검토).
    # 대신 본 연구 점을 지나는 점선 두 개로 "본 연구보다 위반이 적으면서 더 줄인
    # 영역(왼쪽 위)"을 그대로 보인다 — 그 영역에 점이 없다는 것이 주장이다.
    cast = next(p for p in POINTS if p[0] == "④ CAST (ours)")
    ax.axvline(xpos(cast[1]), color="#888888", lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.axhline(cast[2], color="#888888", lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.fill_between([-0.2, xpos(cast[1])], cast[2], 108, color=BG_WASH, zorder=0, lw=0)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)

    # 2026-09-24 b6 배분(그림 10장 통합 점검): 첫 구절("● 본 연구 · ○ 선행 정책
    # 재현")이 캡션("● 본 연구, ○ 선행 정책")과 겹쳤다 — 뺀다. 나머지 읽는 법은
    # 캡션에 없어 남긴다.
    # 2026-09-25: 그림 아래 각주("왼쪽 위가 좋은 자리다")는 캡션으로 옮겼다.
    fig.tight_layout(pad=0.4)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig7_benchmark.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))
    print("wrote", out)


if __name__ == "__main__":
    main()
