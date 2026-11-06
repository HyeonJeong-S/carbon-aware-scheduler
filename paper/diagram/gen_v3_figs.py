"""v3 그림 중 새로 그리는 것. 글꼴·크기·색은 gen_v2_figs 의 규약을 그대로 쓴다.
  arrivals : 현지 시각별 도착 비율(합성 등급 1~2, 합성 등급 3~5, Azure) → v3_fig4_arrivals
  priors2  : 선행 정책 비교 두 칸 — (a) 절감 대 필요 용량, (b) 절감 대 왕복 지연 시간 → v3_fig6_priors2
    ./.venv/bin/python paper/diagram/gen_v3_figs.py arrivals | priors2 | all
"""
import csv
import glob
import json
import os
import sys

import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_v2_figs import (  # noqa: E402
    AUX_GRAY,
    F_ANN,
    F_LABEL,
    F_LEG,
    F_TICK,
    GRAY,
    INK,
    V2,
    W_IN,
    knee_marker,
    stats,
)

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "load_balancer", "data"))


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4, zorder=0)
    ax.tick_params(labelsize=F_TICK)


def save(fig, name):
    out = os.path.join(HERE, f"{name}.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))
    plt.close(fig)
    print("wrote", out)


def hour_shares(path, keep):
    counts = [0] * 24
    with open(path) as f:
        for r in csv.DictReader(f):
            if keep(int(r["k"])):
                counts[int(float(r["submit_local_hour"])) % 24] += 1
    n = sum(counts)
    return [100 * c / n for c in counts]


def fig_arrivals():
    syn = os.path.join(DATA, "jobs.csv")
    azu = os.path.join(DATA, "jobs_azure.csv")
    series = [
        (hour_shares(syn, lambda k: k <= 2), INK, "-", "Syn. 1–2"),
        (hour_shares(syn, lambda k: k >= 3), INK, (0, (3, 1.5)), "Syn. 3–5"),
        (hour_shares(azu, lambda k: True), GRAY, "-", "Azure"),
    ]
    fig, ax = plt.subplots(figsize=(W_IN, 150 / 72.0), dpi=500)
    style(ax)
    hours = list(range(24))
    for ys, col, ls, lab in series:
        ax.plot(hours, ys, color=col, lw=1.1, ls=ls, label=lab, zorder=3)
    ax.set_xlim(0, 23)
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_ylim(0, 12.5)
    ax.set_xlabel("Local hour of submission", fontsize=F_LABEL)
    ax.set_ylabel("Share of jobs (%)", fontsize=F_LABEL)
    leg = ax.legend(fontsize=F_LEG, frameon=False, loc="upper center", ncol=3, handlelength=1.6, columnspacing=0.8, borderpad=0.1, bbox_to_anchor=(0.5, 1.03))
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")
    fig.tight_layout(pad=0.5)
    save(fig, "v3_fig4_arrivals")


def prior(name):
    for p in glob.glob(os.path.join(V2, "priors", "*.json")):
        with open(p) as f:
            j = json.load(f)
        if j["name"] == name:
            return j["at_cap"]
    raise SystemExit(f"priors: {name} 없음")


def fig_priors2():
    suk, cas = prior("suk_st"), prior("caspian_w1.0_frac")
    fig, (a, b) = plt.subplots(2, 1, figsize=(W_IN, 330 / 72.0), dpi=500)
    for q in (a, b):
        style(q)
        q.set_ylabel("Carbon savings (%)", fontsize=F_LABEL)
        q.set_ylim(0, 108)

    # (a) 절감 대 필요 용량 — CAST 는 상한을 7~39 로 바꾼 무릎점·α=1, 선행 정책은 ○
    for suf, mk, col, ls, lab in (("", "o", INK, "-", "CAST, knee"), ("_a1", "s", GRAY, (0, (3, 1.5)), "CAST, α=1")):
        pts = []
        for nm in [f"cap/{c}{suf}" for c in ("0.50x", "0.75x", "1.00x", "1.50x", "2.00x", "3.00x")] + [f"main/joint{suf}"]:
            st = stats(nm)
            if st:
                pts.append((max(st["peak_by_region"].values()), st["savings_pct"]))
        pts.sort()
        a.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.1, ls=ls, marker=mk,
               ms=3.0 if mk == "o" else 2.8, mfc=INK, mec=INK, zorder=4, label=lab)
    for nm, lab in (("main/ignore", "No ceiling, knee"), ("main/ignore_a1", "No ceiling, α=1")):
        st = stats(nm)
        a.axhline(st["savings_pct"], color=INK if nm.endswith("ignore") else GRAY, lw=0.6, ls=(0, (1, 1.6)), zorder=1, label=lab)
    for s, lab, dx, dy, ha in ((suk, "Sukprasert", -6, -9, "right"), (cas, "Caspian", 6, -2, "left")):
        a.scatter([s["required_capacity"]], [s["savings_pct"]], s=60, facecolor="white", edgecolor="none", zorder=4.5)
        a.scatter([s["required_capacity"]], [s["savings_pct"]], s=24, facecolor="white", edgecolor=INK, lw=0.9, zorder=6)
        a.annotate(lab, (s["required_capacity"], s["savings_pct"]), textcoords="offset points", xytext=(dx, dy),
                   fontsize=F_ANN, ha=ha, va="center")
    a.axvline(13, color=AUX_GRAY, lw=0.6, ls=(0, (3, 2)), zorder=1)
    a.axvline(17, color=INK, lw=0.6, ls=(0, (1, 1.6)), zorder=1)
    a.text(17.8, 103, "Ceiling 17", fontsize=F_LEG, ha="left", va="bottom")
    a.set_xscale("log")
    a.set_xlim(6, 260)
    a.set_xticks([10, 20, 50, 100, 200])
    a.set_xticklabels(["10", "20", "50", "100", "200"], fontsize=F_TICK)
    a.set_xlabel("(a) Required capacity (jobs)", fontsize=F_LABEL)
    leg = a.legend(fontsize=F_LEG, frameon=True, loc="center right", bbox_to_anchor=(1.0, 0.36), handlelength=2.0,
                   labelspacing=0.25, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")

    # (b) 절감 대 왕복 지연 시간 — CAST 의 고정 α 곡선(α=0~1), 무릎점, 선행 정책
    names = [f"alpha/{x:.1f}" for x in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)] + ["main/joint_a1"]
    curve = [stats(nm) for nm in names]
    b.plot([s["dw_latency_ms"] for s in curve], [s["savings_pct"] for s in curve], color=INK, lw=1.1, marker="o", ms=2.4,
           mfc=INK, mec=INK, zorder=4, label="CAST, fixed α")
    knee = stats("main/joint")
    knee_marker(b, knee["dw_latency_ms"], knee["savings_pct"])
    b.annotate("CAST, knee", (knee["dw_latency_ms"], knee["savings_pct"]), textcoords="offset points", xytext=(7, -9),
               fontsize=F_ANN, ha="left", va="center")
    for s, lab, dx, dy, ha in ((suk, "Sukprasert", -6, 7, "right"), (cas, "Caspian", 6, -6, "left")):
        b.scatter([s["dw_latency_ms"]], [s["savings_pct"]], s=60, facecolor="white", edgecolor="none", zorder=4.5)
        b.scatter([s["dw_latency_ms"]], [s["savings_pct"]], s=24, facecolor="white", edgecolor=INK, lw=0.9, zorder=6)
        b.annotate(lab, (s["dw_latency_ms"], s["savings_pct"]), textcoords="offset points", xytext=(dx, dy),
                   fontsize=F_ANN, ha=ha, va="center")
    b.set_xlim(-5, 130)
    b.set_xlabel("(b) Duration-weighted mean RTT (ms)", fontsize=F_LABEL)
    leg = b.legend(fontsize=F_LEG, frameon=True, loc="lower right", handlelength=2.0, borderpad=0.2, fancybox=False)
    leg.get_frame().set_facecolor("white")
    leg.get_frame().set_edgecolor("none")
    fig.align_ylabels([a, b])
    fig.tight_layout(pad=0.5, h_pad=0.8)
    save(fig, "v3_fig6_priors2")


