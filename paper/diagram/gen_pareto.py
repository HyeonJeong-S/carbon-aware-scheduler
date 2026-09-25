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

    # 2026-09-25: 곡선은 고정 α 점만 잇는다. auto 는 슬롯마다 α 가 바뀌는 다른 정책이라
    # 고정 α 곡선 위의 점이 아니다 — 한 선으로 이으면 "0.5 와 0.75 사이의 어떤 고정값"처럼
    # 읽힌다(그림 비판 검토에서 지적). auto 는 아래에서 과녁 표식으로 따로 찍는다.
    fx = [p[1] for i, p in enumerate(POINTS) if i != AUTO_IDX]
    fy = [p[2] for i, p in enumerate(POINTS) if i != AUTO_IDX]
    ax.plot(fx, fy, color=INK, lw=1.1, zorder=2)
    ax.scatter(fx, fy, s=14, facecolor=INK, edgecolor=INK, zorder=3)
    ax.scatter([0.0], [0.0], s=26, marker="D", facecolor="white", edgecolor=INK,
               lw=1.1, zorder=4)  # baseline

    # 2026-09-23: 별표를 뺀다. 사용자 지적 — 학술지 그림에서 ★은 거의 쓰지 않는다.
    # 무릎점은 채운 원을 한 겹 키워 두르는 방식(동심원)으로 강조한다.
    # 2026-09-24 4c 배분: 사용자가 "무릎점 표식이 안 보인다"고 재지적 — 동심원이
    # s=62/lw=0.9로는 옆 점(s=14)과 거의 구별이 안 됐다(400%에서도 희미했음).
    # 별·땡땡이·빗금 없이 더 키운다: 가운데 채운 점 자체를 다른 점보다 크게
    # 다시 그리고(s=14→34), 두른 원도 더 크고 굵게(62→150, 0.9→1.6) 해
    # 과녁 모양의 대비를 뚜렷하게 낸다.
    ax.scatter([xs[AUTO_IDX]], [ys[AUTO_IDX]], s=34, facecolor=INK,
               edgecolor=INK, zorder=4)
    ax.scatter([xs[AUTO_IDX]], [ys[AUTO_IDX]], s=150, facecolor="none",
               edgecolor=INK, lw=1.6, zorder=5)

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

    # 2026-09-25: "+6.7 ms, -3,108.8 kg" 주석과 α=0.5→auto 점선을 뺐다. 같은 비교
    # (지연 6.7 ms 로 10.64%p 더 줄임)를 본문 3.3절이 이미 말한다 — 그림은 곡선만 보인다.

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
    # 2026-09-24: 둘째 줄("참고: 배출량은 α=0.75가 더 낮다")을 캡션으로 옮겼다.
    # 캡션이 이미 "auto는 탄소가 가장 낮은 지점이 아니다"를 말하고 있어 같은 말을
    # 그림과 캡션이 두 번 했다. 그림에는 **범례만**, 해석은 캡션에 둔다.
    # 2026-09-25: 마커 범례 각주도 뺐다 — 캡션이 "◆는 baseline(α=0), ◎는 무릎점"을
    # 이미 말한다. 그림 안 설명은 캡션으로 모은다.
    fig.tight_layout(pad=0.5)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig4_pareto.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
