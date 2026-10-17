# -*- coding: utf-8 -*-
"""조건별 '같은 지연 짝' 이분법 드라이버(표 6). 조건마다 무릎점 실행의 평균 지연을 과녁으로,
이미 있는 고정 α 실행(격자·이전 이분법)에서 과녁을 사이에 두는 가장 좁은 구간을 골라 match_alpha 를 돌린다.
    ./.venv/bin/python scheduler/data/v2/pair_driver.py [--only sn24,oracle] [--par 2] [--dry]
무릎점 stats.json 이 아직 없는 조건은 건너뛴다(나중에 다시 부르면 이어서 한다).
"""
import argparse, glob, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
ROOT = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler"
V2 = os.path.join(ROOT, "scheduler/data/v2")
J = "load_balancer/data/variants/jobs_seed{s}.csv"
# (조건, 무릎점 실행, 짝 접두사, run_v2 추가 인자, 고정 α 격자 글롭(이름 끝이 α))
COND = [
    ("sn24",   "main/joint_sn24",   "alpha/sn24_m",   "--forecast sn24",   ["alpha/0.5_sn24"]),
    ("oracle", "main/joint_oracle", "alpha/oracle_m", "--forecast oracle", ["alpha/0.5_oracle"]),
    ("cap0.5", "cap/0.50x",  "cap/0.50x_m", "--cap 0.50", ["cap/0.50x_a*"]),
    ("cap0.75","cap/0.75x",  "cap/0.75x_m", "--cap 0.75", ["cap/0.75x_a*"]),
    ("azure",  "azure/joint", "azure/m", "--jobs load_balancer/data/jobs_azure.csv", ["azure/alpha_*"]),
] + [(f"seed{s}", f"seed/{s}_joint", f"seed/{s}_m", f"--jobs {J.format(s=s)}", [f"seed/{s}_alpha*"]) for s in (1, 2, 3, 4)]

def lat_of(name):
    p = os.path.join(V2, name, "stats.json")
    return json.load(open(p))["avg_latency_ms"] if os.path.exists(p) else None

def alpha_of(name):
    if re.search(r"/\d\.\d+x(_a1|_rho0|_decoupled\w*)?$", name):   # cap/0.50x, cap/0.50x_a1 … 는 고정 α 점이 아님(0.50 은 상한 배수)
        return None
    ms = re.findall(r"(?:_a|_m|/m|alpha_?|/|_?dw)(\d\.\d+)", name)  # 마지막 것이 α (cap/0.50x_a0.4 → 0.4, alpha/0.5_sn24 → 0.5)
    return float(ms[-1]) if ms else None

def bracket(target, prefix, grids):
    """과녁보다 지연이 작은 가장 큰 α, 큰 가장 작은 α. 없으면 0.3 / 0.7."""
    pts = []
    for pat in grids + [prefix + "*"]:
        for d in glob.glob(os.path.join(V2, pat)):
            n = os.path.relpath(d, V2)
            a, l = alpha_of(n), lat_of(n)
            if a is not None and l is not None and a < 1.0:
                pts.append((a, l))
    lo = max([a for a, l in pts if l < target], default=0.3)
    hi = min([a for a, l in pts if l > target], default=0.7)
    if hi <= lo:  # 지연이 단조가 아닐 때의 보호
        lo, hi = max(0.0, lo - 0.1), min(1.0, lo + 0.1)
    return lo, hi, sorted(pts)

def run_one(c, dry):
    key, knee, prefix, extra, grids = c
    t = lat_of(knee)
    if t is None:
        print(f"[{key}] 무릎점 {knee} 없음 — 건너뜀", flush=True); return
    lo, hi, pts = bracket(t, prefix, grids)
    near = min(pts, key=lambda p: abs(p[1] - t), default=None)
    if near and abs(near[1] - t) <= 0.5:
        print(f"[{key}] 이미 맞는 점 있음 α={near[0]} lat {near[1]:.2f} (과녁 {t:.2f})", flush=True); return
    cmd = [os.path.join(ROOT, ".venv/bin/python"), "-m", "scheduler.match_alpha", "--target", f"{t:.2f}",
           "--lo", f"{lo:.4f}", "--hi", f"{hi:.4f}", "--prefix", prefix, "--extra", extra, "--max-runs", "4"]
    print(f"[{key}] 과녁 {t:.2f} ms, 구간 [{lo}, {hi}] (점 {len(pts)}개) → {' '.join(cmd[2:])}", flush=True)
    if dry: return
    log = os.path.join(V2, "logs", "pair_" + prefix.replace("/", "_") + ".log")
    with open(log, "w") as f:
        subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    print(f"[{key}] 끝 → {log}", flush=True)
    print(open(log).read().strip().splitlines()[-1], flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=None); ap.add_argument("--par", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    conds = [c for c in COND if not a.only or c[0] in a.only.split(",")]
    with ThreadPoolExecutor(max_workers=a.par) as ex:
        list(ex.map(lambda c: run_one(c, a.dry), conds))
    print("PAIRS DONE", flush=True)
