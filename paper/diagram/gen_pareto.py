# -*- coding: utf-8 -*-
"""그림 4 · 파레토 곡선 — 고정 alpha 스윕 vs 슬롯별 무릎점(auto).

데이터: 정리.txt [17] (2026-09-16, 배정 CSV 7개를 현재 회계로 재계산,
alpha_auto 행이 논문 표2 ②12,609.8kg 과 정확히 일치함을 확인한 표).
숫자를 다시 계산하지 않고 그 표를 그대로 옮긴다 — 이 스크립트는 그림만 만든다.

기존 load_balancer/framework/results/figures/pareto_curve.png 와 데이터는
같다(같은 [17] 표). 색을 뺀 IEEE 흑백 스타일로, fig1~4(gen_figs.py)와 같은
결(단내 215pt, Malgun/Apple SD Gothic Neo/Noto Sans KR, 굵은 표식 없이 얇은 선)로
새로 그린다.

실행: ./.venv/bin/python paper/diagram/gen_pareto.py
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

# 정리.txt [17] 표 그대로 — (라벨, 평균지연 ms, 절감률 %)
POINTS = [
    ("0",    0.0,   0.00),
    ("0.25", 1.5,   11.07),
    ("0.5",  29.5,  46.22),
    ("auto", 36.2,  56.85),
    ("0.75", 62.6,  64.43),
    ("1",    114.4, 65.77),
]
AUTO_IDX = 3


def main():
    xs = [p[1] for p in POINTS]
    ys = [p[2] for p in POINTS]

    # 215pt = 단내(single-column) 폭 — gen_figs.py 관례와 동일, 2.99in @300dpi.
    # 2026-09-21까지 239pt로 잘못 잡혀 있었음(수정).
    W_IN, H_IN = 215 / 72.0, 190 / 72.0
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=300)

    ax.plot(xs, ys, color=INK, lw=1.1, zorder=2)
    ax.scatter(xs, ys, s=14, facecolor=INK, edgecolor=INK, zorder=3)
    ax.scatter([0.0], [0.0], s=26, marker="D", facecolor="white", edgecolor=INK,
               lw=1.1, zorder=4)  # baseline

    # 2026-09-23: 별표를 뺀다. 사용자 지적 — 학술지 그림에서 ★은 거의 쓰지 않는다.
    # 무릎점은 채운 원을 한 겹 키워 두르는 방식(동심원)으로 강조한다.
    ax.scatter([xs[AUTO_IDX]], [ys[AUTO_IDX]], s=62, facecolor="none",
               edgecolor=INK, lw=0.9, zorder=5)

    for i, (lab, x, y) in enumerate(POINTS):
        t = f"α={lab}" if lab != "auto" else "α=auto\n(무릎점)"
        dx, dy = 4, 6
        ha = "left"
        if i == 0:
            dx, dy, ha = 4, -12, "left"
        elif i == AUTO_IDX:
            dx, dy = -4, 8
            ha = "right"
        elif i == len(POINTS) - 1:
            dx, dy, ha = -4, -14, "right"
        elif lab == "0.5":       # 곡선 위로 겹쳐 무릎점 표식을 가렸다 — 왼쪽으로
            dx, dy, ha = -5, 1, "right"
        elif lab == "0.25":      # 같은 이유로 아래쪽 빈 자리로
            dx, dy, ha = 7, -7, "left"
        ax.annotate(t, (x, y), textcoords="offset points", xytext=(dx, dy),
                    fontsize=6.5, ha=ha, linespacing=1.2)

    # 무릎점의 근거 — 인접 구간 한계수익(kg/ms)이 여기서 정점을 찍고 급락한다는
    # 사실을 그림에도 한 줄로 남긴다(본문 서술과 동일 근거, 정리.txt [17]).
    ax.annotate("", xy=(xs[AUTO_IDX], ys[AUTO_IDX]), xytext=(xs[2], ys[2]),
                arrowprops=dict(arrowstyle="-", lw=0.5, color="#999999",
                                 shrinkA=3, shrinkB=3, linestyle=(0, (1, 1.5))))
    mid_x = (xs[2] + xs[AUTO_IDX]) / 2
    mid_y = (ys[2] + ys[AUTO_IDX]) / 2
    # 2026-09-24: 지시선을 뺀다. 라벨을 곡선 아래 먼 곳에 두고 가는 회색 선으로
    # 이으니, 그 선이 데이터 계열처럼 읽혔다(지면 렌더에서 확인). 글자를 강조
    # 구간 바로 아래 빈 자리에 놓아 위치만으로 가리키게 한다.
    ax.text(mid_x - 6, mid_y - 20, "+6.7 ms, -3,108.8 kg\n(464.9 kg/ms, 전 구간 최대)",
            fontsize=6.2, ha="left", va="top", linespacing=1.3, color="#444444")

    ax.set_xlim(-6, 122)
    ax.set_ylim(-4, 74)
    ax.set_xlabel("평균 지연 (ms)", fontsize=8)
    # 2026-09-24 b6 배분(그림 10장 통합 점검): "% vs baseline"이 그림 8·10의
    # "탄소 절감률 (%)"과 표기가 달랐다(같은 ① 기준 비율인데). 맞춘다.
    ax.set_ylabel("탄소 절감률 (%)", fontsize=8)
    ax.tick_params(labelsize=7)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)

    # 2026-09-24 b6 배분(그림 10장 통합 점검): 둘째 줄("α=auto가 탄소 최저가
    # 아니라...")이 캡션("auto는 탄소가 가장 낮은 지점이 아니라... 정점을 찍는
    # 지점이다")과 그대로 겹쳤다 — 뺀다. 마커 범례(첫 줄)는 캡션에 없어 남기고,
    # 캡션에도 없는 수치(α=0.75가 더 낮다는 사실)만 한 줄로 남긴다.
    fig.text(0.02, 0.012,
              "◆ baseline(α=0) · ◎ α=auto(슬롯별 무릎점, 평균 0.508)\n"
              "참고: 배출량은 α=0.75(10,396.5kg)가 더 낮다 — 지연 62.6ms를 더 쓴 대가다.",
              fontsize=6.2, ha="left", linespacing=1.4)

    fig.tight_layout(rect=(0, 0.20, 1, 1), pad=0.5)   # 각주 3줄(6.2pt) 자리
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig4_pareto.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
