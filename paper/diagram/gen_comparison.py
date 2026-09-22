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


def draw_panel(ax, rows, xlim, show_ylabels=True, panel_tag=""):
    n = len(rows)
    ys = list(range(n - 1, -1, -1))
    ours_kg = next(kg for _, kg, _, tag in rows if tag == "ours")

    bars = ax.barh(ys, [r[1] for r in rows], height=0.62, zorder=3)
    for (label, kg, pct, tag), bar in zip(rows, bars):
        style_for(tag, bar)

    # 막대 끝 값 라벨 — kg과 절감률을 함께. 전부 막대 밖 오른쪽에 둬서
    # 짧은 막대(④,③)에서 글씨가 막대 안으로 밀려 y축 라벨과 겹치는 걸 막는다
    # (첫 시도에서 ④를 막대 안쪽에 흰 글씨로 넣었더니 라벨과 충돌해 수정함).
    # (b)에서는 ④ 기준선(점선)이 ③ 막대 라벨과 겹칠 만큼 가까워서, 라벨에
    # 흰 배경 박스를 깔아 선이 글자를 가로질러도 가독성이 떨어지지 않게 한다
    # (gen_concurrency.py의 "상한 12" 라벨과 같은 처리).
    for y, (label, kg, pct, tag) in zip(ys, rows):
        txt = f"{kg:,.1f} kg" if pct is None else f"{kg:,.1f} kg ({pct:.2f}%)"
        weight = "bold" if tag == "ours" else "normal"
        ax.annotate(txt, (kg, y), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=6.1, color=INK,
                    fontweight=weight, zorder=5,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.6))

    # ④(본 연구) 값에 세로 기준선 — ①②③'이 이 선을 얼마나 넘어서는지,
    # ③(상한)이 이 선에 얼마나 더 가까운지를 두 패널 모두에서 같은 기준으로 본다.
    ax.axvline(ours_kg, color="#999999", lw=0.7, ls=(0, (2, 2)), zorder=1)

    ax.set_yticks(ys)
    if show_ylabels:
        ax.set_yticklabels([r[0] for r in rows], fontsize=6.6, linespacing=1.1)
        for tick, (label, kg, pct, tag) in zip(ax.get_yticklabels(), rows):
            if tag == "ours":
                tick.set_fontweight("bold")
    else:
        ax.set_yticklabels([])
    ax.set_xlim(*xlim)
    ax.tick_params(axis="x", labelsize=6.4)
    ax.tick_params(axis="y", length=0)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.7)
    ax.grid(axis="x", color="#dddddd", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if panel_tag:
        ax.text(0.0, 1.06, panel_tag, transform=ax.transAxes, fontsize=7.5,
                 fontweight="bold", ha="left", va="bottom")


def main():
    # be 2차 리뷰(2026-09-22) 반영: ①이 축을 지배해 ②③'④③(9,958~12,609)의
    # 차이가 안 보인다는 지적 — (a)전체 5개 (b)①을 뺀 나머지 4개를 x축
    # 확대해서 아래에 붙인다(CASPER Fig.5/CarbonFlex Fig.9의 서브패널 방식).
    zoom_rows = ROWS[1:]  # ②③'④③
    zoom_vals = [r[1] for r in zoom_rows]
    zoom_lo, zoom_hi = min(zoom_vals), max(zoom_vals)
    zoom_pad = (zoom_hi - zoom_lo) * 0.28
    zoom_xlim = (zoom_lo - zoom_pad, zoom_hi + zoom_pad * 2.1)

    # 215pt = 단내(single-column) 폭. 세로로 (a)(b) 쌓음 — 가로로 놓으면
    # 막대 5개짜리 (a)가 너무 좁아져 라벨이 안 들어가서 세로를 택했다.
    W_IN, H_IN = 215 / 72.0, 330 / 72.0
    fig, (axa, axb) = plt.subplots(
        2, 1, figsize=(W_IN, H_IN), dpi=300,
        gridspec_kw=dict(height_ratios=[5, 4.2]))

    draw_panel(axa, ROWS, xlim=(0, BASELINE_KG * 1.34), panel_tag="(a) 다섯 방식 전체")
    draw_panel(axb, zoom_rows, xlim=zoom_xlim, panel_tag="(b) ① 제외, x축 확대")

    axa.set_xlabel("")
    axb.set_xlabel("총 배출량 (kg)", fontsize=7.6)

    fig.text(0.02, 0.012,
              "* ③은 용량 제약을 전혀 적용하지 않은 반사실 상한 — 동시 실행이\n"
              "상한의 3.4배까지 몰려 실현 불가하다(§6.4). ④가 두 경계(①의 손해,\n"
              "③의 이상치) 사이에서 실제 달성한 값이다. (b)의 점선은 ④ 값이다.",
              fontsize=5.0, ha="left", linespacing=1.35)

    fig.tight_layout(rect=(0, 0.115, 1, 0.985), h_pad=1.8)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig7_comparison.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