def fig_capacity():
    """3.5절 용량 관리 개념도 — 한 리전의 동시 실행 수를 이번 슬롯의 시작 순간(U_t)과 미래 슬롯(σ)에서 센다. 값은 설명용."""
    cap, rho = 10, 2
    xs = [0, 0.7, 1.4, 2.7, 3.7, 4.7, 6.2]
    labels = ["$t$", "", "", "$t{+}1$", "$t{+}2$", "$t{+}3$", "$t{+}H$"]
    running = [7, 6, 6, 4, 3, 2, 0]
    planned = [3, 5, 4, 4, 6, 5, 3]
    fig, ax = plt.subplots(figsize=(W_IN, 150 / 72.0), dpi=500)
    style(ax)
    ax.grid(False)
    for k, (x, n, p) in enumerate(zip(xs, running, planned)):
        w = 0.45 if k < 3 else 0.7
        ax.bar(x, n, w, color=GRAY, edgecolor=INK, lw=0.6, zorder=3, label="Running $n_r(\\kappa)$" if k == 0 else None)
        ax.bar(x, min(p, cap - n), w, bottom=n, color="white", edgecolor=INK, lw=0.6, zorder=3,
               label="Planned $\\sum x_{jri}$" if k == 0 else None)
        if n + p > cap:
            ax.bar(x, n + p - cap, w, bottom=cap, color="white", edgecolor=INK, lw=0.6, hatch="////", zorder=3,
                   label="Excess $z^A$, $z^B$")
        if k >= 3 and n + p > cap - rho:
            ax.bar(x, n + p - (cap - rho), w, bottom=cap - rho, color="white", edgecolor=INK, lw=0.6, hatch="////",
                   zorder=3)
    ax.text(5.45, 1.5, "…", ha="center", va="center", fontsize=F_LABEL)
    ax.plot([-0.4, 6.7], [cap, cap], color=INK, lw=0.9, zorder=4)
    ax.text(6.75, cap, "cap$_r$", fontsize=F_ANN, ha="left", va="center")
    ax.plot([2.2, 6.7], [cap - rho, cap - rho], color=INK, lw=0.8, ls=(0, (3, 2)), zorder=4)
    ax.text(6.75, cap - rho, "cap$_r-\\rho_r$", fontsize=F_ANN, ha="left", va="center")
    for x0, x1, lab in ((-0.3, 1.7, "Start instants $U_t$"), (2.3, 6.6, "Future slots $\\sigma$")):
        ax.annotate("", (x0, -2.6), (x1, -2.6), xycoords="data", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
        ax.text((x0 + x1) / 2, -2.9, lab, ha="center", va="top", fontsize=F_ANN)
    ax.axvline(2.05, color=AUX_GRAY, lw=0.6, ls=(0, (1, 1.6)), zorder=1)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=F_TICK)
    ax.set_xlim(-0.45, 7.9)
    ax.set_ylim(0, 13.8)
    ax.set_yticks([])
    ax.set_ylabel("Jobs running in region $r$", fontsize=F_LABEL)
    leg = ax.legend(fontsize=F_LEG, frameon=False, loc="upper center", ncol=3, handlelength=1.2, columnspacing=0.6,
                    handletextpad=0.4, borderpad=0.1, bbox_to_anchor=(0.5, 1.06))
    leg.get_frame().set_facecolor("white")
    fig.tight_layout(pad=0.5)
    fig.subplots_adjust(bottom=0.3)
    save(fig, "v3_fig3_capacity")


