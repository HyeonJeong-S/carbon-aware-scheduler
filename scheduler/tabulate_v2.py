# -*- coding: utf-8 -*-
"""v2 실행 결과(stats.json) 를 한 줄씩 표로 뽑는다 — 브리프에 손 전사하지 않기 위한 도구.

사용:
  ./.venv/bin/python scheduler/tabulate_v2.py cap/0.50x cap/0.75x ...          # 행 출력
  ./.venv/bin/python scheduler/tabulate_v2.py --glob 'cap/*'                     # 이름 글롭
  ./.venv/bin/python scheduler/tabulate_v2.py --diff cap/0.50x_a1 cap/0.50x     # %포인트 차 = kg 차 ÷ 기준 kg
%포인트 차는 반올림한 절감률끼리 빼지 않고 kg 차를 기준 배출로 나눈 뒤 반올림한다(v2_검증지시.txt 규칙).
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "scheduler", "data", "v2")


def load(name):
    p = os.path.join(V2, name, "stats.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def cap_str(c):
    if isinstance(c, dict):
        return "{" + ",".join(f"{k.split('-')[-1][:3]}{v}" for k, v in c.items()) + "}"
    return str(c)


def peak_max(d):
    pk = d.get("peak_by_region") or {}
    return max(pk.values()) if pk else None


HDR = ("name", "sav%", "kg", "viol", "over_h", "forced", "lat_ms", "dw_ms", "delay_h", "home%",
       "alpha", "peak", "cap", "rho", "n/n_all", "wall_min")


def row(name, d):
    h = d.get("herding") or {}
    return (
        name,
        f"{d['savings_pct']:.2f}",
        f"{d['total_carbon_kg']:,.1f}",
        f"{d.get('capacity_violations', 0):,}",
        f"{sum((d.get('hours_over_by_region') or {}).values()):.1f}",
        f"{d.get('forced_admissions', 0):,}",
        f"{d['avg_latency_ms']:.1f}",
        f"{d.get('dw_latency_ms', float('nan')):.1f}",
        f"{d.get('avg_delay_h', float('nan')):.2f}",
        f"{100 * d.get('home_share', float('nan')):.1f}",
        f"{d.get('alpha_mean', float('nan')):.3f}",
        str(peak_max(d)),
        cap_str(d.get("cap")),
        str(d.get("rho")),
        f"{d.get('n', 0):,}/{d.get('n_all', 0):,}",
        f"{d.get('wall_s', 0) / 60:.1f}",
    )


def main(argv):
    if argv and argv[0] == "--diff":
        a, b = load(argv[1]), load(argv[2])
        base = a["baseline_kg"]
        dk = a["total_carbon_kg"] - b["total_carbon_kg"]
        print(f"{argv[1]} − {argv[2]}: {dk:,.1f} kg = {100 * dk / base:.2f} %p  "
              f"(절감률 {a['savings_pct']:.2f} vs {b['savings_pct']:.2f}; 기준 {base:,.1f} kg)")
        return
    names = []
    i = 0
    while i < len(argv):
        if argv[i] == "--glob":
            pat = os.path.join(V2, argv[i + 1], "stats.json")
            names += sorted(os.path.relpath(os.path.dirname(p), V2) for p in glob.glob(pat))
            i += 2
        else:
            names.append(argv[i])
            i += 1
    rows = [HDR]
    for n in names:
        d = load(n)
        rows.append(row(n, d) if d else (n, "(없음)") + ("",) * (len(HDR) - 2))
    w = [max(len(r[c]) for r in rows) for c in range(len(HDR))]
    for r in rows:
        print(" | ".join(r[c].rjust(w[c]) if c else r[c].ljust(w[c]) for c in range(len(HDR))))


if __name__ == "__main__":
    main(sys.argv[1:])
