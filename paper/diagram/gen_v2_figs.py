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
F_LABEL, F_TICK, F_ANN, F_LEG = 8.8, 7.7, 7.1, 6.0
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


def knee_marker(ax, x, y, filled=True):
    ax.scatter([x], [y], s=34, facecolor=INK if filled else "white", edgecolor=INK, lw=0.8, zorder=4)
    ax.scatter([x], [y], s=150, facecolor="none", edgecolor=INK, lw=1.6, zorder=5)


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
        ax.plot([h[0] for h in H], [100 * (1 - h[1] / base) for h in H], color=INK if filled else GRAY, lw=1.1, zorder=2)
        ax.scatter(xs, ys, s=14, facecolor=INK if filled else "white", edgecolor=INK, lw=0.8, zorder=3)
        kx, ky = r["knee"][0], 100 * (1 - r["knee"][1] / base)
        knee_marker(ax, kx, ky, filled=filled)
        # 라벨은 양 끝 α 와 무릎점만. 결합(●)은 위·왼쪽, 분리형(○)은 아래·오른쪽에 적어 서로 피한다(렌더 확인 10-17).
        dy = 6 if filled else -12
        if filled:
            ax.annotate("α=0", (xs[0], ys[0]), textcoords="offset points", xytext=(7, 1), fontsize=F_ANN, ha="left")
        ax.annotate("α=1", (xs[-1], ys[-1]), textcoords="offset points", xytext=(-4, dy), fontsize=F_ANN, ha="right")
        if filled:
            ax.annotate("knee", (kx, ky), textcoords="offset points", xytext=(-4, 8), fontsize=F_ANN, ha="right")
        else:
            ax.annotate("knee", (kx, ky), textcoords="offset points", xytext=(10, -5), fontsize=F_ANN, ha="left")
        ax.plot([], [], color=INK if filled else GRAY, lw=1.1, marker="o", ms=3.5, mfc=INK if filled else "white", mec=INK,
                label="CAST" if filled else "Decoupled")   # 표 5·본문과 같은 이름
        drawn += 1
    if not drawn:
        print("alpha: 자료 없음"); return
    ax.set_xlabel("Mean latency (ms)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    ax.set_xlim(-6, 130); ax.set_ylim(-4, 100)
    ax.legend(fontsize=F_LEG, frameon=False, loc="lower right", handlelength=2.0)
    save(fig, "alpha")


# ── 그림: 용량비 스윕 — 절감(무릎점 실선·α=1 점선), 초과 시간(막대), 합성 ●/Azure ○ ──
def fig_capsweep():
    """상한 스윕 — 절감(무릎점 ● 실선, α=1 ■ 점선) 대 상한 배수. 10-17: 오른쪽 '초과 시간' 축과 막대는 뺐다 — 전 상한에서 0 이라
    (그것이 결과) 축이 비어 보였고, 로그축 보조 눈금 라벨이 0.5× 와 겹쳤다. 용량 무시 수준을 가는 점선 기준선으로 둔다."""
    from matplotlib.ticker import NullFormatter, NullLocator
    fig, ax = new_ax()
    levels = [("0.50x", 0.5), ("0.75x", 0.75), ("1.00x", 1.0), ("1.50x", 1.5), ("2.00x", 2.0), ("3.00x", 3.0)]
    any_data = False
    for pre, main_name, filled, lab in (("cap/", "main/joint", True, "Synthetic"), ("azure/cap_", "azure/joint", False, "Azure")):
        for suf_a, mk, ls, col, name in (("", "o", "-", INK, "knee α"), ("_a1", "s", (0, (3, 1.5)), GRAY, "α=1")):   # 범례 이름은 표 4 와 같게(CAST, knee α / CAST, α=1)
            rows = []
            for suf, x in levels:
                st = stats(pre + suf + suf_a)
                if st: rows.append((x, st["savings_pct"]))
            m = stats(main_name + suf_a)
            if m: rows.append((1.25, m["savings_pct"]))
            rows.sort()
            if not rows:
                continue
            any_data = True
            series = ("CAST" if filled else "CAST on Azure")
            ax.plot([r[0] for r in rows], [r[1] for r in rows], color=col, lw=1.1 if suf_a == "" else 0.9, ls=ls, marker=mk,
                    ms=3.2 if mk == "o" else 2.6, mfc=col if filled else "white", mec=col, zorder=3, label=f"{series}, {name}")
            # 용량 무시 수준 — 가는 점선 기준선(같은 계열 색)
            ig = stats(("main/ignore" if pre == "cap/" else "azure/ignore") + suf_a)
            if ig:
                ax.axhline(ig["savings_pct"], color=col, lw=0.6, ls=(0, (1, 1.6)), zorder=1,
                           label=("Capacity ignored" if (filled and suf_a == "") else None))
    if not any_data:
        print("capsweep: 자료 없음"); return
    ax.set_xscale("log")
    ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.5, 0.75, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.5×", "0.75×", "1×", "1.5×", "2×", "3×"], fontsize=F_TICK)
    ax.set_xlim(0.45, 3.4)
    ax.set_xlabel("Capacity (× baseline peak)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
    ax.set_ylim(50, 100)
    ax.legend(loc="lower right", fontsize=F_LEG, frameon=False, handlelength=2.0)
    save(fig, "capsweep")


# ── 그림: 어디서 무는가 — 리전별 시간 이동 이득 몫 vs σ (원 크기 = 초과 시간 몫); 별도로 CAL 현지 시각 ──
def fig_where():
    p = os.path.join(V2, "analysis", "regions_main.json")
    if not os.path.exists(p):
        print("where: regions_main.json 없음"); return
    r = json.load(open(p))
    fig, ax = new_ax()
    regs = list(r["swing_abs"].keys())
    # 10-17: x 축은 상대 σ 가 아니라 절대 변동(일별 최대−최소 평균) — 시간 이득은 이것을 따른다(FR σ 0.97·이득 0.3%).
    xs = [r["swing_abs"][g] for g in regs]; ys = [100 * r["temporal_gain_share"][g] for g in regs]
    ho = r.get("ignore", {}).get("hours_over_share", {g: 0 for g in regs})
    # 원 넓이 = 용량 무시 실행에서 상한을 넘긴 시간의 몫(CAL 55.6%, FR 37.7%, JP 6.7%, 나머지 0 → 작은 점)
    ax.scatter(xs, ys, s=[14 + 420 * ho.get(g, 0) for g in regs], facecolor="white", edgecolor=INK, lw=0.9, zorder=3)
    short = {"US-CAL-CISO": "CAL", "US-TEX-ERCO": "TEX", "US-NY-NYIS": "NY", "FR": "FR", "DE": "DE", "KR": "KR", "IN": "IN", "JP": "JP"}
    # 점 라벨 자리(렌더 확인 뒤 손으로): CAL 큰 원 → 오른쪽 위, FR 큰 원(왼쪽 끝) → 오른쪽, 나머지 오른쪽 아래
    # 렌더(10-17 00:30)에서 JP·CAL 라벨이 겹치고 FR 라벨이 NY 원에 가렸다 → CAL 은 큰 원 왼쪽, JP 는 위, FR 은 원 위.
    off = {"CAL": (-13, -4, "right"), "JP": (0, 7, "center"), "FR": (0, 14, "center"), "NY": (7, -3, "left"), "KR": (5, -8, "left")}
    for g, x, y in zip(regs, xs, ys):
        dx, dy, ha = off.get(short[g], (5, -2, "left"))
        ax.annotate(short[g], (x, y), textcoords="offset points", xytext=(dx, dy), fontsize=F_ANN, ha=ha)
    ax.set_xlim(0, max(xs) * 1.18); ax.set_ylim(-1.5, max(ys) * 1.25)
    ax.set_xlabel("Mean daily range of intensity (gCO₂/kWh)", fontsize=F_LABEL)
    ax.set_ylabel("Share of temporal savings (%)", fontsize=F_LABEL)
    save(fig, "where")
    # 둘째 판: 상한을 넘긴 시각의 현지 시간 분포 — 캘리포니아(채움, 한낮) 대 프랑스(빈 막대, 한밤)
    fig, ax = new_ax(h=150 / 72.0)
    hc = np.array(r.get("ignore", {}).get("local_hist_CAL", [0] * 24)); hf = np.array(r.get("ignore", {}).get("local_hist_FR", [0] * 24))
    x = np.arange(24)
    ax.bar(x - 0.2, 100 * hc / max(hc.sum(), 1e-9), color=INK, width=0.4, zorder=3, label="California")
    ax.bar(x + 0.2, 100 * hf / max(hf.sum(), 1e-9), facecolor="white", edgecolor=INK, lw=0.6, width=0.4, zorder=3, label="France")
    ax.set_xticks([0, 6, 12, 18]); ax.set_xlim(-0.7, 23.7)
    ax.set_xlabel("Local hour", fontsize=F_LABEL)
    ax.set_ylabel("Share of hours over ceiling (%)", fontsize=F_LABEL)
    ax.legend(fontsize=F_LEG, frameon=False, loc="upper right", handlelength=1.2)
    save(fig, "where_hours")


# ── 그림: 선행 정책 평면 — 절감 vs 필요 용량. ○ 선행, ● CAST 곡선(용량비 스윕의 자기 피크) ──
def fig_priors():
    fig, ax = new_ax()
    # (라벨, dx, dy, ha) — 점마다 지정. 오른쪽 끝(Sukprasert 둘)은 왼쪽으로 적어 축 밖으로 안 나가게.
    # 그림 안 글자는 짧은 이름만 — 뜻은 캡션에서 푼다 (S-T: Sukprasert temporal, S-ST: spatial+temporal, h: 홈 고정)
    # 10-17: 라벨은 표 7 의 이름과 같게(92 지적 — 그림·표 이름 일치 규칙)
    # 렌더(10-17): CASPER 라벨이 α=1 곡선 점(26·39)에 걸리고 S+T 라벨이 "CAST α=1" 과 겹쳐 자리 조정
    labels = {"cics": ("CICS", 6, -1, "left"), "casper": ("CASPER", 0, -11, "center"),   # CASPER 는 α=1 곡선 위에 놓이는 점 — 라벨은 곡선 아래
              "suk_home": ("Suk. temporal (home)", 6, -1, "left"),
              "suk_lb": ("Suk. temporal (ours)", 6, -1, "left"),        # CAST 가 정한 리전 위의 Sukprasert 시간 이동(92 지적)
              "suk_st": ("Suk. spatial+temporal", 0, -11, "center"),  # 오른쪽 끝 점 — 왼쪽으로 적으면 α=1 곡선을 가로지르므로 점 아래
              "caspian_w1.0_frac": ("Caspian", 6, -1, "left")}
    for p in glob.glob(os.path.join(V2, "priors", "*.json")):
        j = json.load(open(p)); s = j["at_cap"]; n = j["name"]
        if n == "baseline":
            continue
        ax.scatter([s["required_capacity"]], [s["savings_pct"]], s=24, facecolor="white", edgecolor=INK, lw=0.9, zorder=3)
        lab, dx, dy, ha = labels.get(n, (n, 6, -1, "left"))
        ax.annotate(lab, (s["required_capacity"], s["savings_pct"]), textcoords="offset points", xytext=(dx, dy),
                    fontsize=F_ANN, ha=ha, va="center", linespacing=1.2)
    for suf, mk, col in (("", "o", INK), ("_a1", "s", GRAY)):
        pts = []
        for name in [f"cap/{c}{suf}" for c in ("0.50x", "0.75x", "1.00x", "1.50x", "2.00x", "3.00x")] + [f"main/joint{suf}"]:
            st = stats(name)
            if st:
                pts.append((max(st["peak_by_region"].values()), st["savings_pct"]))
        pts.sort()
        if pts:
            ax.plot([q[0] for q in pts], [q[1] for q in pts], color=col, lw=1.1, marker=mk, ms=3.2,
                    mfc=col, mec=col, zorder=4, ls="-" if suf == "" else (0, (3, 1.5)))
            if suf == "":
                ax.annotate("CAST", pts[-1], textcoords="offset points", xytext=(6, -1), fontsize=F_ANN, ha="left", color=col)
            else:   # α=1 곡선 라벨은 곡선 가운데 위(CASPER 라벨은 곡선 아래)
                mid = pts[len(pts) // 2]
                ax.annotate("CAST α=1", mid, textcoords="offset points", xytext=(0, 6), fontsize=F_ANN, ha="center", color=col)
    ax.axvline(13, color=AUX_GRAY, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.text(13.4, 1.5, "baseline peak", fontsize=F_ANN - 0.6, color="#555555", ha="left", va="bottom")   # 아래쪽(위는 ceiling 라벨)
    ax.axvline(17, color=INK, lw=0.6, ls=(0, (1, 1.6)), zorder=1)          # 본문 상한 17
    ax.text(17.4, 103, "ceiling 17", fontsize=F_ANN - 0.6, color=INK, ha="left", va="bottom")
    ax.set_xscale("log"); ax.set_xlim(9, 260); ax.set_ylim(0, 108)
    ax.set_xticks([10, 20, 50, 100, 200]); ax.set_xticklabels(["10", "20", "50", "100", "200"], fontsize=F_TICK)
    ax.set_xlabel("Required capacity (jobs)", fontsize=F_LABEL)
    ax.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
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
    fns = dict(alpha=fig_alpha, capsweep=fig_capsweep, where=fig_where, priors=fig_priors, herding=fig_herding, alphadist=fig_alphadist)
    for k, f in fns.items():
        if which in (k, "all"):
            f()
