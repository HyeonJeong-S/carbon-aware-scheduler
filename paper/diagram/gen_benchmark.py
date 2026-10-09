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
# 2026-09-28(3): 동그라미 번호를 뺐다 — 사용자 지적 "단계를 묶을 거면 잘 묶던가,
# 표에 넣을 때 너무 보기 어렵다". ①~⑤ 가 논리 순서와 어긋나게 매겨져 있었고
# (반사실 ③ 이 본 연구 ④ 보다 앞 번호), 표 2·표 4·그림 8·그림 10 이 같은 것을
# 서로 다른 이름으로 불렀다. 이제 여섯 이름만 쓴다 — 기준 · 공간만 · 시간만 ·
# 시간 무제약 · 사후 용량 강제 · CAST. 본문의 번호 5회도 함께 없앴다.
# (라벨, 용량위반, 절감률%, 우리 것인가, 라벨 위치)
POINTS = [
    ("CICS",                 0,       13.76, False, (5, -7)),
    # 2026-10-08(글자 1.099배): Caspian 라벨과 1.4×2.3pt 겹쳤다 — 3pt 내린다.
    ("Temporal-only",       24,      18.60, True,  (5, -2)),
    ("Caspian",              3745,    30.51, False, (5, -8)),
    # 2026-10-08: "CAST (ours)" 를 위 "Capacity ignored" 라벨에서 떼려면 아래로
    # 내려야 하는데, 두 라벨 사이 빈 띠가 1pt 밖에 없었다. CAST 를 끼우는 대신
    # 이 라벨을 8pt 내려 자리를 만든다 — 아래는 Caspian(30.51%)까지 비어 있다.
    ("Spatial-only",        0,       56.85, True,  (5, -6)),
    # 2026-09-28(3d 배분, 3차·확정): "CAST (ours)" 문자열은 사용자 지정(위 주석)이라
    # 그대로 두고 번호 "④"만 앞에 붙인다 — 문자열을 바꾸는 "④ 전체"안은 사용자
    # 지시를 덮어써서 기각됐다.
    # "④ CAST (ours)"는 "④ 전체"(4자)보다 훨씬 길어(13자) 옛 오프셋(-4)으로는
    # 닫는 괄호가 점선(음영 경계, x=227 세로 점선)에 거의 닿았다(8배 확대로 확인,
    # 간격 1px 미만) — 왼쪽으로 더 민다.
    # 2026-10-08: 위 "Capacity ignored" 라벨(제 점 왼쪽으로 50.8pt 뻗는다)과
    # 가로로 6.8pt 겹쳤다. 왼쪽으로 11pt 더 미는 안(-20)은 Spatial-only 점
    # (x≈39)에 11.4pt 로 가까워져 소속이 뒤집혀 기각했다 — 가로가 아니라 세로로
    # 뗀다. 5pt 내리면 위 라벨 아래끝(50.6)과 3.8pt 떨어지고 제 점이 그대로
    # 가장 가깝다(9.0pt).
    ("CAST (ours)",         227,     63.03, True,  (-9, 0)),
    # "③ 시간 무제약"(표 4의 ③)은 선행 정책이 아니라 본 연구 자신의 반사실 상한이므로
    # 채운 원(본 연구)으로 그린다 — 캡션의 "● 본 연구, ○ 선행 정책"과 맞춘다.
    # 2026-09-28(3d 배분, 400% 재검토): 옛 오프셋(③ -10, Sukprasert 시간 -4)은 둘 다
    # 왼쪽으로 뻗어 "Sukprasert 시간" 글자가 ③ 점 위에 얹히고, ③ 라벨은 y=60 격자선을
    # 관통했다. ③은 점 바로 위(격자선 사이 빈 자리)로, Sukprasert 시간은 제 점 오른쪽
    # (빈 자리)으로 서로 반대 방향으로 벌렸다.
    # 2026-09-28(3d 배분, 2차): 라벨을 표4와 맞춰 "③ 무제약"→"③ 시간 무제약"으로
    # 늘렸다 — 글자가 길어져 오프셋을 다시 확인해야 한다(아래 렌더 확인).
    # 2026-10-08(70 지적, 2차): 되돌린 뒤에도 틀렸다. ** 재는 기준이 갈렸다 ** —
    # 나는 라벨 **가장자리**에서, 70 은 라벨 **중심**에서 쟀다. 왼쪽으로 50.8pt
    # 뻗는 긴 라벨은 오른쪽 끝이 제 점에 닿아도 중심은 옆 점 위에 온다
    # (가장자리 8.0 대 11.1 로 통과, 중심 30.8 대 18.3 으로 탈락).
    # 이 그림은 라벨이 점 왼쪽·오른쪽에 섞여 붙어 규약으로 못 가르므로, 두 기준이
    # 모두 통과하는 자리를 찾는 게 맞다 — 제 점 **바로 아래 가운데맞춤**이 답이다
    # (가장자리 5.7 대 7.4, 중심 10.2 대 14.0). 쓸기로 확인했다.
    ("Capacity ignored",    20208,   65.93, True,  (0, -13)),
    ("Sukprasert temporal",   49356,   67.21, False, (5, 4)),
    # 2026-10-08: 이 점과 Sukprasert 공간+시간 점이 거의 겹쳐 있어 거리로는
    # 소속을 못 가른다(4.4 대 4.8pt). 아래쪽 규약을 분명히 하려고 더 내린다.
    ("CASPER",               69310,   95.28, False, (-4, -16)),
    ("Sukprasert spatial+temporal", 120186, 96.61, False, (-4, 4)),
]


