# -*- coding: utf-8 -*-
"""합성 워크로드 변형 — 시드 4개와 등급 비율(φ) 4개. gen_jobs.py 의 전역을 덮어써 만든다.
    ./.venv/bin/python load_balancer/data/generator/gen_variants.py
출력: load_balancer/data/variants/jobs_seed{1..4}.csv, jobs_phi{20,30,50,60}.csv
φ = 미룰 수 있는 작업(L_max ≥ 1h, 곧 k∈{1,2}) 비율. 기본 3:1:1:2:3 → 40%.
"""
import importlib, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
G = importlib.import_module("gen_jobs")
OUT = os.path.join(os.path.dirname(HERE), "variants")
os.makedirs(OUT, exist_ok=True)

def make(path, seed, weights=None):
    G.SEED = seed
    G.rng = np.random.default_rng(seed)
    if weights:
        for k, w in weights.items():
            G.K_TABLE[k]["w"] = w
    df = G.generate()
    df.to_csv(path, index=False)
    phi = (df.L_max >= 3600).mean() * 100
    print(f"{os.path.basename(path):18s} seed={seed} n={len(df):,} 미룰수있음 {phi:.1f}%  k비율 "
          + " ".join(f"{k}:{(df.k == k).mean()*100:.0f}" for k in (1, 2, 3, 4, 5)), flush=True)

base = {k: G.K_TABLE[k]["w"] for k in G.K_TABLE}
for s in (1, 2, 3, 4):
    make(os.path.join(OUT, f"jobs_seed{s}.csv"), s, base)
# φ 변형: k1:k2 = 3:1 비율 유지, k3:k4:k5 = 1:2:3 유지, 두 묶음의 합만 바꾼다
for phi in (20, 30, 50, 60):
    a, b = phi / 100, 1 - phi / 100
    w = {1: 3 * a / 4, 2: 1 * a / 4, 3: 1 * b / 6, 4: 2 * b / 6, 5: 3 * b / 6}
    make(os.path.join(OUT, f"jobs_phi{phi}.csv"), 42, w)
