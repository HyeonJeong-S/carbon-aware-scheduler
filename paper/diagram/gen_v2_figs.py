# -*- coding: utf-8 -*-
"""v2 그림 — 결과 파일(scheduler/data/v2/**)에서 그린다.  v1 규약(gen_pareto·gen_benchmark·gen_capacity_sweep) 그대로:
  · 단내 215×190pt, dpi 500, png+pdf.  축 라벨 8.8pt, 눈금 7.7pt, 점 주석 7.1pt, 범례 6pt·테두리 없음.
  · 본 연구 ● 채운 점(INK), 선행·대조 ○ 빈 원, 무릎점은 동심원 과녁(s=34 + 고리 s=150, lw 1.6), 기준 ◇.
  · 위·오른쪽 축선 없음, 왼·아래 0.7pt, y 격자 #dddddd 0.4.  그림 안 설명은 캡션으로 — 그림에는 데이터와 최소 라벨만.
  · 그림 안 글자는 전부 영문(투고규정 10조). 캡션만 국·영문.
  · 점 라벨은 점마다 (dx, dy, ha) 를 손으로 지정하고, 바꿀 때 이유를 주석으로 남긴다.
  · 두 워크로드는 두 패널이 아니라 한 축에 ●(합성)/○(Azure) 로.
  · 그릴 때마다 렌더해서 400% 로 본다(그림_검수규약.txt). 코드만 보고 넘기지 않는다.

    ./.venv/bin/python paper/diagram/gen_v2_figs.py alpha | capsweep | where | priors | herding | alphadist | all
"""
import csv
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.normpath(os.path.join(HERE, "..", "..", "scheduler", "data", "v2"))
sys.path.insert(0, HERE)
from palette import INK, AUX_GRAY, BG_WASH  # noqa: E402

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

W_IN, H_IN = 215 / 72.0, 190 / 72.0
F_LABEL, F_TICK, F_ANN, F_LEG = 8.8, 7.7, 7.1, 7.1   # 10-18: 범례 6.0→6.6 — 215 pt 로 그려 단폭 195.6 pt 에 0.91배로 들어가므로 인쇄 6.0 pt(JOK 실물 최소 5.7~5.9 위)
# 10-18(82 점검4 E [4]): 범례·보조 글자 6.6 → 7.1(점 주석과 같게). 인쇄 6.0 pt 는 대문자 높이로 재면(÷0.72) 5.6~5.8 pt 라 기준 아래였다 —
# 7.1 은 인쇄 6.46 pt(대문자 높이로 약 6.0~6.2).
GRAY = "#888888"


def new_ax(h=H_IN):
    fig, ax = plt.subplots(figsize=(W_IN, h), dpi=500)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)
    ax.tick_params(labelsize=F_TICK)
    return fig, ax


def knee_marker(ax, x, y, filled=True, zo=0):
    ax.scatter([x], [y], s=34, facecolor=INK if filled else "white", edgecolor=INK, lw=0.8, zorder=4 + zo)
    ax.scatter([x], [y], s=150, facecolor="none", edgecolor=INK, lw=1.6, zorder=5 + zo)


def stats(name):
    p = os.path.join(V2, name, "stats.json")
    return json.load(open(p)) if os.path.exists(p) else None


