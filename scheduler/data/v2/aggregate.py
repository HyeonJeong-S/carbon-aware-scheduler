# -*- coding: utf-8 -*-
"""v2 결과 모으기 — scheduler/data/v2/**/stats.json + priors/*.json → summary.csv / summary.md

    ./.venv/bin/python scheduler/data/v2/aggregate.py [--md]
"""
import glob, json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
COLS = ["name", "n_jobs", "baseline_kg", "total_carbon_kg", "savings_pct", "capacity_violations",
        "over_cap_forced", "over_cap_immediate", "over_cap_normal", "scored_cap", "peak", "hours_over",
        "slo_violations", "forced_admissions", "avg_latency_ms", "p95_latency_ms", "home_share",
        "avg_delay_h", "alpha_mean", "solve_ms_mean", "solve_ms_p95", "solve_ms_max", "n_mip", "n_slots",
        "max_vars", "wall_min", "engine", "forecast", "alpha_setting", "cap", "rho", "jobs_csv"]
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, "*", "*", "stats.json")) + glob.glob(os.path.join(ROOT, "*", "stats.json"))):
    s = json.load(open(p))
    pk = s.get("peak_by_region") or {}
    ho = s.get("hours_over_by_region") or {}
    rows.append(dict(
        name=s.get("name", os.path.relpath(os.path.dirname(p), ROOT)), n_jobs=s.get("n_jobs") or s.get("n"),
        baseline_kg=s.get("baseline_kg"), total_carbon_kg=s.get("total_carbon_kg"), savings_pct=s.get("savings_pct"),
        capacity_violations=s.get("capacity_violations"), over_cap_forced=s.get("over_cap_forced"),
        over_cap_immediate=s.get("over_cap_immediate"), over_cap_normal=s.get("over_cap_normal"),
        scored_cap=s.get("scored_cap") or s.get("scored_cap_eff"), peak=max(pk.values()) if pk else s.get("peak_concurrency"),
        hours_over=round(sum(ho.values()), 2) if ho else None, slo_violations=s.get("slo_violations"),
        forced_admissions=s.get("forced_admissions"), avg_latency_ms=s.get("avg_latency_ms"),
        p95_latency_ms=s.get("p95_latency_ms"), home_share=s.get("home_share"), avg_delay_h=s.get("avg_delay_h"),
        alpha_mean=s.get("alpha_mean"), solve_ms_mean=s.get("solve_ms_mean"), solve_ms_p95=s.get("solve_ms_p95"),
        solve_ms_max=s.get("solve_ms_max"), n_mip=s.get("n_mip"), n_slots=s.get("n_slots"), max_vars=s.get("max_vars"),
        wall_min=round(s["wall_s"] / 60, 1) if s.get("wall_s") else None, engine=s.get("engine"),
        forecast=s.get("forecast"), alpha_setting=s.get("alpha_setting"), cap=s.get("cap"), rho=s.get("rho"),
        jobs_csv=os.path.basename(str(s.get("jobs_csv", ""))),
    ))
for p in sorted(glob.glob(os.path.join(ROOT, "priors", "*.json"))):
    s = json.load(open(p)); a = s["at_cap16"]; b = s["at_cap12"]
    pk = a.get("peak_by_region") or {}; ho = a.get("hours_over_by_region") or {}
    rows.append(dict(name="prior/" + s["name"], n_jobs=a["n"], baseline_kg=a.get("baseline_kg"),
                     total_carbon_kg=a["total_carbon_kg"], savings_pct=a.get("savings_pct"),
                     capacity_violations=a["capacity_violations"], scored_cap=a.get("scored_cap"),
                     peak=a.get("required_capacity"), hours_over=round(sum(ho.values()), 2) if ho else None,
                     slo_violations=a["deadline_misses"], avg_latency_ms=a["avg_latency_ms"],
                     wall_min=round(a["wall_s"] / 60, 1) if a.get("wall_s") else None, engine="prior",
                     cap=12, rho=b["capacity_violations"]))   # rho 열에 위반@12 를 임시로 (prior 행만)

import csv
with open(os.path.join(ROOT, "summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
    for r in rows: w.writerow({c: r.get(c) for c in COLS})

def fmt(v, nd=2):
    if v is None: return ""
    if isinstance(v, float): return f"{v:,.{nd}f}"
    return str(v)
hdr = ["name", "savings_pct", "total_carbon_kg", "capacity_violations", "peak", "hours_over", "slo_violations",
       "avg_latency_ms", "avg_delay_h", "alpha_mean", "solve_ms_mean", "n_mip", "wall_min"]
lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
for r in rows:
    lines.append("| " + " | ".join(fmt(r.get(c)) for c in hdr) + " |")
open(os.path.join(ROOT, "summary.md"), "w").write("\n".join(lines) + "\n")
print(f"{len(rows)} rows → summary.csv / summary.md")
if "--md" in sys.argv:
    print("\n".join(lines))
