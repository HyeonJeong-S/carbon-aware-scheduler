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
from matplotlib.patches import Patch

# 2026-09-25: Mac 절대경로 → 스크립트 위치 기준(레포 루트 = paper/diagram 의 두 단계 위).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
sys.path.insert(0, HERE)
# 2026-09-24: 그림 전체 공용 회색 팔레트(palette.py). GRAY(#7a7a7a)는 여기 대상이
# 아니다 — "실측 대 예측" 두 계열을 가르는 색이지 정상/예외를 나타내는 색이 아니다.
from palette import EXCEPT_GRAY, CRITICAL_GRAY
INK, GRAY, LIGHT = "#000000", "#7a7a7a", "#cccccc"
COL = 215 / 72.0                 # 단내 폭
FULL = 451 / 72.0                # 전단 폭(그림 1·2가 쓰는 구역)
LAB, TICK, NOTE = 7.5, 6.5, 6.0  # 축 이름 / 눈금 / 주석
# 2026-09-24 b6 배분(그림 10장 통합 점검): NOTE가 5.6이라 그림 3·4·7의 범례·주석이
# 6pt 아래였다. 6.0으로 올린다 — 렌더해서 겹침 없는지 확인 완료.


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

    # 2026-09-25: 입력 168 h 전부를 그리면 요점인 출력 24 h 가 가로축의 12% 로 눌렸다
    # (그림 비판 검토). 입력은 최근 48 h 만 보이고, 168 h 라는 사실은 캡션·본문이 말한다.
    SHOW = 48
    hist = hist[-SHOW:]
    fig, ax = plt.subplots(figsize=(COL, 116 / 72.0), dpi=300)
    ax.plot(np.arange(-SHOW, 0), hist, color=GRAY, lw=0.9)
    ax.plot(np.arange(24), fut, color=GRAY, lw=1.7, label="실측")
    ax.plot(np.arange(24), pred, color=INK, lw=1.3, ls=(0, (3.5, 1.6)), label="LSTM 예측")
    ax.axvline(0, color=INK, lw=0.8)

    ax.axvspan(-SHOW - 2, 0, color="#f2f2f2", zorder=0)
    # 출력 구간이 전체 폭의 12%뿐이라 그 안에 글자를 넣으면 전부 겹친다.
    # 구간 이름은 아래쪽에, 오차는 위쪽 빈 곳에 따로 둔다. 발행 시각은 세로선과
    # 음영 경계가 이미 말하므로 따로 적지 않는다.
    ax.text(-SHOW / 2, 14, "입력 (최근 48 h)", ha="center", fontsize=6.4)
    # 출력 구간이 24단위뿐이라 "출력 24 h"(8자)를 넣으면 구분선과 오른쪽
    # 테두리를 둘 다 넘는다. 시간 길이는 x축 눈금(0, 24)이 이미 말한다.
    ax.text(12, 14, "출력", ha="center", fontsize=6.4)
    # 2026-09-24 b6 배분(그림 10장 통합 점검): "이 구간 MAE ..."가 캡션("이 구간의
    # 평균 절대 오차는 12.2 gCO₂/kWh다")과 겹쳤다 — 어디를 가리킬 필요도 없는 떠
    # 있는 주석이라 캡션 쪽에 맡기고 그림에서는 뺀다(왼쪽 축선에 거의 붙던 문제도
    # 같이 없어진다). mae 값 자체는 print 로그용으로 계속 계산한다.

    ax.set_xlim(-SHOW - 2, 25)
    ax.set_ylim(0, 245)
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.set_xticks([-48, -36, -24, -12, 0, 12, 24])
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
    # 2026-09-25: 나머지 리전을 빈 원으로 그리면 범례의 빈 원("α=1 · 프랑스")과 구별이
    # 안 됐다(그림 비판 검토). 세 선택 밖의 리전은 작은 회색 점으로 낮춘다.
    others = [i for i in range(len(REGIONS)) if i not in (i_auto, i_lat, i_car)]
    ax.scatter(lat[others], c[others], s=10, facecolor=GRAY, edgecolor="none",
               zorder=3, label="기타 리전")
    for i, r in enumerate(REGIONS):
        if i in (i_auto, i_lat, i_car):
            continue
        nm = KO[r]
        # 2026-09-24 b6 배분(그림 10장 통합 점검): 독일(lat=244)이 x축 오른쪽
        # 끝(262)에 바짝 붙어 있어, 오른쪽으로 미는 기본 오프셋을 쓰면 라벨이
        # 축선을 넘어간다(400% 확대로 발견) — 이 점만 왼쪽으로 뒤집는다.
        if r == "DE":
            ax.annotate(nm, (lat[i], c[i]), textcoords="offset points",
                        xytext=(-4, 3), ha="right", fontsize=NOTE, color=GRAY)
        else:
            ax.annotate(nm, (lat[i], c[i]), textcoords="offset points",
                        xytext=(4, 3), fontsize=NOTE, color=GRAY)

    # 2026-09-24: ★을 뺀다(사용자 지적 — 학술지 그림에서 별표는 거의 쓰지 않는다).
    # 세 선택은 네모·원·채운원으로 구분하고, 무릎점만 테두리를 한 겹 더 둘러 강조한다.
    # 2026-09-28(3d 배분, 사용자 메모 "점 위에 나라 이름"): 세 강조 점의 나라는
    # 지금까지 범례 글자("α=0 · 홈(한국)")로만 알 수 있었다 — 정작 "기타 리전"
    # 회색 점은 이미 이름을 점 옆에 바로 찍어 두고 있어(위 for 문) 같은 그림
    # 안에서 표기 규약이 갈렸다(그림_검수규약 "같은 성격 요소는 같은 규약"과
    # 어긋남). 강조 점도 옆에 이름을 찍어 통일하고, 이제 중복이 된 범례의
    # 나라 이름은 뺀다 — 남는 "α=0 · 홈"·"α=1"·"무릎점"은 이름이 아니라
    # 그 점이 셋 중 어느 역할인지(범례 도형 규약)만 말하면 된다. 검게(INK) 써
    # 회색인 "기타 리전" 이름과 강조 대비를 그대로 유지한다.
    marks = ((i_lat, "s", 30, "white", "α=0 · 홈"),
             (i_car, "o", 30, "white", "α=1"),
             (i_auto, "o", 44, INK, "무릎점"))
    for idx, mk, s, fc, lab in marks:
        ax.scatter([lat[idx]], [c[idx]], s=s, marker=mk, facecolor=fc,
                   edgecolor=INK, lw=1.0, zorder=5, label=lab)
    ax.scatter([lat[i_auto]], [c[i_auto]], s=110, marker="o", facecolor="none",
               edgecolor=INK, lw=0.7, zorder=5)
    ax.annotate(KO[REGIONS[i_lat]], (lat[i_lat], c[i_lat]), textcoords="offset points",
                xytext=(6, 2), fontsize=NOTE, color=INK, zorder=6)
    # 2026-09-28(3d 재지적, 400% 확대로 확인): 무릎점·프랑스 둘 다 y≈0~15에 앉아
    # 있어 그 아래 여백이 거의 없다 — 자리를 옮겨 가며 풀다 네 번 다 뭔가에
    # 부딪혔다(테두리 잘림·격자선 관통·화살표와 헷갈림). 자리를 옮기는 대신
    # ylim 아래 끝을 내려 자리 자체를 만든다: 각자 제 점 바로 아래(data 좌표로
    # 직접 지정 — offset points 는 ylim이 바뀌면 스케일도 같이 바뀌어 혼동을
    # 더한다)에 놓아 y=0 격자선 아래·테두리 위 빈 구간 안에 들어가게 한다.
    ax.annotate(KO[REGIONS[i_car]], xy=(lat[i_car], c[i_car]), xytext=(lat[i_car], -30),
                textcoords="data", ha="center", va="top", fontsize=NOTE, color=INK, zorder=6)
    ax.annotate(KO[REGIONS[i_auto]], xy=(lat[i_auto], c[i_auto]), xytext=(lat[i_auto], -30),
                textcoords="data", ha="center", va="top", fontsize=NOTE, color=INK, zorder=6)

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
    # 2026-09-24 b6 배분(그림 10장 통합 점검): 이 글자가 바로 위 화살표 선 위에
    # 놓여 "탄소" 글자를 선이 가로질렀다(확대해서 발견) — 흰 바탕을 깔아 뗀다.
    ax.text((lat[i_lat] + lat[i_auto]) / 2 - 4, (c[i_lat] + c[i_auto]) / 2 + 18,
            f"{lat[i_auto]-lat[i_lat]:.0f} ms 로\n탄소 {c[i_lat]-c[i_auto]:.0f} 감소",
            ha="center", fontsize=NOTE, linespacing=1.35, zorder=6,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2))

    ax.set_xlim(-16, 262)
    # 2026-09-28(3d 재지적): 아래 끝을 -42→-95 로 내려 무릎점·프랑스 라벨 한 줄이
    # y=0 격자선 아래·테두리 위에 들어갈 자리를 만든다(위 주석 참고).
    ax.set_ylim(-95, 430)
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

    캘리포니아의 한 날(101일차) 실측이다. 위는 시각별 탄소집약도, 가운데는 그날 그 리전
    에서 실행된 개별 작업(간트, 아래 참고), 아래는 시각별 동시 실행 수다.
    탄소가 가장 낮은 시간대(UTC 기준, 현지로는 한낮)가 정확히 상한 12 에 닿아 있다 —
    작업을 옮기고 싶은 곳이 이미 차 있다는 것이 §6.4 의 발견이고, 이 그림이 그 문장을
    대신한다. 개념도의 '자리 없음' 회색 상자와 달리 여기서는 왜 없는지가 보인다.

    2026-09-24 b6 배분(1차): 기존 동시 실행 수 막대는 '몇 개가 겹치는가'만 보이고
    '작업 하나가 몇 시간을 무는가'가 안 보였다. 가운데 간트 띠를 추가해 그 점유
    지속을 직접 그렸다 — 실행 구간(tau_j~tau_j+d_j)만 막대로.

    2026-09-24 4c 배분(2차, 사용자 재지적): "그림 이해가 잘 안 된다" — 실행
    구간만 보여서는 "왜 하필 거기서 실행됐는가"가 안 보였다. 이번 판은 각 작업의
    **레일**(s_j~D_j, 제출 시각부터 마감까지 — 가는 선, 실행 가능한 전체 구간)을
    막대 뒤에 함께 그린다. 막대(굵은 채움)는 그 레일 위 어딘가([tau_j,
    tau_j+d_j])에 놓인다. 레일이 넓은데도 막대가 저탄소 구간(그림 왼쪽, 이 날의
    한낮)으로 못 간 작업(j_132777: 레일 22.1h인데 20시가 돼서야 실행)이 바로
    "용량이 막았다"는 이 그림의 요지를 직접 보여준다 — 무제약으로 다시 돌리면
    이 작업은 제출 즉시(21.0 gCO2/kWh)에 실행되지만, 용량 12 아래서는 16시
    (27.2 gCO2/kWh)로 밀린다(scheduler.capacity.run_rolling을 capacity=100000으로
    재실행해 대조 검산함). 레일 끝점(s_j·D_j)에 짧은 세로 눈금을 달아 경계를
    표시하고, 하루 밖으로 이어지는 레일은 눈금 없이 액자 끝까지만 그어 "더
    있다"를 암시한다(막대 자체가 하루 밖으로 이어질 때만 기존 ◀▶ 화살촉을 쓴다
    — 레일은 대부분 하루 밖으로 나가므로 화살촉을 쓰면 거의 매 행에 찍혀 오히려
    어지럽다).

    표본: "그날 겹치는 캘리포니아 작업 중 실행시간 3.0시간 이상" 문턱 하나로만
    거른다(문턱을 3.5→3.0h로 낮췄다 — 3.5h에서는 위 j_132777이 빠졌었다). 14건,
    손으로 고르지 않음. 더 촘촘한 창을 가진 작업은 전부 실행시간이 1시간
    미만이라 막대가 안 보일 만큼 작아 표본에서 자연히 빠진다.

    데이터 출처: gen_fig4_scheduler_data.py 가 scheduler.reproduce와 정확히 같은
    파이프라인(capacity.run_rolling, capacity=12, 표2 ④)을 다시 돌려
    fig4_gantt_data.json을 만든다.

    2026-09-24 4c 배분(세 번째 개정): 레일을 넣고 보니 겹치지 않는 작업끼리 한
    행을 같이 쓰던 그리디 배정이 더는 안 맞았다 — 레일 여러 개가 한 행에서
    하나로 이어져 보여 "이 창이 어느 작업 것인지" 다시 모호해졌다(4c 재지적).
    **한 행에 한 작업**으로 바꾸고, 표본을 "창(window) >= 22h" 단일 문턱으로
    다시 골라(gen_fig4_scheduler_data.py 참고 — j_132777을 반드시 포함해야
    해서 실행시간 문턱을 버렸다) 9건으로 줄였다. 회색 팔레트의 CRITICAL_GRAY
    (마감 강제)는 이 표본엔 없다 — 강제 편입은 창이 좁아야 일어나는 일이라
    창>=22h 조건과 거의 배타적이다(이 날 강제 편입 2건의 창은 16.97h·18.21h로
    22h에 못 미친다). 범례에서도 이 항목은 표본에 실제로 쓰였을 때만 보인다.

    높이: 한 행-한 작업으로 바꾸며 행 수는 6(1차)→9(이번)로 늘었지만, 4c 지시
    ("높이를 늘리지 마라, 줄일 수 있으면 줄여라")에 따라 행당 pt를 13.0→10.0
    으로 낮춰 전체 높이는 오히려 259→256pt로 줄었다(렌더해서 겹침 없는지
    확인했다).
    """
    d = json.load(open(os.path.join(HERE, "fig4_slot_data.json")))
    car, occ, cap = np.array(d["carbon"]), np.array(d["occ"]), d["cap"]
    t = np.arange(24)

    g = json.load(open(os.path.join(HERE, "fig4_gantt_data.json")))
    gjobs = sorted(g["jobs"], key=lambda j: j["tau"])
    # 2026-09-28(3d 배분): 사용자 지적 — "막힌다"만 보이고 "그래서 어디로
    # 갔는가"가 없었다. gen_fig4_scheduler_data.py가 이미 골라 둔 한 건
    # (highlight_id, 자료 기준 — 직접 고르지 않음)만 "가고 싶던 자리"(점선 상자)
    # 를 얹고 실제 자리까지 화살표를 긋는다.
    highlight_id = g.get("highlight_id")
    highlight_job = next((j for j in gjobs if j["id"] == highlight_id), None)
    # 2026-09-24 4c 배분(세 번째 개정): 한 행에 한 작업 — 레일을 넣은 뒤로는
    # 그리디 구간 배정(안 겹치면 행 공유)이 성립하지 않는다. rows[i]=i로
    # 그대로 둔다.
    rows = list(range(len(gjobs)))
    n_rows = len(gjobs)
    ROW_PT = 10.0  # 2026-09-24 4c 배분: 6행→9행이어도 높이가 오히려 줄게(13.0→10.0)
    # 2026-09-28(7차, 사용자 반려): "① 원하던 자리 · ② 실제 자리" 라벨이 맨 아래 행
    # 밑 여백(0.85행)에 안 들어갔다 — 위로 올리면 레일과, 내리면 액자 테두리와
    # 겹쳤다(400%에서 실제로 테두리가 글자를 관통한 것을 확인함). 자리를 옮겨서 될
    # 문제가 아니라 자리 자체가 없었다(그림 4 때와 같은 종류의 제약) — 사용자가
    # 권한 (a)안대로 빈 띠를 한 행만큼 더 넣는다. 높이 증가는 아래 로그에 적는다.
    EXTRA_ROWS = 1.3  # 라벨 한 줄 + 인출선 굴곡이 들어갈 여유(렌더해서 정한 값)

    fig, (a1, a3, a2) = plt.subplots(
        3, 1, figsize=(COL, (166 + ROW_PT * (n_rows + EXTRA_ROWS)) / 72.0), dpi=300, sharex=True,
        gridspec_kw=dict(height_ratios=[1, ROW_PT / 100 * (n_rows + EXTRA_ROWS) + 0.12, 1.15],
                          hspace=0.12))

    a1.plot(t, car, color=INK, lw=1.3)
    lo = int(np.argmin(car))
    a1.scatter([lo], [car[lo]], s=26, marker="v", color=INK, zorder=4)
    a1.annotate("탄소 최저", (lo, car[lo]), textcoords="offset points",
                xytext=(5, 9), ha="left", fontsize=NOTE)   # 2026-09-25: 곡선이 없는 오른쪽 위로
    # 2026-09-28(3d 배분, 사용자 반려 후 2차): "꽉 찼다"만 보이고 "그래서 밀렸다"가
    # 약했다 — 세 패널을 관통하는 안내선으로 탄소최저(위)→상한도달(아래)→실제로
    # 밀린 자리(가운데)의 인과를 한 줄로 잇는다. lo와 highlight_job의 원하던 자리가
    # 정확히 같은 시각(둘 다 x=16)임을 자료로 확인했다 — 우연이 아니라 애초에 그
    # 시각이 탄소 최저라서 그 작업이 거기를 원했던 것이다.
    if highlight_job is not None:
        GUIDE = "#333333"
        wx0_top = highlight_job["tau_unconstrained"]
        a1.plot([wx0_top, wx0_top], [125, car[lo]], color=GUIDE, lw=0.9,
                ls=(0, (3, 2)), zorder=1)
    a1.set_ylim(0, 138)
    a1.set_yticks([0, 40, 80, 120])
    a1.set_ylabel("탄소집약도\n(gCO₂/kWh)", fontsize=LAB, linespacing=1.25, labelpad=1)
    a1.tick_params(labelsize=TICK)

    # ── 가운데: 작업별 간트 — 막대 왼쪽 끝이 tau_j(실행 시작), 길이가 d_j(실행시간) ──
    # 흑백이라 빗금 대신 회색 농담으로 구분한다. 2026-09-24 b6 재검토에서 확인한 것:
    # 이 패널의 회색(개별 작업의 강제 편입)과 아래 occ 패널의 회색(그 시각 동시
    # 실행 수가 상한에 닿음)은 서로 다른 사실이다 — 직접 세어 보면 occ가 상한에
    # 닿은 15개 시간대 중 9개(0~5·21~23시)는 강제 편입 작업이 하나도 없이 정상
    # 편입만으로 찼고, 반대로 14시는 강제 편입이 3건 있는데도 occ는 5로 상한에
    # 한참 못 미친다 — 둘을 같은 회색으로 그리면 "이 막대가 저 칸을 채웠다"는
    # 착각을 준다. 그래서 이 패널만 더 짙은 회색을 쓴다(같은 결의 "예외" 표시를
    # 유지하되 occ 패널의 회색과 눈으로 구별되게).
    x_lo, x_hi = -0.8, 23.8
    # 2026-09-24 b6 배분(회색 팔레트 통일): CRITICAL_GRAY(가장 예외적인 것)를 쓴다.
    # occ 패널의 EXCEPT_GRAY(상한 도달, 한 단계 옅음)와 나란히 놓이는 유일한 자리라
    # 인쇄 크기 그대로 렌더해 구별됨을 확인했다.
    FORCED_GRAY = CRITICAL_GRAY
    forced_end = forced_row = forced_x0 = None
    highlight_row = None
    for j, ri in zip(gjobs, rows):
        forced = j["forced"]
        fc = FORCED_GRAY if forced else "white"
        # 2026-09-24 4c 배분: 레일(s_j~D_j) — 이 작업이 실행될 수 있었던 전체 구간.
        # 막대(아래)보다 먼저, 더 낮은 zorder로 그려 막대가 겹치는 구간을 덮게 한다.
        # 참끝(s_j·D_j)이 하루 안이면 짧은 세로 눈금으로 경계를 표시하고, 하루
        # 밖이면 액자 끝까지만 긋는다(레일 대부분이 하루 밖으로 나가므로 화살촉을
        # 매 행마다 찍으면 오히려 어지럽다 — 막대 쪽 ◀▶만 유지한다).
        s0, D0 = j["s"], j["D"]
        a3.plot([max(s0, x_lo), min(D0, x_hi)], [ri, ri], color=INK, lw=0.7, zorder=2)
        if s0 >= x_lo:
            a3.plot([s0, s0], [ri - 0.15, ri + 0.15], color=INK, lw=0.7, zorder=2)
        if D0 <= x_hi:
            a3.plot([D0, D0], [ri - 0.15, ri + 0.15], color=INK, lw=0.7, zorder=2)
        x0, x1 = j["tau"], j["tau"] + j["dur"]
        a3.barh(ri, min(x1, x_hi) - max(x0, x_lo), left=max(x0, x_lo), height=0.62,
                facecolor=fc, edgecolor=INK, lw=0.6, zorder=3)
        # 2026-09-25(그림 비판 검토): 막대가 하루 밖으로 이어질 때 찍던 ◀▶ 표식이 액자
        # 끝에서 반쯤 잘려 설명 없는 작은 검은 사각형으로 보였다. 레일과 같은 관례로
        # 액자 끝까지 긋는 것만으로 "이어진다"를 나타내고 표식은 뺀다.
        # 20시(occ가 14로 상한을 넘는 자리)까지 걸치는 강제 편입 막대를 짚는다 —
        # 아래 occ 패널의 "마감 강제" 주석과 같은 사건을 가리킨다.
        if forced and x0 < 20 < x1 and (forced_end is None or x1 > forced_end):
            forced_end, forced_row, forced_x0 = x1, ri, x0
        if highlight_job is not None and j["id"] == highlight_id:
            highlight_row = ri

    # ── "가고 싶던 자리 → 실제 자리" — highlight_job 한 건만 그린다 ──
    # wx0/wx1: capacity=100000(사실상 무제약)으로 재실행해 구한 시작·끝(자료
    # 기준, 상상이 아니다). 점선 빈 상자로 실제 막대(굵은 채움)와 구분한다.
    if highlight_job is not None:
        hj, hr = highlight_job, highlight_row
        wx0, wx1 = hj["tau_unconstrained"], hj["tau_unconstrained"] + hj["dur"]
        ax0, ax1 = hj["tau"], hj["tau"] + hj["dur"]
        GUIDE = "#333333"
        a3.barh(hr, min(wx1, x_hi) - max(wx0, x_lo), left=max(wx0, x_lo), height=0.62,
                facecolor="none", edgecolor=INK, lw=0.7, ls=(0, (2, 1.3)), zorder=4)
        # 2026-09-28(2~4차, 사용자 반려 3회): 라벨을 상자에 붙였더니(2차) 좁은 행이라
        # 계속 겹쳤고(3~4차), 흰 배경을 여러 겹 깔아야 했다. **5차, 사용자 재지시**:
        # 글자를 그 자리에 붙이지 말고 상자 둘만 치고, 글자는 행 바깥(패널 아래
        # 여백)에 모아 인출선 둘로 가리킨다. 여백은 이 행(맨 아래 행) 바로 아래뿐이라
        # 다른 행과 안 부딪힌다.
        # 5차 재시도: 글자를 가운데(label_x~20)에 두니 폭(13유닛 안팎)이 액자
        # 오른쪽 끝(23.8)을 넘었다(400%에서 확인) — 왼쪽 빈 자리로 옮긴다. 이 행
        # 아래 여백(y>hr)은 다른 모든 행보다 아래라 어디를 지나든 다른 행과 안
        # 부딪힌다 — 인출선을 대각선으로 곧장 그어도 된다.
        box_cx = (wx0 + min(wx1, x_hi)) / 2       # 원하던 자리(점선 상자) 중심
        bar_cx = min(ax0, x_hi) + (ax1 - ax0) / 2  # 실제 자리(막대) 중심
        pct = 100 * (hj["rate_actual"] / hj["rate_unconstrained"] - 1)
        # 인출선이 이 행의 레일과 거의 나란히 겹쳐 보였다(400%에서 확인, label_y가
        # 레일(y=hr)에 너무 가까웠다) — 액자 바닥 바로 위까지 더 내리고, 살짝 휘게
        # 그어 레일의 곧은 직선과 눈으로 구별되게 한다.
        label_y = n_rows + EXTRA_ROWS / 2 + 0.1   # 새로 늘린 빈 띠 한가운데 즈음
        label_x0 = 0.5
        a3.annotate(f"① 원하던 자리 · ② 실제 자리 (+{pct:.0f}%)", (label_x0, label_y),
                    ha="left", va="center", fontsize=NOTE, zorder=6)
        leader_from_x = label_x0 + 13.3  # 글자 오른쪽 끝 근처에서 인출선 출발
        for cx in (box_cx, bar_cx):
            a3.annotate("", xy=(cx, hr + 0.33), xytext=(leader_from_x, label_y),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=5,
                                         shrinkA=1.0, shrinkB=1.5,
                                         connectionstyle="arc3,rad=0.12"),
                        zorder=6)
        # 2026-09-28(2차, 사용자 반려): "연회색 점선은 인쇄하면 거의 안 보인다" — 더
        # 짙게(#333333) 하고, 위 탄소 패널까지 끌어올려 세 패널을 관통하는 한 줄로
        # 만든다. 다른 행의 레일·막대보다 낮은 zorder로 두어 그 위에 겹치는 자리는
        # 기존 요소가 이기게 한다(행마다 배경에 지나가는 눈금선처럼 읽힌다).
        a3.plot([wx0, wx0], [-0.85, n_rows + EXTRA_ROWS - 0.15], color=GUIDE, lw=0.9,
                ls=(0, (3, 2)), zorder=0.5)
    a3.set_ylim(n_rows + EXTRA_ROWS - 0.15, -0.85)
    a3.set_yticks([])
    a3.set_ylabel("작업", fontsize=LAB, labelpad=1)   # 건수는 캡션 소관(y축 라벨 정렬 문제도 같이 없어짐)
    a3.tick_params(labelsize=TICK, left=False)
    if forced_row is not None:
        # 패널 오른쪽 밖으로 글자가 잘리던 문제(2026-09-24 b6 지적) — 막대 왼쪽의
        # 빈 구간(6~15시, 이 행엔 그 사이 아무 막대도 없다)에 넣어 패널 안에 완전히
        # 들어가게 한다. 아래 occ 패널과 같은 문구("마감 강제")를 써서 같은 사건임을
        # 알아보게 한다.
        # 2026-09-24 4c 배분(세 번째 개정): 레일 선이 생기면서 이 글자 자리를 선이
        # 관통할 수 있다(확대해서 발견) — 흰 배경을 깔아 뗀다. 이번 9건 표본에는
        # forced 작업이 없어 이 분기가 실제로는 안 그려지지만, forced가 다시
        # 섞이는 문턱으로 바뀔 때를 위해 고쳐 둔다.
        a3.annotate("마감 강제", (forced_x0, forced_row),
                    textcoords="offset points", xytext=(-4, 0), ha="right", va="center",
                    fontsize=NOTE, zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

    full = occ >= cap
    # 빗금 대신 회색 농담 — 흑백 인쇄에서 더 깨끗하고 학술지에서 더 흔하다.
    # 범례는 아래에서 Patch로 따로 만든다(세 채움을 한 줄에 다 넣으려고) — 여기
    # label= 은 안 쓴다.
    a2.bar(t[~full], occ[~full], width=0.74, facecolor="white", edgecolor=INK, lw=0.7)
    a2.bar(t[full], occ[full], width=0.74, facecolor=EXCEPT_GRAY, edgecolor=INK, lw=0.7)
    a2.axhline(cap, color=INK, lw=1.0, ls=(0, (4, 1.6)))
    # 2026-09-28: "원하던 자리" 세로 안내선이 이 글자를 관통했다(확대해서 발견,
    # 위쪽 절반은 캡션 위쪽 빈 자리를 지나지만 x=16 부근에서 이 글자와 겹친다) —
    # 흰 배경을 깔고 안내선보다 위 zorder로 그려 그 아래를 가린다.
    a2.text(13.2, cap + 0.6, f"유효 상한 {cap}", ha="left", fontsize=NOTE, zorder=5,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    a2.set_ylim(0, 17.5)
    a2.set_yticks([0, 6, 12])
    a2.set_xlim(x_lo, x_hi)
    if highlight_job is not None:
        # 위 두 패널의 세로 안내선 아래쪽 절반 — "원하던 자리"의 시각이 이미
        # 상한에 닿아 있었다는 것을 막대 위까지 이어 보여준다. 2026-09-28(2차):
        # 위 두 패널과 같은 짙은 색·굵기로 맞춘다(사용자 반려 — "인쇄하면 안 보인다").
        hour = int(round(highlight_job["tau_unconstrained"]))
        a2.plot([highlight_job["tau_unconstrained"]] * 2, [17.5, occ[hour]],
                color="#333333", lw=0.9, ls=(0, (3, 2)), zorder=0.5)
    a2.set_xticks([0, 6, 12, 18])   # 2026-09-25: 끝의 23 이 간격을 깨서 뺐다
    # 2026-09-24: x 축은 UTC 다(원자료가 UTC). day 101 은 4월이라 캘리포니아는
    # PDT(UTC−7) — UTC 14~23시가 현지 오전 7시~오후 4시, 곧 태양광 한낮이다.
    # 축에 UTC 를 명시하지 않으면 "저녁"으로 읽힌다(fd 가 원자료 대조로 발견).
    a2.set_xlabel("하루 중 시각 (UTC · 현지는 7시간 이르다)", fontsize=LAB)
    a2.set_ylabel("동시 실행 수", fontsize=LAB, labelpad=1)
    a2.tick_params(labelsize=TICK)
    # 상한을 넘긴 슬롯 — 마감이 임박해 미룰 수 없는 작업이 들어간 자리
    over = int(np.argmax(occ))
    if occ[over] > cap:
        a2.annotate("마감 강제", (over, occ[over]), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=NOTE)
    # 2026-09-24 b6 지적: 채움이 이제 셋(흰색·중간회색·짙은회색)인데 범례는 둘뿐이었고,
    # 그나마 하나뿐인 범례가 맨 위에 있어 세 패널 전부에 적용되는 것처럼 읽혔다.
    # 세로 높이를 더 늘리지 말라는 지시(11→10쪽 목표)에 따라 줄을 하나 더 만드는
    # 대신, 한 줄에 세 항목을 다 넣고 각 라벨에 소속 패널을 괄호로 밝힌다.
    # 2026-09-24 4c 배분(세 번째 개정): "(동시실행)"·"(간트)"가 패널 이름이라
    # 낯설다는 지적 — "그 시각"(occ 패널, 시간대의 성질) 대 "그 작업"(간트 패널,
    # 개별 작업의 성질)로 바꿔 무엇을 두고 하는 말인지 패널 이름 없이도 읽히게
    # 한다. 또한 이번 9건 표본엔 forced 작업이 없어 CRITICAL_GRAY가 실제로는
    # 안 쓰인다 — 쓰이지 않는 색의 범례 항목을 보여주면 안 되므로 조건부로 뺀다.
    # 2026-09-25(그림 비판 검토): 범례가 그림 맨 위에 있어 세 패널 전부에 적용되는
    # 것처럼 읽혔다. 채움 두 가지는 아래(동시 실행 수) 패널의 것이므로 그 패널 안
    # 윗부분(상한 12 위 빈 띠)으로 옮기고, 패널 안이라 "(그 시각)"도 뺀다.
    handles = [
        Patch(facecolor="white", edgecolor=INK, lw=0.7, label="여유 있음"),
        Patch(facecolor=EXCEPT_GRAY, edgecolor=INK, lw=0.7, label="상한 도달"),
    ]
    if any(j["forced"] for j in gjobs):
        handles.append(Patch(facecolor=FORCED_GRAY, edgecolor=INK, lw=0.6, label="마감 강제(그 작업)"))
    a2.legend(handles=handles, fontsize=NOTE, frameon=False, ncol=len(handles), loc="upper left",
              bbox_to_anchor=(0.0, 1.02), handlelength=1.3, columnspacing=0.9,
              handletextpad=0.35, borderaxespad=0.2)

    fig.subplots_adjust(left=0.215, right=0.985, top=0.985, bottom=0.115, hspace=0.12)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "fig4_scheduler" + e))
    print(f"wrote fig4_scheduler  (상한 도달 {int(full.sum())}/24 슬롯 · 간트 {len(gjobs)}건/{n_rows}행)")


def main():
    data = carbon_2025.load_2025()
    fig_forecast(data)
    fig_loadbalancer(data)
    fig_scheduler()


if __name__ == "__main__":
    main()