def save(fig, name, pad=0.5):
    fig.tight_layout(pad=pad)
    out = os.path.join(HERE, f"v2_{name}.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))
    print("wrote", out)


# ── 그림: α 전선 — 고정 α 11점의 하부 껍질 + 무릎점, 합성 ● / Azure ○ ───────────────
def fig_alpha():
    fig, ax = new_ax()
    drawn = 0
    # 10-17: Azure 는 고정 α 전선이 없다(G파는 무릎점·α=1 만). 둘째 계열은 분리형 전선(○·회색) — 같은 α 에서 설계 효과를 보이는 자리.
    for fn, main_name, filled in (("alpha_hull_main_joint.json", "main/joint", True),
                                  ("alpha_hull_main_decoupled.json", "main/decoupled", False)):
        p = os.path.join(V2, "analysis", fn)
        st = stats(main_name)
        if not (os.path.exists(p) and st):
            continue
        r = json.load(open(p))["작업당평균"]      # 본문 판정(같은 지연 짝)과 같은 축 — 작업당 평균 지연
        base = st["baseline_kg"]
        pts = sorted(r["points"].values())
        xs = [v[0] for v in pts]; ys = [100 * (1 - v[1] / base) for v in pts]
        H = r["hull"]
        # 10-18(89 점검 [17]): 분리형 ○ 가 CAST ● 를 덮어 α=0.1~0.3·0.6 근처에서 ● 가 안 보였다 → CAST 계열을 위(zorder +4)에,
        # ● 를 ○ 보다 조금 작게(s 14 → 9) 그려 ○ 안에 ● 가 보이게 한다.
        zo = 4 if filled else 0
        ax.plot([h[0] for h in H], [100 * (1 - h[1] / base) for h in H], color=INK if filled else GRAY, lw=1.1, zorder=2)   # 선은 둘 다 점 아래(CAST 선이 분리형 ○ 를 꿰지 않게)
        # 10-18(87 점검2 [2]): ○ 를 키우고(s 14 → 30, 테두리 0.8 → 0.7) ● 는 그대로 작게(s 6) — ○ 안지름(약 4.8 pt)이 ● 지름(2.4 pt)의
        # 두 배라 두 점이 거의 같은 자리(α=0~0.3, 0.9, 1)에서도 고리와 점 사이 흰 틈이 남아 "○ 안의 ●" 로 둘 다 보인다.
        ax.scatter(xs, ys, s=6 if filled else 30, facecolor=INK if filled else "white", edgecolor=INK, lw=0.5 if filled else 0.7, zorder=3 + zo)
        kx, ky = r["knee"][0], 100 * (1 - r["knee"][1] / base)
        if filled:
            # 10-18(82 점검4 E [9](a)): 같은 지연 ×(47.71, 72.86)가 무릎점(47.85, 71.93)과 1.3 pt 거리라 과녁 안 검은 ● 위에 얹혀
            # 흰 테두리를 둘러도 ⊗ 처럼 묻혔다 → CAST 무릎점 과녁만 안을 흰색으로 비우고(가운데 ● 없음) 고리를 1.6 → 1.0 으로 가늘게.
            # 과녁 크기(s 150)와 자리는 그대로 — 고리 안에는 × 하나만 남는다. 분리형 과녁(○ + 고리)은 그대로.
            ax.scatter([kx], [ky], s=150, facecolor="white", edgecolor=INK, lw=1.0, zorder=5 + zo)
        else:
            knee_marker(ax, kx, ky, filled=filled, zo=zo)
        # 라벨은 양 끝 α 와 무릎점만. 결합(●)은 위·왼쪽, 분리형(○)은 아래·오른쪽에 적어 서로 피한다(렌더 확인 10-17).
        dy = 6 if filled else -12
        if filled:
            ax.annotate("α=0", (xs[0], ys[0]), textcoords="offset points", xytext=(7, 1), fontsize=F_ANN, ha="left")
        # 10-18: 두 계열의 α=1 점은 같은 자리(120 ms, 95.7/95.3 %)라 라벨 하나만 점 아래에 — 위 라벨은 격자 100 에 얹히고 축 위로 나갔다
        # 10-18(82 점검4 E [9]): 오른쪽 맞춤(−4 pt)이면 라벨이 α=0.9 점(112.5 ms) 바로 아래라 그 점이 자기 점(120 ms)보다 가까웠다 →
        # 왼쪽 맞춤으로 α=1 점 바로 아래(−1.5 pt 에서 시작)에 둔다. 오른쪽 끝은 축 안(xlim 130).
        if not filled:
            ax.annotate("α=1", (xs[-1], ys[-1]), textcoords="offset points", xytext=(-1.5, dy), fontsize=F_ANN, ha="left")
        # 10-18(87 점검2 [2]): "knee" 두 라벨이 어느 설계 것인지 적었다 — "CAST knee" / "Decoupled knee"
        if filled:
            # 10-18(84 점검3 [8]): 라벨이 과녁에서 약 10 ms 왼쪽·8 %p 위로 떨어져 있었다 → 과녁 고리 바로 왼쪽(고리 반지름 6.1 pt + 틈)에 붙였다
            ax.annotate("CAST knee", (kx, ky), textcoords="offset points", xytext=(-8, 3), fontsize=F_ANN, ha="right", va="center")
        else:
            ax.annotate("Decoupled knee", (kx, ky), textcoords="offset points", xytext=(10, -5), fontsize=F_ANN, ha="left")
        # 같은 지연 짝(×): 무릎점과 같은 작업당 평균 지연을 내는 고정 α 실행. 본문 판정(분리형 무릎점이 같은 지연의 고정 α 보다
        # 6.62 %p 뒤짐)을 그림에서 보이게 — 회색 보조선은 α=0.4~0.5 를 직선으로 이어 그 자리의 실제 값보다 낮다.
        # 흰 테두리(path effect)로 CAST 무릎점의 검은 ● 위에서도 × 가 보인다.
        pair = stats("alpha/m0.5687" if filled else "alpha/decoupled_m0.4375")
        if pair:
            import matplotlib.patheffects as pe
            # 10-18(84 점검3 [8]): CAST × 가 과녁 안에 묻혀 거의 안 보였다 → 선 0.9 → 1.3, 크기 20 → 30, 흰 테두리 1.8 → 2.6.
            # zorder 12 는 과녁(●4+4, 고리 5+4)보다 위 — 범례 표식도 같은 굵기로.
            ax.scatter([pair["avg_latency_ms"]], [pair["savings_pct"]], marker="x", s=30, color=INK, lw=1.3, zorder=12,
                       path_effects=[pe.withStroke(linewidth=2.6, foreground="white")])
        ax.plot([], [], color=INK if filled else GRAY, lw=1.1, marker="o", ms=2.45 if filled else 5.5, mew=0.5 if filled else 0.7, mfc=INK if filled else "white", mec=INK,
                label="CAST" if filled else "Decoupled")   # 표 5·본문과 같은 이름
        drawn += 1
    if not drawn:
        print("alpha: 자료 없음"); return
    ax.set_xlabel("Mean latency (ms)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    ax.set_xlim(-6, 130); ax.set_ylim(-4, 100)
    ax.scatter([], [], marker="x", s=30, color=INK, lw=1.3, label="Fixed α, same latency")   # 87 점검2 [2]: 같은 지연 짝
    # 10-18(82 점검4 E [4]): 범례를 7.1 pt 로 키우니 y 격자 20 이 "CAST" 글자 아랫부분을 지나갔다(전 판도 글자 가운데를 지났다) →
    # 그림 11 처럼 흰 바탕(테두리 없음)으로 격자만 가린다. 범례 자리(오른쪽 아래)에는 점·선이 없다(렌더 확인).
    leg = ax.legend(fontsize=F_LEG, frameon=True, loc="lower right", handlelength=2.0, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    save(fig, "alpha")


# ── 그림: α 전선, CAST 만(줄인 판 그림 8, v2_alpha_cast) ─────────────────────────────
# 10-18(73_그림8_CAST만): 줄인 판(74_줄인판_설계안 143행 "그림 8 은 CAST 만")용 변형. v2_alpha 는 그대로 두고 따로 만든다.
#  · 분리형 곡선·과녁·× 와 범례 항목을 뺐다.
#  · 줄인 판의 "같은 왕복 지연 짝" 은 실행 시간 가중 지연으로 맞춘 고정 α(74 설계안 28행, 원고 표 6 짝 0.575)라
#    가로축·열한 점·무릎점을 모두 같은 자(alpha_hull_main_joint.json 의 "d가중", stats 의 dw_latency_ms)로 그린다 —
#    × 만 가중 자로 찍고 나머지를 작업당 자로 두면 한 그림에 두 자가 섞인다.
#  · 선은 열한 점을 α 순서대로 잇는다(원고 "열한 점을 이은 선은 보조선"). 가중 자에서는 하부 껍질(hull)도 열한 점 전부라 같은 선.
#  · 분리형 ○ 가 없으니 ● 를 본래 크기(s 14)로 되돌렸다(s 6 은 ○ 안에 넣으려고 줄인 것).
def fig_alpha_cast():
    p = os.path.join(V2, "analysis", "alpha_hull_main_joint.json")
    st = stats("main/joint")
    pair = stats("alpha/m0.5750")      # 가중 지연 짝(analysis/alpha_pair_main_joint_dw.json 의 pair 와 같은 실행)
    if not (os.path.exists(p) and st and pair):
        print("alpha_cast: 자료 없음"); return
    r = json.load(open(p))["d가중"]
    base = st["baseline_kg"]
    pts = sorted(r["points"].values())
    xs = [v[0] for v in pts]; ys = [100 * (1 - v[1] / base) for v in pts]
    assert len(xs) == 11
    kx, ky = r["knee"][0], 100 * (1 - r["knee"][1] / base)
    px, py = pair["dw_latency_ms"], pair["savings_pct"]
    print(f"alpha_cast: knee ({kx:.2f} ms, {ky:.2f} %), pair α={pair['alpha_mean']:.4f} ({px:.2f} ms, {py:.2f} %)")

    fig, ax = new_ax()
    ax.plot(xs, ys, color=INK, lw=1.1, zorder=2)
    ax.scatter(xs, ys, s=12, facecolor=INK, edgecolor=INK, lw=0.5, zorder=7)
    # 무릎점 과녁과 ×: 가중 자에서 × 는 무릎점에서 왼쪽 0.5 pt·위 2.6 pt(설계 크기) — v2_alpha 의 고리(s 150, 안지름 5.6 pt)와
    # × (s 30 + 흰 테두리)로는 × 윗끝이 고리를 끊었다(1200 dpi 확인). → 고리를 키우고(s 150 → 230, 반지름 7.6 pt, 선 1.0 그대로)
    # × 를 줄이고(s 30 → 20, 선 1.3 → 1.1) 흰 테두리를 뺐다(고리 안이 흰 바탕이라 필요 없다). × 끝–고리 안쪽 틈 약 0.9 pt.
    # 고리 바깥–α=0.6 ● 틈은 ● 를 s 14 → 12 로 줄여 약 1.4 pt.
    ax.scatter([kx], [ky], s=230, facecolor="white", edgecolor=INK, lw=1.0, zorder=9)
    ax.scatter([px], [py], marker="x", s=20, color=INK, lw=1.1, zorder=12)
    ax.annotate("α=0", (xs[0], ys[0]), textcoords="offset points", xytext=(7, 1), fontsize=F_ANN, ha="left")
    ax.annotate("α=1", (xs[-1], ys[-1]), textcoords="offset points", xytext=(-1.5, -12), fontsize=F_ANN, ha="left")
    ax.annotate("CAST knee", (kx, ky), textcoords="offset points", xytext=(-10, 3), fontsize=F_ANN, ha="right", va="center")   # 고리 반지름 7.6 pt + 틈
    ax.plot([], [], color=INK, lw=1.1, marker="o", ms=3.46, mew=0.5, mfc=INK, mec=INK, label="CAST, fixed α")
    ax.scatter([], [], marker="x", s=20, color=INK, lw=1.1, label="Fixed α, same RTT")
    ax.set_xlabel("Duration-weighted mean RTT (ms)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    ax.set_xlim(-6, 130); ax.set_ylim(-4, 100)
    leg = ax.legend(fontsize=F_LEG, frameon=True, loc="lower right", handlelength=2.0, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    save(fig, "alpha_cast")
    fig.savefig(os.path.join(HERE, "v2_alpha_cast.svg"))


# ── 그림: 용량비 스윕 — Azure 한 패널(단폭). 합성 워크로드는 선행 정책 평면(fig_priors)이 맡는다 ──
def fig_capsweep():
    """상한 스윕 — Azure 한 패널, 단폭 215 pt. 절감(무릎점 ● 실선, α=1 ■) 대 상한 배수, 용량 무시 수준은 점선 기준선.
    10-18(89 점검 [4]): 합성 (a) 패널은 그림 11(fig_priors)의 CAST 곡선 두 개와 같은 실행 14개라 지웠다 — 합성의 용량 무시 수준은
    그림 11 에 가로 점선으로 옮겼다. [11]: x 범위를 자료가 있는 0.75~2× 에 맞춰 0.65~2.3×, 대표 상한 1.25× 에 눈금.
    [10]: 계열 이름 "CAST, knee" / "CAST, α=1", 용량 무시 점선은 "Capacity ignored, knee"(검은) / "…, α=1"(회색, 자료가 있을 때만 —
    Azure 는 α=1 용량 무시 실행이 없다)."""
    from matplotlib.ticker import NullFormatter, NullLocator
    fig, ax = new_ax(h=170 / 72.0)
    YLIM = (25, 70)
    levels = [("0.50x", 0.5), ("0.75x", 0.75), ("1.00x", 1.0), ("1.50x", 1.5), ("2.00x", 2.0), ("3.00x", 3.0)]
    pre, main_name, ig_name = "azure/cap_", "azure/joint", "azure/ignore"
    any_data = False
    for suf_a, mk, ls, col, name in (("", "o", "-", INK, "CAST, knee"), ("_a1", "s", (0, (3, 1.5)), GRAY, "CAST, α=1")):
        rows = []
        for suf, x in levels:
            st = stats(pre + suf + suf_a)
            if st: rows.append((x, st["savings_pct"]))
        m = stats(main_name + suf_a)
        if m: rows.append((1.25, m["savings_pct"]))
        rows.sort()
        if not rows: continue
        any_data = True
        # 10-18(78 점검6 E [9]): 캡션이 "■"(검정)라 부르는데 회색으로 찍혔다 → ■ 만 검정(선 색·굵기·파선은 그대로 회색)
        ax.plot([r[0] for r in rows], [r[1] for r in rows], color=col, lw=1.1 if suf_a == "" else 0.9, ls=ls if len(rows) > 1 else "none",
                marker=mk, ms=3.2 if mk == "o" else 2.8, mfc=INK, mec=INK, mew=1.0 if mk == "o" else 0.4, zorder=3, label=name)
    # 용량 무시 점선은 곡선 둘 다음에 — 범례 순서가 CAST 둘, 용량 무시 순이 되게
    for suf_a, col, ig_lab in (("", INK, "Capacity ignored, knee"), ("_a1", GRAY, "Capacity ignored, α=1")):
        ig = stats(ig_name + suf_a)
        # 10-18(82 점검4 E 반영 중 발견): azure/ignore_a1(10-18 10:01 실행, 95.11 %)이 생겨 세로 범위(25~70) 밖 선의 범례만 찍혔다 —
        # 그림에 안 보이는 범례 항목을 막으려고 범위 안의 값만 그린다(지난 판 그림·캡션과 같은 세 항목).
        if ig and YLIM[0] <= ig["savings_pct"] <= YLIM[1]:
            ax.axhline(ig["savings_pct"], color=col, lw=0.6, ls=(0, (1, 1.6)), zorder=1, label=ig_lab)
    if not any_data:
        print("capsweep: 자료 없음"); return
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.75, 1, 1.25, 1.5, 2]); ax.set_xticklabels(["0.75×", "1×", "1.25×", "1.5×", "2×"], fontsize=F_TICK)
    ax.set_xlim(0.65, 2.3); ax.set_ylim(*YLIM)
    ax.set_xlabel("Ceiling (× baseline peak)", fontsize=F_LABEL)   # 10-18(87 점검2 [14]): "Capacity" → 본문·그림 6·7·11 과 같은 "Ceiling"
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    # 10-18(82 점검4 E [4]): 범례 7.1 pt 에서 y 격자 30 이 "Capacity ignored, knee" 윗부분에 닿았다 → 흰 바탕(테두리 없음)으로 격자만 가린다
    leg = ax.legend(loc="lower right", fontsize=F_LEG, frameon=True, handlelength=2.0, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    save(fig, "capsweep"); plt.close(fig)


# ── 그림: 어디서 무는가 — (a) 리전별 시간 이동 이득 몫 vs 일교차 (원 크기 = 초과 시간 몫); (b) 상한을 넘긴 현지 시각 ──
REGION_NAME = {"US-CAL-CISO": "California", "US-TEX-ERCO": "Texas", "US-NY-NYIS": "New York", "FR": "France",
               "DE": "Germany", "KR": "Korea", "IN": "India", "JP": "Japan"}   # 그림 4·(b) 범례와 같은 전체 이름


def where_scatter(ax, r):
    regs = list(r["swing_abs"].keys())
    # 10-17: x 축은 상대 σ 가 아니라 절대 변동(일별 최대−최소 평균) — 시간 이득은 이것을 따른다(FR σ 0.97·이득 0.3%).
    xs = [r["swing_abs"][g] for g in regs]; ys = [100 * r["temporal_gain_share"][g] for g in regs]
    ho = r.get("ignore", {}).get("hours_over_share", {g: 0 for g in regs})
    # 원 넓이 = 용량 무시 실행에서 상한을 넘긴 시간의 몫(CAL 55.6%, FR 37.7%, JP 6.7%, 나머지 0 → 작은 점)
    # 10-18(89 점검 [19]): JP 원이 CAL 큰 원에 닿았다. 넓이 계수 420 → 336(0.8배)으로는 렌더에서 여전히 닿아(중심 간 8.7 pt,
    # 반지름 합 11 pt), 10 + 250x 도 닿아(렌더 확인) 14 + 420x → 9 + 180x 로 줄였다(CAL 지름 15.8 → 10.4 pt, 두 원 사이 약 1.4 pt).
    # 모든 원에 같은 식이라 넓이 대비(넓이 ∝ 몫)는 그대로.
    ax.scatter(xs, ys, s=[9 + 180 * ho.get(g, 0) for g in regs], facecolor="white", edgecolor=INK, lw=0.9, zorder=3)
    # 10-18(89 점검 [19]): 약자(CAL·TEX·NY…)는 캡션·본문에 정의가 없어 전체 이름으로. 자리는 렌더 확인 뒤 손으로:
    # 10-18(84 점검3 [5]): Japan 라벨에 "(6.7%)" 가 붙어 길어지자 오른쪽 끝이 India 점 위로 가 India 점에 더 가까웠다 → 8 pt 왼쪽으로.
    # Korea 는 점 아래면 격자 5 가 글자 윗부분을 지나 점 오른쪽으로. California 는 큰 원 왼쪽, Japan 은 원 위, France 는 원 위(가운데 맞춤이면 F 가 y 축선에 걸려 왼쪽 맞춤), Germany 는 오른쪽이면 축 밖이라 점 아래, 나머지 오른쪽.
    off = {"US-CAL-CISO": (-11, -4, "right"), "JP": (-8, 7, "center"), "FR": (-5, 11, "left"), "US-NY-NYIS": (7, -3, "left"),
           "KR": (6, -2.5, "left"), "DE": (0, -10, "center")}
    for g, x, y in zip(regs, xs, ys):
        dx, dy, ha = off.get(g, (5, -2, "left"))
        # 10-18(84 점검3 [5]): 넓이 식 9+180x 에 바닥값이 있어 일본 원(6.7%)이 몫 0 인 작은 원과 거의 같은 크기로 보였다 →
        # 큰 원(몫 1% 이상: CAL 55.6·FR 37.7·JP 6.7, regions_main.json 의 hours_over_share 그대로)은 이름 뒤 괄호에 몫을 적는다.
        share = ho.get(g, 0)
        lab = REGION_NAME[g] + (f" ({100 * share:.1f}%)" if share >= 0.01 else "")
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(dx, dy), fontsize=F_ANN, ha=ha)
    ax.set_xlim(0, max(xs) * 1.18); ax.set_ylim(-1.5, max(ys) * 1.17)   # 10-18: 위 여백 1.25 → 1.17 — 세로 눈금을 넓혀 CAL·JP 원 사이를 띄운다
    ax.set_xlabel("Mean daily range of intensity (gCO₂/kWh)", fontsize=F_LABEL)
    ax.set_ylabel("Share of temporal savings (%)", fontsize=F_LABEL)


def where_hours(ax, r):
    hc = np.array(r.get("ignore", {}).get("local_hist_CAL", [0] * 24)); hf = np.array(r.get("ignore", {}).get("local_hist_FR", [0] * 24))
    x = np.arange(24)
    # 10-18(87 점검2 [13]): 높이 0 인 막대는 그리지 않는다(흰 막대는 높이 0 이어도 테두리가 축 위에 검은 줄로 찍혔다).
    # 흰 막대 테두리 0.6 → 0.4 — 1% 미만의 낮은 흰 막대(프랑스 18·20시)가 테두리만으로 검은 막대처럼 보였다.
    # 막대는 축선(zorder 2.5) 아래에 두어 낮은 막대의 아래 테두리가 축선에 묻히게 한다.
    # 렌더(400%): 0.4 로도 프랑스 18시(0.12%)는 높이 0.5 pt 라 검은 조각으로 보였다 → 두 계열 모두 0.5% 미만은 그리지 않는다
    # (캘리포니아 16·17시 0.13·0.16%, 프랑스 18·20시 0.12·0.25% — 합 0.66%. 캡션에 한 구절).
    MIN_PCT = 0.5
    pc, pf = 100 * hc / max(hc.sum(), 1e-9), 100 * hf / max(hf.sum(), 1e-9)
    ax.bar(x[pc >= MIN_PCT] - 0.2, pc[pc >= MIN_PCT], color=INK, width=0.4, zorder=2, label="California")
    ax.bar(x[pf >= MIN_PCT] + 0.2, pf[pf >= MIN_PCT], facecolor="white", edgecolor=INK, lw=0.4, width=0.4, zorder=2, label="France")
    ax.set_xticks([0, 6, 12, 18]); ax.set_xlim(-0.7, 23.7)
    ax.set_xlabel("Local hour", fontsize=F_LABEL)
    ax.set_ylabel("Hours over ceiling (%)", fontsize=F_LABEL)   # 10-18(84 점검3 [6]): "Share of hours over ceiling (%)" 가 패널 높이보다 길어 축 위로 나갔다
    # 10-18(89 점검 [8]): 범례 6.6 → 7.1 — 두 장을 build_v2_docx.stack_ab 로 이어 붙이면 배율 0.847 이라 6.6 은 인쇄 5.6 pt
    # 흰 바탕(테두리 없음)은 y 격자 20 이 "California" 글자를 지나가지 않게 — 가리는 것은 격자뿐
    leg = ax.legend(fontsize=F_ANN, frameon=True, loc="upper right", handlelength=1.2, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)


def fig_where():
    p = os.path.join(V2, "analysis", "regions_main.json")
    if not os.path.exists(p):
        print("where: regions_main.json 없음"); return
    r = json.load(open(p))
    fig, ax = new_ax(); where_scatter(ax, r); save(fig, "where"); plt.close(fig)
    fig, ax = new_ax(h=150 / 72.0); where_hours(ax, r); save(fig, "where_hours"); plt.close(fig)
    # 10-18(89 점검 [8]): 한 장짜리 v2_where_ab — 215 pt 폭 한 figure 에 (a)(b) 를 위아래로, 패널 머리 (a)(b) 는 각 축 안 왼쪽 위.
    # stack_ab(라벨 띠 110 px 를 붙여 230.8 pt → 0.847배)를 거치지 않으므로 단폭 배율 0.91 이 그대로 산다. 원고 표기는 [그림 9 | v2_where_ab | 단폭].
    fig, (a, b) = plt.subplots(2, 1, figsize=(W_IN, 300 / 72.0), dpi=500, gridspec_kw=dict(height_ratios=[1.45, 1.0]))
    for q in (a, b):
        for sp in ("top", "right"): q.spines[sp].set_visible(False)
        for sp in ("left", "bottom"): q.spines[sp].set_linewidth(0.7)
        q.grid(axis="y", color="#dddddd", lw=0.4, zorder=0); q.tick_params(labelsize=F_TICK)
    where_scatter(a, r); where_hours(b, r)
    for q, t in ((a, "(a)"), (b, "(b)")):
        q.text(0.02, 0.98, t, transform=q.transAxes, fontsize=F_LABEL, ha="left", va="top")
    fig.align_ylabels([a, b])
    fig.tight_layout(pad=0.5, h_pad=0.8)
    out = os.path.join(HERE, "v2_where_ab.png"); fig.savefig(out); fig.savefig(out.replace(".png", ".pdf")); plt.close(fig)
    print("wrote", out)


# ── 그림: 선행 정책 평면 — 절감 vs 필요 용량. ○ 선행, ● CAST 곡선(용량비 스윕의 자기 피크) ──
def fig_priors():
    fig, ax = new_ax()
    # (라벨, dx, dy, ha) — 점마다 지정. 오른쪽 끝(Sukprasert 둘)은 왼쪽으로 적어 축 밖으로 안 나가게.
    # 그림 안 글자는 짧은 이름만 — 뜻은 캡션에서 푼다 (S-T: Sukprasert temporal, S-ST: spatial+temporal, h: 홈 고정)
    # 10-17: 라벨은 표 7 의 이름과 같게(92 지적 — 그림·표 이름 일치 규칙)
    # 렌더(10-17): CASPER 라벨이 α=1 곡선 점(26·39)에 걸리고 S+T 라벨이 "CAST α=1" 과 겹쳐 자리 조정
    labels = {"cics": ("CICS", -6, -1, "right"),   # 10-18 렌더: 오른쪽이면 기준 피크 점선(13)을 가로질러 왼쪽으로
              "casper": ("CASPER", 0, -11, "center"),   # CASPER 는 α=1 곡선 위에 놓이는 점 — 라벨은 곡선 아래
              "suk_home": ("Suk. temporal (home)", 6, -1, "left"),
              # 10-18(84 점검3 [1]): 가운데 맞춤이면 라벨 왼쪽 끝이 Caspian 점(34, 67.5) 바로 오른쪽에 붙고 그 아래 Caspian 라벨이 있어
              # (34, 67.5) 점이 "Suk. temporal (ours)" 로 읽혔다 → 자기 점 바로 아래, 점 8 pt 왼쪽에서 시작(왼쪽 맞춤)해
              # Caspian 라벨(점 오른쪽) 끝과 띄우고, 같은 줄로 이어 읽히지 않게 Caspian 라벨보다 한 줄쯤 낮게 둔다.
              # 점에서 16 pt 내려가므로 점 → 라벨 짧은 지시선(세로, 아래 LEADER)을 단다. 렌더: −11 이면 Caspian 라벨과 기준선이 거의 같아
              # "Caspian Suk. temporal (ours)" 한 줄로 읽혔고, Caspian 라벨을 점 높이에 두면 CAST 곡선 끝점(39, 73.4)이 자기 점보다 가까웠다.
              "suk_lb_v2knee": ("Suk. temporal (ours)", -8, -16, "left"),   # 10-18 렌더: 오른쪽이면 그림 끝에 닿아 점 아래로  # CAST(무릎점)가 정한 리전 위의 Sukprasert 시간 이동 — 표 7 과 같은 행(10-18)
              "suk_st": ("Suk. spatial+temporal", -14, -11, "center"),   # 10-18 렌더: 가운데면 그림 오른쪽 끝에 닿아 왼쪽으로 조금  # 오른쪽 끝 점 — 왼쪽으로 적으면 α=1 곡선을 가로지르므로 점 아래
              "caspian_w1.0_frac": ("Caspian", 5, -3, "left")}   # 10-18(84 점검3 [1]): 점 아래 → 점 오른쪽(같은 높이). 라벨이 자기 점에 붙어 읽힌다   # 10-18 렌더: 오른쪽이면 Suk(ours) 라벨과 겹쳐 점 아래로
    # 10-18(84 점검3 [1]) 지시선 아래 끝(점 기준 offset pt). 렌더: 세로로 내리면 "k" 줄기 위에 떨어져 k 가 길어 보였다 →
    # "Suk." 와 "temporal" 사이 빈칸 위(라벨 시작 −8 + "Suk." 폭 13 + 빈칸 반 1.2 = +6.2)로 비스듬히 내린다.
    LEADER = {"suk_lb_v2knee": (6.2, -11.0)}
    for p in glob.glob(os.path.join(V2, "priors", "*.json")):
        j = json.load(open(p)); s = j["at_cap"]; n = j["name"]
        if n in ("baseline", "suk_lb"):   # 10-18: suk_lb 는 v1 로드밸런서 리전 위의 옛 행 — 표 7 의 (ours) 는 suk_lb_v2knee
            continue
        # 10-18(78 점검6 E 반영 중 발견): Caspian 가중치 민감도 실행(caspian_w0.5_frac 13:38, w2.0 13:34)이 priors/ 에 생겨
        # 표 7 에 없는 ○ 와 "caspian_w0.5_frac" 라벨이 Caspian 점에 겹쳐 찍혔다 → 표 7 의 Caspian(w1.0_frac)만 그린다
        if n.startswith("caspian") and n != "caspian_w1.0_frac":
            continue
        # 10-18(89 점검 [20]): CASPER ○ 가 α=1 선에 꿰였다 → 흰 채움 ○ 를 곡선·점선(zorder ≤4) 위로 올려 선을 가린다
        # 10-18(87 점검2 [15]): ○ 뒤에 흰 원(테두리 없음, s 60)을 깔아 선이 ○ 앞에서 끊기게 — CASPER ○(α=1 곡선 위)·
        # Suk. temporal (ours) ○(무릎점 가로 점선 73.39 위)·Suk. spatial+temporal ○(α=1 가로 점선 위)가 선에 꿰인 것처럼 보였다.
        # 흰 원은 곡선·점선(zorder ≤4) 위, 라벨(5) 아래.
        ax.scatter([s["required_capacity"]], [s["savings_pct"]], s=60, facecolor="white", edgecolor="none", zorder=4.5)
        ax.scatter([s["required_capacity"]], [s["savings_pct"]], s=24, facecolor="white", edgecolor=INK, lw=0.9, zorder=6)
        lab, dx, dy, ha = labels.get(n, (n, 6, -1, "left"))
        # 10-18: 흰 바탕(테두리 없음, pad 0.4) — y 격자(60·20)가 Caspian·Suk. temporal (home) 글자를 지나갔다. 가리는 것은 격자뿐:
        # 라벨 자리는 세로선 13·17 과 용량 무시 가로 점선(73.4·96.0)에 닿지 않는다(렌더 확인). zorder 5 는 ○(6) 아래.
        ann = ax.annotate(lab, (s["required_capacity"], s["savings_pct"]), textcoords="offset points", xytext=(dx, dy),
                    fontsize=F_ANN, ha=ha, va="center", linespacing=1.2, zorder=5,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.4))
        if n in LEADER:   # 지시선: 라벨 윗변 바로 위에서 점 고리 바깥(반지름 약 2.9 pt)까지
            ax.annotate("", (s["required_capacity"], s["savings_pct"]), textcoords="offset points", xytext=LEADER[n],
                        arrowprops=dict(arrowstyle="-", lw=0.5, color=INK, shrinkA=0, shrinkB=3.2), zorder=5)
            ann.set_in_layout(False)   # 라벨이 축 오른쪽 끝을 조금 넘는다 — tight_layout 이 축을 줄이지 않게(그림 폭 안인지는 렌더로 확인)
    for suf, mk, col in (("", "o", INK), ("_a1", "s", GRAY)):
        pts = []
        for name in [f"cap/{c}{suf}" for c in ("0.50x", "0.75x", "1.00x", "1.50x", "2.00x", "3.00x")] + [f"main/joint{suf}"]:
            st = stats(name)
            if st:
                pts.append((max(st["peak_by_region"].values()), st["savings_pct"]))
        pts.sort()
        if pts:
            # 10-18(89 점검 [10]): 계열 이름 "CAST, knee" / "CAST, α=1"(표 3·7, 그림 7·10 과 같게). 곡선 끝 직접 라벨은
            # 새 용량 무시 가로 점선(73.39 가 CAST 곡선 끝 73.42 와 같은 높이)이 글자를 지나가 범례로 옮겼다.
            # 10-18(82 점검4 E [10](a)): ■ 는 3.2 → 2.8(그림 10 의 ■ 와 같게) — 3.2 면 CASPER ○ 고리와 틈이 0.2 pt 로 붙어 보였다
            ms = 3.2 if mk == "o" else 2.8
            # 10-18(78 점검6 E [6][9]): 캡션의 "■"(검정)와 맞게 ■ 를 검정으로(선은 회색 파선 그대로) — 회색 점선(용량 무시 α=1)과도 갈린다
            ax.plot([q[0] for q in pts], [q[1] for q in pts], color=col, lw=1.1, marker=mk, ms=ms,
                    mfc=INK, mec=INK, mew=1.0 if mk == "o" else 0.4, zorder=4, ls="-" if suf == "" else (0, (3, 1.5)),
                    label="CAST, knee" if suf == "" else "CAST, α=1")
            # 10-18(82 점검4 E [10](a)): CASPER ○(29, 95.30) 밑 흰 원(s 60, 반지름 약 3.9 pt)이 4.3 pt 옆 CAST α=1 ■(상한 26)을 반쯤 덮었다 →
            # 점만 한 번 더, 흰 원(4.5) 위·○ 고리(6) 아래인 zorder 5.2 로 찍는다. 선은 그대로 4 라 ○ 앞에서 끊기는 것은 유지.
            # ■(2.8) 와 ○ 고리는 서로 닿지 않는다(렌더 400% 확인).
            ax.plot([q[0] for q in pts], [q[1] for q in pts], ls="none", marker=mk, ms=ms, mfc=INK, mec=INK, mew=1.0 if mk == "o" else 0.4, zorder=5.2)
            # ↑ 검은 ■ 는 테두리 0.4(전 1.0, 겉 크기 3.8 → 3.2 pt): 1.0 이면 상한 26 의 ■ 와 CASPER ○ 고리 틈이 0.14 pt 라
            #   검정끼리 붙어 보였다(500 dpi 화소 1개). 그림 10 의 ■ 도 같은 크기로 맞췄다.
    # 10-18(89 점검 [4]): 그림 10 의 합성 패널을 지우고 그 용량 무시 수준(무릎점·α=1)을 이 그림에 가로 점선으로 옮겼다
    for ig_name, col, lab in (("main/ignore", INK, "Capacity ignored, knee"), ("main/ignore_a1", GRAY, "Capacity ignored, α=1")):
        ig = stats(ig_name)
        if ig:
            ax.axhline(ig["savings_pct"], color=col, lw=0.6, ls=(0, (1, 1.6)), zorder=1, label=lab)
    ax.axvline(13, color=AUX_GRAY, lw=0.6, ls=(0, (3, 2)), zorder=1)
    # 10-18(87 점검2 [15]): 6.5 → 6.6 pt(인쇄 6.0), 회색 #555 → #333
    ax.text(12.3, 45, "baseline peak", fontsize=F_LEG, color="#333333", ha="right", va="center", rotation=90,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.3))   # 10-18(89 [20]): 12.7 → 12.3 로 13 점선에서 떼고, 흰 바탕은 격자 40 만 가린다   # 10-18 렌더: 가로로 두면 y축이나 17 점선을 가로질러 세로로   # 10-18: 오른쪽이면 17 점선을 가로질러 왼쪽으로   # 아래쪽(위는 ceiling 라벨)
    ax.axvline(17, color=INK, lw=0.6, ls=(0, (1, 1.6)), zorder=1)          # 본문 상한 17
    ax.text(17.8, 103, "Ceiling 17", fontsize=F_LEG, color=INK, ha="left", va="bottom")   # 10-18: 6.5 → 6.6 pt, 그림 6·7 과 같은 "Ceiling 17"
    ax.set_xscale("log"); ax.set_xlim(6, 260); ax.set_ylim(0, 108)   # 10-18: 상한 7 점이 잘려 6 부터
    ax.set_xticks([10, 20, 50, 100, 200]); ax.set_xticklabels(["10", "20", "50", "100", "200"], fontsize=F_TICK)
    ax.set_xlabel("Required capacity (jobs)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    # 범례는 가운데 빈 띠(Suk. temporal (home) 라벨 22 와 Caspian 라벨 60 사이, 오른쪽)
    # 흰 바탕(테두리 없음)은 y 격자 40 이 범례 글자를 지나가지 않게 — 가리는 것은 격자뿐(렌더 확인)
    leg = ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.385), fontsize=F_LEG, frameon=True, handlelength=2.0, labelspacing=0.3,
                    borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white"); leg.get_frame().set_edgecolor("none"); leg.get_frame().set_alpha(1.0)
    save(fig, "priors")


# ── 그림: 역설 대조 — 예측 품질 다이얼. 위반(실선)과 최저 시각 동시 실행(점선), 분리형 ○ / 결합 ● ──
def fig_herding():
    fig, ax1 = new_ax()
    ax2 = ax1.twinx()
    order = [("lstm", "LSTM"), ("mix075", "λ=0.75"), ("mix05", "λ=0.5"), ("mix025", "λ=0.25"), ("oracle", "oracle")]
    any_data = False
    for eng, filled, lab in (("decoupled", False, "decoupled"), ("joint", True, "joint")):
        xs, viol, dip = [], [], []
        for key, l in order:
            name = f"main/{eng}" if key == "lstm" else (f"main/{eng}_oracle" if key == "oracle" else f"herd/{eng}_{key}")
            s = stats(name)
            if not s: continue
            xs.append(l); viol.append(s["capacity_violations"]); dip.append(s["herding"]["dip_occ_mean"])
        if not xs: continue
        any_data = True
        ax1.plot(xs, viol, color=INK, lw=1.1, marker="o", ms=3.2, mfc=INK if filled else "white", mec=INK, zorder=3, label=f"{lab}, violations")
        ax2.plot(xs, dip, color=GRAY, lw=0.9, ls=(0, (3, 1.5)), marker="s", ms=2.6, mfc=GRAY if filled else "white", mec=GRAY, zorder=2, label=f"{lab}, at min.")
    if not any_data:
        print("herding: 자료 없음"); return
    ax1.set_xlabel("Forecast quality λ", fontsize=F_LABEL)
    ax1.set_ylabel("Ceiling violations (jobs)", fontsize=F_LABEL)
    ax2.set_ylabel("Jobs at daily carbon min.", fontsize=F_LABEL - 0.8, color=GRAY)
    ax2.tick_params(axis="y", labelsize=F_TICK - 0.7, colors=GRAY); ax2.spines["top"].set_visible(False); ax2.spines["right"].set_color(GRAY)
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=F_LEG, frameon=False, handlelength=2.0)
    save(fig, "herding")


