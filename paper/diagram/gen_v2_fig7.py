# -*- coding: utf-8 -*-
"""v2 그림 7 — 용량이 시간 이동을 어떻게 막는지, 캘리포니아의 피크 날(day 187, 용량 무시 실행이 그날 63 동시) 하루.
위: 시각별 실측 탄소집약도와 최저 시각. 가운데: 그날 그 리전에서 실행된 작업(창 넓은 9건, 자료 규칙)의 레일(제출~마감)과
실행 막대, 강조 작업 한 건의 원하던 자리(용량 무시 실행의 시작, 점선 상자)와 실제 자리. 아래: CAST 의 시각별 동시 실행과 상한 17.
v1 gen_figs_data.fig_scheduler() 를 그대로 옮기고 입력만 v2_fig4_slot_data.json / v2_fig4_gantt_data.json(gen_v2_data.py)으로
바꿨다. 다른 점: 내부 상한이 없으므로 "Effective ceiling" 대신 "Ceiling 17", 탄소 축 범위(이 날 최대 244).
    ./.venv/bin/python paper/diagram/gen_v2_fig7.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from palette import EXCEPT_GRAY, CRITICAL_GRAY  # noqa: E402

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams.update({"axes.unicode_minus": False, "axes.linewidth": 0.8,
                     "xtick.direction": "in", "ytick.direction": "in",
                     "xtick.major.width": 0.8, "ytick.major.width": 0.8,
                     "xtick.major.size": 2.6, "ytick.major.size": 2.6})
INK = "#000000"
COL = 215 / 72.0
LAB, TICK, NOTE = 8.2, 7.1, 6.6


def main():
    d = json.load(open(os.path.join(HERE, "v2_fig4_slot_data.json")))
    car, occ, cap = np.array(d["carbon"]), np.array(d["occ"]), d["cap"]
    t = np.arange(24)
    g = json.load(open(os.path.join(HERE, "v2_fig4_gantt_data.json")))
    highlight_id = g.get("highlight_id")
    # 시작 시각 순으로 두되 강조 작업은 맨 아래 행에 — 인출선이 다른 행의 레일을 가로지르지 않게(v1 과 같은 배치)
    gjobs = sorted(g["jobs"], key=lambda j: (j["id"] == highlight_id, j["tau"]))
    highlight_job = next((j for j in gjobs if j["id"] == highlight_id), None)
    rows = list(range(len(gjobs))); n_rows = len(gjobs)
    ROW_PT, EXTRA_ROWS = 10.0, 2.0
    ymax_c = float(np.ceil(car.max() / 40) * 40 + 30)
    fig, (a1, a3, a2) = plt.subplots(
        3, 1, figsize=(COL, (166 + ROW_PT * (n_rows + EXTRA_ROWS)) / 72.0), dpi=500, sharex=True,
        gridspec_kw=dict(height_ratios=[1, ROW_PT / 100 * (n_rows + EXTRA_ROWS) + 0.12, 1.15], hspace=0.12))

    # ── 위: 탄소 곡선 ──
    a1.plot(t, car, color=INK, lw=1.3)
    # 최저는 현지 하루(UTC 7시 = 현지 0시 이후) 안에서 찾는다 — UTC 0~6시는 전날 저녁 꼬리라 거기 찍히면 그림이 거짓말을 한다
    lo = 7 + int(np.argmin(car[7:]))
    a1.scatter([lo], [car[lo]], s=26, marker="v", color=INK, zorder=4)
    # 글자는 표식 아래 빈 자리에 — 위·옆은 곡선의 급강하(13~14시)가 지나간다(렌더 확인). 흰 배경은 안내선만 가린다.
    a1.annotate("Carbon minimum", (lo, car[lo]), textcoords="offset points", xytext=(0, -11), ha="center", va="top",
                fontsize=NOTE, zorder=5, bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
    GUIDE = "#333333"
    if highlight_job is not None:
        wx0_top = highlight_job["tau_unconstrained"]
        a1.plot([wx0_top, wx0_top], [ymax_c - 10, car[lo]], color=GUIDE, lw=0.9, ls=(0, (3, 2)), zorder=1)
    a1.set_ylim(0, ymax_c)
    a1.set_yticks([0, 80, 160, 240])
    a1.set_ylabel("Carbon intensity\n(gCO₂/kWh)", fontsize=LAB, linespacing=1.25, labelpad=1)
    a1.tick_params(labelsize=TICK)

    # ── 가운데: 간트 — 레일(s_j~D_j) + 실행 막대 ──
    x_lo, x_hi = -0.8, 23.8
    forced_end = forced_row = forced_x0 = None
    highlight_row = None
    for j, ri in zip(gjobs, rows):
        forced = j["forced"]
        fc = CRITICAL_GRAY if forced else "white"
        s0, D0 = j["s"], j["D"]
        a3.plot([max(s0, x_lo), min(D0, x_hi)], [ri, ri], color=INK, lw=0.7, zorder=2)
        if s0 >= x_lo:
            a3.plot([s0, s0], [ri - 0.15, ri + 0.15], color=INK, lw=0.7, zorder=2)
        if D0 <= x_hi:
            a3.plot([D0, D0], [ri - 0.15, ri + 0.15], color=INK, lw=0.7, zorder=2)
        x0, x1 = j["tau"], j["tau"] + j["dur"]
        a3.barh(ri, min(x1, x_hi) - max(x0, x_lo), left=max(x0, x_lo), height=0.62,
                facecolor=fc, edgecolor=INK, lw=0.6, zorder=3)
        if forced and x0 < 20 < x1 and (forced_end is None or x1 > forced_end):
            forced_end, forced_row, forced_x0 = x1, ri, x0
        if highlight_job is not None and j["id"] == highlight_id:
            highlight_row = ri
    if highlight_job is not None:
        hj, hr = highlight_job, highlight_row
        wx0, wx1 = hj["tau_unconstrained"], hj["tau_unconstrained"] + hj["dur"]
        ax0, ax1 = hj["tau"], hj["tau"] + hj["dur"]
        a3.barh(hr, min(wx1, x_hi) - max(wx0, x_lo), left=max(wx0, x_lo), height=0.62,
                facecolor="none", edgecolor=INK, lw=0.7, ls=(0, (2, 1.3)), zorder=4)
        box_cx = (max(wx0, x_lo) + min(wx1, x_hi)) / 2
        bar_cx = (max(ax0, x_lo) + min(ax1, x_hi)) / 2
        pct = 100 * (hj["rate_actual"] / hj["rate_unconstrained"] - 1)
        label_y = n_rows + EXTRA_ROWS / 2 - 0.4
        label_x0 = 0.5
        a3.annotate(f"Capacity-ignored slot · CAST slot (+{pct:.1f}%)", (label_x0, label_y),
                    ha="left", va="center", fontsize=NOTE, zorder=6)
        leader_from_x = label_x0 + 16.2
        for cx in (box_cx, bar_cx):
            a3.annotate("", xy=(cx, hr + 0.33), xytext=(leader_from_x, label_y),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=5,
                                         shrinkA=1.0, shrinkB=1.5, connectionstyle="arc3,rad=0.12"), zorder=6)
        a3.plot([wx0, wx0], [-0.85, n_rows + EXTRA_ROWS - 0.15], color=GUIDE, lw=0.9, ls=(0, (3, 2)), zorder=0.5)
    a3.set_ylim(n_rows + EXTRA_ROWS - 0.15, -0.85)
    a3.set_yticks([])
    a3.set_ylabel("Jobs", fontsize=LAB, labelpad=1)
    a3.tick_params(labelsize=TICK, left=False)
    if forced_row is not None:
        a3.annotate("Forced", (forced_x0, forced_row), textcoords="offset points", xytext=(-4, 0), ha="right",
                    va="center", fontsize=NOTE, zorder=6, bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

    # ── 아래: 시각별 동시 실행 ──
    full = occ >= cap
    a2.bar(t[~full], occ[~full], width=0.74, facecolor="white", edgecolor=INK, lw=0.7)
    a2.bar(t[full], occ[full], width=0.74, facecolor=EXCEPT_GRAY, edgecolor=INK, lw=0.7)
    a2.axhline(cap, color=INK, lw=1.0, ls=(0, (4, 1.6)))
    a2.text(11.5, cap + 0.8, f"Ceiling {cap}", ha="left", fontsize=NOTE, zorder=5,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    a2.set_ylim(0, cap * 1.4)
    a2.set_yticks([0, cap])
    a2.set_xlim(x_lo, x_hi)
    if highlight_job is not None:
        hour = int(round(highlight_job["tau_unconstrained"]))
        a2.plot([highlight_job["tau_unconstrained"]] * 2, [cap * 1.4, occ[hour]], color=GUIDE, lw=0.9, ls=(0, (3, 2)), zorder=0.5)
    a2.set_xticks([0, 6, 12, 18])
    a2.set_xlabel("Hour of day (UTC; local time is 7 h earlier)", fontsize=LAB)
    a2.set_ylabel("Concurrent executions", fontsize=LAB, labelpad=1)
    a2.tick_params(labelsize=TICK)
    over = int(np.argmax(occ))
    if occ[over] > cap:
        a2.annotate("Forced", (over, occ[over]), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=NOTE)
    handles = [Patch(facecolor="white", edgecolor=INK, lw=0.7, label="Headroom"),
               Patch(facecolor=EXCEPT_GRAY, edgecolor=INK, lw=0.7, label="At ceiling")]
    if any(j["forced"] for j in gjobs):
        handles.append(Patch(facecolor=CRITICAL_GRAY, edgecolor=INK, lw=0.6, label="Forced (this job)"))
    a2.legend(handles=handles, fontsize=NOTE, frameon=False, ncol=len(handles), loc="upper left",
              bbox_to_anchor=(0.0, 1.02), handlelength=1.3, columnspacing=0.9, handletextpad=0.35, borderaxespad=0.2)
    fig.subplots_adjust(left=0.215, right=0.985, top=0.985, bottom=0.115, hspace=0.12)
    for e in (".png", ".pdf"):
        fig.savefig(os.path.join(HERE, "v2_fig7_day" + e))
    print(f"wrote v2_fig7_day  (상한 도달 {int(full.sum())}/24 슬롯 · 간트 {len(gjobs)}건 · 강조 {highlight_id} · day {d['day']})")


if __name__ == "__main__":
    main()
