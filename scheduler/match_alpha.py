# -*- coding: utf-8 -*-
"""무릎점과 같은 평균 지연을 내는 고정 α 를 이분법으로 찾아 실제로 돌린다(92 제안 10-17: 보간 없는 비교).
    ./.venv/bin/python -m scheduler.match_alpha --engine decoupled --target 23.4 --lo 0.4 --hi 0.5 --prefix alpha/decoupled_m
    (--extra 로 run_v2 추가 인자, 예: --extra "--cap 0.75" / --extra "--jobs load_balancer/data/jobs_azure.csv")
결과: 실행마다 scheduler/data/v2/<prefix><α>/stats.json; 끝나면 표 한 줄씩 출력. 지연 단조 증가(α↑ → 지연↑)를 가정.
"""
import argparse, json, os, shlex, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(name, engine, alpha, extra):
    p = os.path.join(ROOT, "scheduler/data/v2", name, "stats.json")
    if not os.path.exists(p):
        cmd = [os.path.join(ROOT, ".venv/bin/python"), "-m", "scheduler.run_v2", "--name", name, "--engine", engine, "--alpha", f"{alpha:.4f}"] + shlex.split(extra)
        log = os.path.join(ROOT, "scheduler/data/v2/logs", name.replace("/", "_") + ".log")
        with open(log, "w") as f:
            subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    s = json.load(open(p))
    return s["avg_latency_ms"], s["dw_latency_ms"], s["savings_pct"], s["total_carbon_kg"], s["capacity_violations"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="joint"); ap.add_argument("--target", type=float, required=True, help="무릎점 평균 지연 ms")
    ap.add_argument("--lo", type=float, required=True); ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--tol", type=float, default=0.5); ap.add_argument("--max-runs", type=int, default=5)
    ap.add_argument("--prefix", required=True); ap.add_argument("--extra", default="")
    ap.add_argument("--axis", choices=["mean", "dw"], default="mean", help="맞출 지연 축: 작업당 평균(mean) 또는 실행시간 가중(dw, 3.4 무릎점 규칙의 축)")
    a = ap.parse_args()
    lo, hi = a.lo, a.hi
    rows = []
    for k in range(a.max_runs):
        mid = (lo + hi) / 2
        name = f"{a.prefix}{mid:.4f}"
        lat0, dw, save, kg, viol = run(name, a.engine, mid, a.extra)
        lat = dw if a.axis == "dw" else lat0
        rows.append((mid, lat, dw, save, kg, viol))
        print(f"[{k+1}] α={mid:.4f}  {a.axis} {lat:.2f} ms (dw {dw:.2f})  save {save:.2f}%  kg {kg:,.1f}  viol {viol}", flush=True)
        if abs(lat - a.target) <= a.tol:
            print("MATCHED", flush=True); break
        if lat < a.target: lo = mid
        else: hi = mid
    best = min(rows, key=lambda r: abs(r[1] - a.target))
    print(f"BEST α={best[0]:.4f} lat {best[1]:.2f} (target {a.target}) save {best[3]:.2f}% kg {best[4]:,.1f} viol {best[5]}")

if __name__ == "__main__":
    main()
