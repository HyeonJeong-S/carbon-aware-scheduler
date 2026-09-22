# -*- coding: utf-8 -*-
"""그림 7(신설) · 5개 방식 총배출량 비교 — 표2를 막대로 옮긴 "money figure".

배경(paper/그림개선_브리프.txt): 참고 논문(CarbonFlex Fig.8/9, CASPER Fig.5)은
전부 베이스라인 여러 개를 한 그래프에 놓고 비교하는데, 우리 그림 3~6은 전부
"우리 방법 하나"만 보여준다. 표2에 5개 방식 수치가 있는데 그림으로는 한 번도
안 보여줬다 — 이 그림이 그 구멍을 메운다.

데이터: paper/CAST.docx 표2(§6.3)를 그대로 옮긴다. 재계산하지 않는다.
  ① 홈 리전 즉시 실행         29,225.6 kg  (기준)
  ② 탄소 인지 공간 이동        12,609.8 kg  (-56.85%)
  ③'용량 사후 강제(② + 시간 이동, 사후 강제)  11,873.0 kg  (-59.37%)
  ④ 온라인 용량 인지(② + 시간 이동, Algorithm 1)  10,805.0 kg  (-63.03%) — 본 연구
  ③ 무제약 반사실 상한(② + 시간 이동, 용량 미강제)  9,958.2 kg  (-65.93%) — 실현 불가

막대 순서는 be 지시대로 "나쁨→좋음"인 ①②③'④③ 순 — 표2 값 자체가 이미 이
순서로 단조 감소하므로 그대로 정렬한 것이며 임의로 재배열하지 않았다.

흑백 인쇄 전제: 해치 패턴으로 계열을 구분한다(그림 자체엔 색을 쓰지 않음).
④(본 연구, 온라인 용량 인지)만 검게 채워 강조하고, ③(반사실 상한)은 점선
테두리 + 옅은 해치로 "참고용, 달성 불가"임을 시각적으로 분리한다.

단내(215pt) 폭, gen_pareto.py/gen_concurrency.py와 같은 톤(Apple SD Gothic
Neo/Malgun Gothic/Noto Sans KR, 잉크색 #000000, 9pt 안팎 글씨).

실행: ./.venv/bin/python paper/diagram/gen_comparison.py
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
BASELINE_KG = 29225.6

# 표2 원문 그대로 (paper/CAST.docx §6.3). 위에서 아래로 "나쁨→좋음" 순서.
# (라벨, kg, 절감률%, 스타일태그)
ROWS = [
    ("① 홈 리전\n즉시 실행",        29225.6, None,   "base"),
    ("② 탄소 인지\n공간 이동",       12609.8, -56.85, "hatch1"),
    ("③′ 용량\n사후 강제",          11873.0, -59.37, "hatch2"),
    ("④ 온라인 용량\n인지(본 연구)", 10805.0, -63.03, "ours"),
    ("③ 무제약\n반사실 상한*",       9958.2,  -65.93, "infeasible"),
]


def style_for(tag, bar):
    if tag == "base":
        bar.set_facecolor("white")
        bar.set_edgecolor(INK)
        bar.set_linewidth(1.0)
    elif tag == "hatch1":
        bar.set_facecolor("white")
        bar.set_edgecolor(INK)
        bar.set_hatch("///")
        bar.set_linewidth(0.9)
    elif tag == "hatch2":
        bar.set_facecolor("white")
        bar.set_edgecolor(INK)
        bar.set_hatch("...")
        bar.set_linewidth(0.9)
    elif tag == "ours":
        bar.set_facecolor(INK)
        bar.set_edgecolor(INK)
        bar.set_linewidth(1.3)
    elif tag == "infeasible":
        bar.set_facecolor("white")
        bar.set_edgecolor(INK)
        bar.set_hatch("///")
        bar.set_linewidth(0.9)
        bar.set_linestyle((0, (3, 1.5)))


def main():
    labels = [r[0] for r in ROWS]
    values = [r[1] for r in ROWS]
    n = len(ROWS)
    ys = list(range(n - 1, -1, -1))  # 맨 위(y=n-1)가 ①, 맨 아래가 ③

    # 215pt = 단내(single-column) 폭 — gen_pareto.py/gen_concurrency.py와 동일.
    W_IN, H_IN = 215 / 72.0, 200 / 72.0
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=300)

    bars = ax.barh(ys, values, height=0.62, zorder=3)
    for (label, kg, pct, tag), bar in zip(ROWS, bars):
        style_for(tag, bar)

    # 막대 끝 값 라벨 — kg과 절감률을 함께. 전부 막대 밖 오른쪽에 둬서
    # 짧은 막대(④,③)에서 글씨가 막대 안으로 밀려 y축 라벨과 겹치는 걸 막는다
    # (첫 시도에서 ④를 막대 안쪽에 흰 글씨로 넣었더니 라벨과 충돌해 수정함).
    for y, (label, kg, pct, tag) in zip(ys, ROWS):
        txt = f"{kg:,.1f} kg" if pct is None else f"{kg:,.1f} kg ({pct:.2f}%)"
        weight = "bold" if tag == "ours" else "normal"
        ax.annotate(txt, (kg, y), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=6.3, color=INK,
                    fontweight=weight, zorder=4)

    # ④(본 연구) 값에 세로 기준선을 그어, ①②③'이 이 선을 얼마나 넘어서는지와
    # ③(상한)이 이 선에 얼마나 더 가까운지를 한눈에 비교하게 한다 — 막대
    # 길이만으로는 잘 안 보이는 "④ 기준 초과분"을 시각적으로 강조하는 2차 개선.
    ours_kg = ROWS[3][1]
    ax.axvline(ours_kg, color="#999999", lw=0.7, ls=(0, (2, 2)), zorder=1)
    ax.annotate("④ 기준", (ours_kg, n - 0.35), xytext=(3, 0),
                textcoords="offset points", ha="left", va="top", fontsize=5.6,
                color="#666666", rotation=90)

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=6.8, linespacing=1.15)
    ax.set_xlabel("총 배출량 (kg)", fontsize=7.8)
    ax.set_xlim(0, BASELINE_KG * 1.34)
    ax.tick_params(axis="x", labelsize=6.8)
    ax.tick_params(axis="y", length=0)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.7)
    ax.grid(axis="x", color="#dddddd", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # ④(본 연구)를 y축 라벨에서도 한 번 더 강조 — 굵게.
    for tick, (label, kg, pct, tag) in zip(ax.get_yticklabels(), ROWS):
        if tag == "ours":
            tick.set_fontweight("bold")

    fig.text(0.02, 0.012,
              "* ③은 배치 뒤 용량을 사후적으로만 강제하는 조건의 반사실 상한 —\n"
              "실제로는 동시 실행이 상한의 3.4배까지 몰려 실현 불가하다(§6.4).\n"
              "④가 두 경계(①의 손해, ③의 이상치) 사이에서 실제 달성한 값이다.",
              fontsize=5.1, ha="left", linespacing=1.35)

    fig.tight_layout(rect=(0, 0.135, 1, 1), pad=0.5)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig7_comparison.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
