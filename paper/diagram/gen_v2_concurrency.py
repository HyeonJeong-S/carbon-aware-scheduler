# -*- coding: utf-8 -*-
"""v2 그림 9 — 캘리포니아 피크 주의 동시 실행: 용량 무시(결합, 무릎점) 회색 채움 vs CAST(무릎점) 검은 선, 상한 17.
v1 gen_concurrency.py 를 그대로 옮기고 입력만 v2_cal_concurrency.json(gen_v2_data.py 가 만듦)으로 바꿨다.
서식(215×184pt, 글자 8.8/7.7/7.1, 위·오른쪽 축선 없음, y 격자 #dddddd)은 v1 과 같다.
    ./.venv/bin/python paper/diagram/gen_v2_concurrency.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_HERE, "v2_cal_concurrency.json")

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
INK = "#000000"


def step_xy(events):
    xs, ys = [], []
    for t, v in events:
        if xs:
            xs.append(t); ys.append(ys[-1])
        xs.append(t); ys.append(v)
    return xs, ys


def main():
    d = json.load(open(DATA_PATH))
    win_lo, win_hi, cap = d["win_lo"], d["win_hi"], d["cap"]
    xa, ya = step_xy(d["win_events_a"])
    xb, yb = step_xy(d["win_events_b"])
    day0 = win_lo // 24
    fig, ax = plt.subplots(figsize=(215 / 72.0, 184 / 72.0), dpi=500)
    ax.fill_between(xa, ya, color="#c8c8c8", lw=0, zorder=1, label="Capacity ignored")
    ax.plot(xb, yb, color=INK, lw=0.8, zorder=3, label="CAST, knee")   # 10-18(89 점검 [10]): 계열 이름을 표 3·7 과 같게 "CAST, knee"
    ax.axhline(cap, color=INK, lw=1.0, ls=(0, (4, 1.6)), zorder=2, label=f"Ceiling {cap}")   # 10-18(87 점검2 [12]): 점선 → 그림 6(gen_v2_fig7.py) 상한 선과 같은 파선(lw 1.0, 4/1.6)
    # 10-18(87 점검2 [12]): 선 위 "Ceiling 17" 글자를 범례 셋째 항목으로 옮겼다. 선 위에 두면 어디든 회색 봉우리(용량 무시)를
    # 흰 바탕이 가리거나(오른쪽 끝: day 189.8, 왼쪽 끝: day 184.7 의 18~21 구간), 바탕을 빼면 격자 20 이 글자를 지난다(렌더 확인).
    pa = max(ya); ia = ya.index(pa)
    ax.annotate(f"{pa}", (xa[ia], pa), textcoords="offset points", xytext=(-4, -16),
                fontsize=8.2, fontweight="bold", ha="right", va="top")
    ax.set_xlim(0, win_hi - win_lo); ax.set_ylim(0, pa * 1.12)
    xt = list(range(0, win_hi - win_lo + 1, 24))
    ax.set_xticks(xt); ax.set_xticklabels([f"{day0 + i // 24}" for i in xt], fontsize=7.7)
    ax.tick_params(axis="y", labelsize=7.7)
    ax.set_xlabel("Day of year", fontsize=8.8)
    ax.set_ylabel("California: concurrent executions", fontsize=8.8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4)
    # 10-18(87 점검2 [12]): 범례 오른쪽 위 → 왼쪽 위. 셋째 항목(Ceiling 17)이 생기며 범례 표식이 day 187.85 의 63 봉우리와
    # "63" 글자에 닿았다(오른쪽 위에서도 첫 두 표식이 봉우리를 지났다). 왼쪽 위(184~186, 45 이상)는 비어 있다.
    # 흰 바탕(테두리 없음): 격자 60 이 "CAST, knee" 글자 윗부분을 지났다(렌더 확인) — 가리는 것은 격자뿐
    leg = ax.legend(loc="upper left", fontsize=7.1, frameon=True, fancybox=False, handlelength=2.2, borderpad=0.2)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    fig.tight_layout(pad=0.5)
    out = os.path.join(_HERE, "v2_fig9_concurrency.png")
    fig.savefig(out); fig.savefig(out.replace(".png", ".pdf"))
    print("wrote", out, "| 이 주 최대: 용량 무시", pa, "CAST", max(yb), "| 주", day0, "~", (win_hi - 1) // 24)


if __name__ == "__main__":
    main()