def main():
    W_IN, H_IN = 215 / 72.0, 175 / 72.0     # 단내(215pt) — 전단은 자리가 없다
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=500)

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
                    xytext=(dx, dy), fontsize=6.8,
                    # dx=0 은 "제 점 바로 위/아래 가운데맞춤" — 수직선이 곧 소속을 말한다
                    ha="center" if dx == 0 else ("right" if dx < 0 else "left"),
                    fontweight="bold" if is_ours else "normal", linespacing=1.25)

    ax.set_xscale("symlog", linthresh=1.0)
    ax.set_xlim(-0.2, 400000)
    ax.set_ylim(0, 108)
    ax.set_xticks([0, 1, 10, 100, 1000, 10000, 100000])
    # 아라비아 숫자와 한글 단위("100"과 "1천")를 섞으면 읽는 사람이 눈금을
    # 두 번 환산해야 한다(fd 지적). 자릿수를 한 체계로 통일한다.
    # 2026-09-25: "1, 10, 10²"처럼 두 표기가 섞여 있었다 — 거듭제곱 하나로 통일.
    # 2026-10-08(글자 1.099배): 거듭제곱 표기는 matplotlib 이 지수를 밑글자의 0.7배로
    # 찍는다 — 눈금 글자를 아무리 키워도 지수는 그 0.7배다. 단에 넣으면 4.20pt 로
    # 5d 가 잰 JOK 실물 하한(5.7~5.9pt)의 절반 수준이다. 평문 자릿수로 바꾸면
    # 모든 눈금이 6.00pt 로 찍히고 겹침도 없다(쓸기로 확인).
    # 2026-09-25 의 "거듭제곱 하나로 통일" 결정은 "1, 10, 10²" 처럼 두 표기가
    # 섞인 것을 없애려던 것이므로, 평문 하나로 통일하는 것도 그 뜻에 맞는다.
    # 2026-10-08(글자 1.099배): 거듭제곱 표기는 matplotlib 이 지수를 밑글자의 0.7배로
    # 찍는다 — 눈금을 키워도 지수는 그 0.7배다. 단에 넣으면 4.20pt 로, 5d 가 잰 JOK
    # 실물 하한(5.7~5.9pt)의 절반 수준이라 어떤 크기로도 못 맞춘다.
    # 평문 자릿수로 바꾸면 전부 6.00pt 로 찍힌다. 다만 일곱 자리를 다 적으면
    # "10,000" 과 "100,000" 이 맞닿으므로(간격 17.5pt < 글자폭 22pt) 두 자릿수
    # 걸러 적는다 — 눈금선은 일곱 개 그대로다.
    # 2026-09-25 의 "거듭제곱 하나로 통일" 결정은 "1, 10, 10²" 처럼 두 표기가
    # 섞인 것을 없애려던 것이므로, 평문 하나로 통일하는 것도 그 뜻에 맞는다.
    ax.set_xticklabels(["0", "", "10", "", "1,000", "", "100,000"],
                       fontsize=6.6)
    ax.set_xlabel("Ceiling violations (jobs)", fontsize=7.7)
    ax.set_ylabel("Carbon savings (%)", fontsize=7.7)
    ax.tick_params(labelsize=6.6)

    # 2026-09-24: "상한을 지키는 영역"은 과장이었다 — 이 음영 안에 본 연구의
    # 위반 227건이 들어 있다. 본문도 용량을 소프트 제약이라고 밝히므로
    # 그림만 "지킨다"고 말하면 안 된다. 경계값을 그대로 적는다.
    # 2026-09-25: "위반 300건 이하" 음영을 뺐다. 300 에 근거가 없고 본 연구(227)가
    # 딱 들어가는 값이라 유리하게 고른 경계로 읽힐 수 있다(그림 비판 검토).
    # 대신 본 연구 점을 지나는 점선 두 개로 "본 연구보다 위반이 적으면서 더 줄인
    # 영역(왼쪽 위)"을 그대로 보인다 — 그 영역에 점이 없다는 것이 주장이다.
    # 2026-09-28(3): 라벨에서 번호를 뺐으므로 여기 이름도 함께 바꿨다.
    # 위 주석들의 "④ …" 표기는 그때의 이력이고 현재 라벨이 아니다.
    cast = next(p for p in POINTS if p[0] == "CAST (ours)")
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
