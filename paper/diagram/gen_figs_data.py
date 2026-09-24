# -*- coding: utf-8 -*-
"""그림 2·3·4 — 실측 자료로 그리는 판 (2026-09-24 전면 재작업).

왜 다시 그리나
-------------
이전 판은 셋 다 "상자와 화살표"였다. 입력 상자와 출력 상자가 면적의 30%를 먹으면서
정보는 0이었고, 곡선에는 눈금이 없어 전부 개념도였다. 1년치 실측 자료를 갖고 있으면서
개념도를 싣는 것은 자료를 버리는 일이다.

서식은 이 분야 논문의 관례를 그대로 따른다(paper/참고 의 그림들을 직접 뜯어 확인).
  · 축은 네 면을 모두 두른다. 위·오른쪽을 지우는 방식은 이 분야에서 쓰지 않는다.
  · 범례는 축 바깥 위쪽에 가로 한 줄, 테두리 없이 둔다.
  · 계열은 색이 아니라 선 모양(실선·파선·일점쇄선)과 빗금으로 구분한다 — 흑백 인쇄 대비.
  · 축 이름은 크게, 여백은 작게. 눈금은 필요한 곳에만.
  · 본 연구에 해당하는 요소만 채우거나 빗금으로 강조한다.

실행: ./.venv/bin/python paper/diagram/gen_figs_data.py
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
from interface import carbon_2025
from interface.regions import REGIONS, REGION_LABELS

# 본문·표와 같은 한글 표기. REGION_LABELS는 영문이라 한국어 논문 그림에 쓰지 않는다.
KO = {"US-CAL-CISO": "캘리포니아", "US-TEX-ERCO": "텍사스", "US-NY-NYIS": "뉴욕",
      "FR": "프랑스", "DE": "독일", "KR": "한국", "IN": "인도", "JP": "일본"}
from load_balancer.framework.config import load_latency_matrix

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({
    "axes.unicode_minus": False,
    "axes.linewidth": 0.8,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "xtick.major.size": 2.6, "ytick.major.size": 2.6,
})

HERE = os.path.dirname(os.path.abspath(__file__))
INK, GRAY, LIGHT = "#000000", "#7a7a7a", "#cccccc"
COL = 215 / 72.0                 # 단내 폭
FULL = 451 / 72.0                # 전단 폭(그림 1·2가 쓰는 구역)
LAB, TICK, NOTE = 7.5, 6.5, 5.6  # 축 이름 / 눈금 / 주석


def legend_above(ax, ncol, y=1.02, fs=NOTE):
    ax.legend(fontsize=fs, frameon=False, ncol=ncol, loc="lower left",
              bbox_to_anchor=(0, y), handlelength=1.7, columnspacing=1.1,
              handletextpad=0.5, borderaxespad=0)


# ═════════════════ 그림 2 · 예측 ═════════════════
def fig_forecast(data):
    """블록도 대신 실제 예측을 보인다. 과거 168 h 를 받아 향후 24 h 를 낸다는 구조가
    시간 축 위에서 그대로 읽히고, 예측이 실측을 얼마나 따라가는지도 같은 그림에 있다."""
    r, t0 = "US-CAL-CISO", 5400
    act = np.asarray(data["actual"][r])
    # pred24[h][0] 은 '지금'이 아니라 'h+1' 의 예측이다(carbon_2025 원자료 규약).
    # capacity._Windows 가 쓰는 보정과 똑같이 맞춘다 — 그러지 않으면 같은 모델이
    # 이 그림에서만 한 시간 어긋나 실제보다 나쁘게 보인다(f6 교차검증에서 발견,
    # 보정 전 MAE 16.4 → 보정 후 12.2).
    pred = np.concatenate([[act[t0]], data["pred24"][r][t0][:23]])
    hist, fut = act[t0 - 168:t0], act[t0:t0 + 24]
    mae = float(np.abs(fut - pred).mean())

    fig, ax = plt.subplots(figsize=(COL, 116 / 72.0), dpi=300)
    ax.plot(np.arange(-168, 0), hist, color=GRAY, lw=0.7)
    ax.plot(np.arange(24), fut, color=GRAY, lw=1.7, label="실측")
    ax.plot(np.arange(24), pred, color=INK, lw=1.3, ls=(0, (3.5, 1.6)), label="LSTM 예측")
    ax.axvline(0, color=INK, lw=0.8)

    ax.axvspan(-172, 0, color="#f2f2f2", zorder=0)
    # 출력 구간이 전체 폭의 12%뿐이라 그 안에 글자를 넣으면 전부 겹친다.
    # 구간 이름은 아래쪽에, 오차는 위쪽 빈 곳에 따로 둔다. 발행 시각은 세로선과
    # 음영 경계가 이미 말하므로 따로 적지 않는다.
    ax.text(-86, 14, "입력 168 h", ha="center", fontsize=6.4)
    # 출력 구간이 24단위뿐이라 "출력 24 h"(8자)를 넣으면 구분선과 오른쪽
    # 테두리를 둘 다 넘는다. 시간 길이는 x축 눈금(0, 24)이 이미 말한다.
    ax.text(12, 14, "출력", ha="center", fontsize=6.4)
    ax.text(-166, 232, f"MAE {mae:.1f} gCO₂/kWh", ha="left", va="top", fontsize=6.4)

    ax.set_xlim(-172, 24)
    ax.set_ylim(0, 245)
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.set_xticks([-168, -96, -24, 0, 24])
    ax.set_xlabel("발행 시각 기준 경과 시간 (h)", fontsize=LAB)
    ax.set_ylabel("탄소집약도 (gCO₂/kWh)", fontsize=LAB)
    ax.tick_params(labelsize=TICK)
    legend_above(ax, 2)
    fig.tight_layout(pad=0.3)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig3_forecast_curve" + e))
    print(f"wrote fig3_forecast_curve  (MAE {mae:.1f})")


# ═════════════════ 그림 3 · 공간 이동 ═════════════════
def fig_loadbalancer(data):
    """α 가 무엇을 맞바꾸는지를 한 슬롯의 여덟 리전으로 보인다.

    슬롯은 세 선택(α=0·무릎점·α=1)이 모두 다른 시각 중 하나를 골랐다. 한국에서 제출된
    작업은 홈에 두면 351 gCO₂/kWh 이고, 가장 깨끗한 프랑스로 보내면 9 까지 내려가지만
    238 ms 를 쓴다. 무릎점은 캘리포니아를 골라 14 를 134 ms 에 얻는다 — 탄소는 거의
    같고 지연은 절반이다. 이 그림 하나가 무릎점이 왜 필요한지를 대신한다."""
    h, origin = 3499, "KR"
    oi = REGIONS.index(origin)
    lat = load_latency_matrix()[oi]
    c = np.array([np.asarray(data["actual"][r])[h] for r in REGIONS])
    sc = lambda a: a * (c / c.max()) + (1 - a) * (lat / 244.0)
    i_auto, i_lat, i_car = int(np.argmin(sc(0.508))), int(np.argmin(lat)), int(np.argmin(c))

    fig, ax = plt.subplots(figsize=(COL, 128 / 72.0), dpi=300)
    ax.scatter(lat, c, s=16, facecolor="white", edgecolor=INK, lw=0.9, zorder=3)
    for i, r in enumerate(REGIONS):
        if i in (i_auto, i_lat, i_car):
            continue
        nm = KO[r]
        ax.annotate(nm, (lat[i], c[i]), textcoords="offset points",
                    xytext=(4, 3), fontsize=NOTE, color=GRAY)

    # 2026-09-24: ★을 뺀다(사용자 지적 — 학술지 그림에서 별표는 거의 쓰지 않는다).
    # 세 선택은 네모·원·채운원으로 구분하고, 무릎점만 테두리를 한 겹 더 둘러 강조한다.
    marks = ((i_lat, "s", 30, "white", "α=0 · 홈(한국)"),
             (i_car, "o", 30, "white", "α=1 · 프랑스"),
             (i_auto, "o", 44, INK, "무릎점 · 캘리포니아"))
    for idx, mk, s, fc, lab in marks:
        ax.scatter([lat[idx]], [c[idx]], s=s, marker=mk, facecolor=fc,
                   edgecolor=INK, lw=1.0, zorder=5, label=lab)
    ax.scatter([lat[i_auto]], [c[i_auto]], s=110, marker="o", facecolor="none",
               edgecolor=INK, lw=0.7, zorder=5)

    # 무릎점이 무엇을 아꼈는지 — 프랑스까지 더 가는 구간을 화살표로
    ax.annotate("", xy=(lat[i_car], c[i_car]), xytext=(lat[i_auto], c[i_auto]),
                arrowprops=dict(arrowstyle="->", lw=0.7, color=INK,
                                shrinkA=5, shrinkB=5, ls=(0, (2, 1.5))))
    ax.text((lat[i_auto] + lat[i_car]) / 2, c[i_car] + 42,
            f"여기서 {lat[i_car]-lat[i_auto]:.0f} ms 를 더 써도\n"
            f"탄소는 {c[i_auto]-c[i_car]:.0f} 밖에 못 줄인다",
            ha="center", va="bottom", fontsize=NOTE, linespacing=1.35)
    # 반대로 홈에서 무릎점까지는 같은 지연으로 훨씬 많이 준다 — 무릎점의 근거
    ax.annotate("", xy=(lat[i_auto], c[i_auto]), xytext=(lat[i_lat], c[i_lat]),
                arrowprops=dict(arrowstyle="->", lw=0.9, color=INK,
                                shrinkA=6, shrinkB=8))
    ax.text((lat[i_lat] + lat[i_auto]) / 2 - 4, (c[i_lat] + c[i_auto]) / 2 + 18,
            f"{lat[i_auto]-lat[i_lat]:.0f} ms 로\n탄소 {c[i_lat]-c[i_auto]:.0f} 감소",
            ha="center", fontsize=NOTE, linespacing=1.35)

    ax.set_xlim(-16, 262)
    ax.set_ylim(-42, 430)
    ax.set_xticks([0, 50, 100, 150, 200, 250])
    ax.set_xlabel("출발지(한국)로부터의 네트워크 지연 (ms)", fontsize=LAB)
    ax.set_ylabel("탄소집약도 (gCO₂/kWh)", fontsize=LAB)   # "그 슬롯의"는 캡션이 이미 말한다
    ax.tick_params(labelsize=TICK)
    ax.grid(axis="y", color=LIGHT, lw=0.45, zorder=0)
    ax.set_axisbelow(True)
    legend_above(ax, 2)
    fig.tight_layout(pad=0.3)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig3_loadbalancer" + e))
    print(f"wrote fig3_loadbalancer  (무릎점={REGIONS[i_auto]})")


# ═════════════════ 그림 4 · 시간 이동 ═════════════════
def fig_scheduler():
    """용량이 왜 시간 이동을 막는지를 실제 하루로 보인다.

    캘리포니아의 한 날(101일차) 실측이다. 위는 시각별 탄소집약도, 아래는 그 시각 실제
    동시 실행 수다. 탄소가 가장 낮은 저녁 시간대가 정확히 상한 12 에 닿아 있다 —
    작업을 옮기고 싶은 곳이 이미 차 있다는 것이 §6.4 의 발견이고, 이 그림이 그 문장을
    대신한다. 개념도의 '자리 없음' 회색 상자와 달리 여기서는 왜 없는지가 보인다."""
    d = json.load(open(os.path.join(HERE, "fig4_slot_data.json")))
    car, occ, cap = np.array(d["carbon"]), np.array(d["occ"]), d["cap"]
    t = np.arange(24)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(COL, 166 / 72.0), dpi=300,
                                 sharex=True, gridspec_kw=dict(height_ratios=[1, 1.15],
                                                               hspace=0.14))
    a1.plot(t, car, color=INK, lw=1.3)
    lo = int(np.argmin(car))
    a1.scatter([lo], [car[lo]], s=26, marker="v", color=INK, zorder=4)
    a1.annotate("탄소 최저", (lo, car[lo]), textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=NOTE)
    a1.set_ylim(0, 138)
    a1.set_yticks([0, 40, 80, 120])
    a1.set_ylabel("탄소집약도\n(gCO₂/kWh)", fontsize=LAB, linespacing=1.25, labelpad=1)
    a1.tick_params(labelsize=TICK)

    full = occ >= cap
    # 빗금 대신 회색 농담 — 흑백 인쇄에서 더 깨끗하고 학술지에서 더 흔하다.
    a2.bar(t[~full], occ[~full], width=0.74, facecolor="white",
           edgecolor=INK, lw=0.7, label="여유 있음")
    a2.bar(t[full], occ[full], width=0.74, facecolor="#8c8c8c", edgecolor=INK,
           lw=0.7, label="상한 도달 · 배치 불가")
    a2.axhline(cap, color=INK, lw=1.0, ls=(0, (4, 1.6)))
    a2.text(13.2, cap + 0.6, f"유효 상한 {cap}", ha="left", fontsize=NOTE)
    a2.set_ylim(0, 17.5)
    a2.set_yticks([0, 6, 12])
    a2.set_xlim(-0.8, 23.8)
    a2.set_xticks([0, 6, 12, 18, 23])
    a2.set_xlabel("하루 중 시각 (h)", fontsize=LAB)
    a2.set_ylabel("동시 실행 수", fontsize=LAB, labelpad=1)
    a2.tick_params(labelsize=TICK)
    # 상한을 넘긴 슬롯 — 마감이 임박해 미룰 수 없는 작업이 들어간 자리
    over = int(np.argmax(occ))
    if occ[over] > cap:
        a2.annotate("마감 강제", (over, occ[over]), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=NOTE)
    h1, l1 = a2.get_legend_handles_labels()
    fig.legend(h1, l1, fontsize=NOTE, frameon=False, ncol=2, loc="upper left",
               bbox_to_anchor=(0.19, 1.005), handlelength=1.6, columnspacing=1.2,
               handletextpad=0.5)

    fig.subplots_adjust(left=0.215, right=0.985, top=0.905, bottom=0.135, hspace=0.16)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig4_scheduler" + e))
    print(f"wrote fig4_scheduler  (상한 도달 {int(full.sum())}/24 슬롯)")


def main():
    data = carbon_2025.load_2025()
    fig_forecast(data)
    fig_loadbalancer(data)
    fig_scheduler()


if __name__ == "__main__":
    main()
