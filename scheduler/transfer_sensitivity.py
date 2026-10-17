# -*- coding: utf-8 -*-
"""심사 M10(회계 단순화) 민감도 — 리전을 옮긴 작업마다 전송 에너지 E_tx(kWh) 를 더했을 때 절감률과 순위가 어떻게 움직이는지.
전송 탄소 = E_tx × 목적지 리전의 그 작업 평균 탄소집약도(g/kWh; 1 kW 상수 회계라 carbon_emitted/duration 이 곧 그 값).
    ./.venv/bin/python scheduler/transfer_sensitivity.py [--etx 0.006,0.06] [runs ...]
"""
import argparse, gzip, io, json, os
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "scheduler/data/v2")
DEFAULT = ["main/joint", "main/joint_a1", "main/decoupled", "main/decoupled_a1", "main/spatial_only", "main/spatial_only_a1", "main/time_only", "main/ignore", "main/ignore_a1"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--etx", default="0.006,0.06"); ap.add_argument("runs", nargs="*")
    a = ap.parse_args(); etx = [float(x) for x in a.etx.split(",")]; runs = a.runs or DEFAULT
    print("E_tx(kWh/옮긴 작업):", etx)
    print("run | 채점 n | 옮긴 n(%) | kg | 절감% | " + " | ".join(f"절감%@{e}" for e in etx) + " | " + " | ".join(f"전송 kg@{e}" for e in etx))
    for r in runs:
        st = json.load(open(os.path.join(V2, r, "stats.json")))
        df = pd.read_csv(os.path.join(V2, r, "jobs.csv.gz"))
        df = df[df.submit_time >= st["score_from"]]
        assert abs(df.carbon_emitted.sum() / 1000 - st["total_carbon_kg"]) < 0.05, (r, df.carbon_emitted.sum() / 1000, st["total_carbon_kg"])
        moved = df[df.region != df.origin]
        inten = moved.carbon_emitted / moved.duration          # g/kWh
        base = st["baseline_kg"]
        kg = st["total_carbon_kg"]
        tx = [float((inten * e).sum() / 1000) for e in etx]
        sav = [100 * (1 - (kg + t) / base) for t in tx]
        print(f"{r} | {len(df):,} | {len(moved):,}({100*len(moved)/len(df):.1f}) | {kg:,.1f} | {st['savings_pct']:.2f} | "
              + " | ".join(f"{s:.2f}" for s in sav) + " | " + " | ".join(f"{t:,.1f}" for t in tx))

if __name__ == "__main__":
    main()