def fig_compare():
    """선행 정책 비교 막대(표 10을 그림으로) — 절감, 필요 용량, 마감 위반을 세 칸에. 값은 priors json·main 실행에서 읽는다."""
    suk, cas = prior("suk_st"), prior("caspian_w1.0_frac")
    knee, a1 = stats("main/joint"), stats("main/joint_a1")
    rows = [
        ("Sukprasert", suk["savings_pct"], suk["required_capacity"], suk["slo_violations"], "white"),
        ("Caspian", cas["savings_pct"], cas["required_capacity"], cas["slo_violations"], "white"),
        ("CAST, α=1", a1["savings_pct"], max(a1["peak_by_region"].values()), a1["slo_violations"], GRAY),
        ("CAST, knee", knee["savings_pct"], max(knee["peak_by_region"].values()), knee["slo_violations"], INK),
    ]
    names = [r[0] for r in rows]
    ys = list(range(len(rows)))[::-1]
    fig, axes = plt.subplots(3, 1, figsize=(W_IN, 250 / 72.0), dpi=500, sharey=True)
    panels = (("(a) Carbon savings (%)", 1, (0, 108), "{:.1f}"),
              ("(b) Required capacity (jobs)", 2, (0, 150), "{:d}"),
              ("(c) Deadline misses (jobs)", 3, (0, 7000), "{:,}"))
    for ax, (lab, k, lim, fmt) in zip(axes, panels):
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color="#dddddd", lw=0.4, zorder=0)
        for y, r in zip(ys, rows):
            v = r[k]
            ax.barh(y, v, height=0.62, color=r[4], edgecolor=INK, lw=0.6, zorder=3)
            ax.text(v + lim[1] * 0.012, y, fmt.format(int(round(v)) if k > 1 else v), va="center", ha="left",
                    fontsize=F_ANN, zorder=4)
        if k == 2:
            ax.axvline(17, color=INK, lw=0.6, ls=(0, (1, 1.6)), zorder=2)
            ax.text(18.5, ys[0] + 0.45, "Ceiling 17", fontsize=F_LEG, ha="left", va="bottom")
        ax.set_xlim(*lim)
        ax.set_yticks(ys)
        ax.set_yticklabels(names, fontsize=F_TICK)
        ax.set_xlabel(lab, fontsize=F_LABEL)
        ax.tick_params(axis="y", length=0)
    axes[2].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout(pad=0.5, h_pad=0.6)
    save(fig, "v3_fig7_compare")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k, fn in (("arrivals", fig_arrivals), ("priors2", fig_priors2), ("capacity", fig_capacity), ("compare", fig_compare)):
        if which in (k, "all"):
            fn()