# ── 그림: 슬롯별 α 분포 — 합성 ■ / Azure □ ───────────────────────────────────────
def fig_alphadist():
    fig, ax = new_ax(h=150 / 72.0)
    any_data = False
    for name, filled in (("main/joint", True), ("azure/joint", False)):
        p = os.path.join(V2, name, "alpha.csv")
        if not os.path.exists(p): continue
        a = [float(r["alpha"]) for r in csv.DictReader(open(p)) if float(r["t"]) >= 168]
        vals, cnts = np.unique(np.round(a, 1), return_counts=True)
        ax.bar(vals + (-0.02 if filled else 0.02), 100 * cnts / cnts.sum(), width=0.04,
               color=INK if filled else "white", edgecolor=INK, lw=0.6, zorder=3, label="Synthetic" if filled else "Azure")
        any_data = True
    if not any_data:
        print("alphadist: 자료 없음"); return
    ax.set_xticks(np.arange(0, 1.01, 0.1)); ax.set_xticklabels([f"{v:.1f}" for v in np.arange(0, 1.01, 0.1)], fontsize=F_TICK - 0.7)
    ax.set_xlabel("α chosen per slot", fontsize=F_LABEL); ax.set_ylabel("Share of slots (%)", fontsize=F_LABEL)
    ax.legend(fontsize=F_LEG, frameon=False)
    save(fig, "alphadist")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = dict(alpha=fig_alpha, alpha_cast=fig_alpha_cast, capsweep=fig_capsweep, where=fig_where, priors=fig_priors, herding=fig_herding, alphadist=fig_alphadist)
    for k, f in fns.items():
        if which in (k, "all"):
            f()
