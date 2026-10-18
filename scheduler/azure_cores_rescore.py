"""3회차 A[3] — Azure VM 크기. 배정은 그대로 두고 전력을 코어 수에 비례하게 채점만 다시 한다.
작업 → vmid 는 생성기(gen_jobs_azure.build, 시드 42)를 다시 돌려 얻고, 결과가 jobs_azure.csv 와 행마다 같은지 확인한다.
코어 수는 원 트레이스의 구간 값(2·4·8·24·'>24'); '>24' 는 30 으로 둔다(BIG_CORES 로 바꿔 민감도).
    ./.venv/bin/python -m scheduler.azure_cores_rescore azure/joint azure/joint_a1 azure/ignore ...
"""
import json
import os
import sys

import pandas as pd

from interface import carbon_2025
from scheduler import capacity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "scheduler", "data", "v2")
GEN = os.path.join(ROOT, "load_balancer", "data", "generator")


BIG = float(os.environ.get("BIG_CORES", 30))   # '>24' 구간에 줄 값(민감도: BIG_CORES=64)


def _num(v):
    return BIG if v.strip() == ">24" else float(v)


def cores_by_job():
    cache = os.path.join(V2, "analysis", "azure_cores.csv")
    if os.path.exists(cache):
        return pd.read_csv(cache, dtype={"cores": str}).set_index("job_name").cores.map(_num)
    sys.path.insert(0, GEN)
    import gen_jobs_azure as g
    out, prov, _, _ = g.build("prior", "uniform")
    ref = pd.read_csv(os.path.join(ROOT, "load_balancer", "data", "jobs_azure.csv"))
    assert len(out) == len(ref) and (out.job_name.values == ref.job_name.values).all()
    for c in ["submit_time", "duration", "L_max"]:
        assert (out[c].values == ref[c].values).all(), c
    assert (out.region.values == ref.region.values).all() and (out.k.values == ref.k.values).all()
    vt = pd.read_csv(g.SRC, header=None, names=g.COLS, usecols=["vmid", "cores"]).drop_duplicates("vmid").set_index("vmid").cores
    c = prov.set_index("job_name").vmid.map(vt)
    assert c.notna().all()
    c.rename("cores").to_frame().to_csv(cache)
    return c.rename("cores").astype(str).map(_num)


def main():
    cores = cores_by_job()
    print("코어 구간 분포:", cores.value_counts().sort_index().to_dict(), f"평균 {cores.mean():.2f}")
    data = carbon_2025.load_2025()
    W = capacity._Windows(data["actual"], data["pred24"])
    for name in sys.argv[1:]:
        st = json.load(open(os.path.join(V2, name, "stats.json")))
        df = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
        df = df[df.submit_time >= st["score_from"]]
        base = [W.actual_mean(o, s, d) * d for o, s, d in zip(df.origin, df.submit_time, df.duration)]
        df = df.assign(base=base, w=df.job_id.map(cores).values)
        assert abs(df.base.sum() / 1000 - st["baseline_kg"]) < 0.5, (df.base.sum() / 1000, st["baseline_kg"])
        sav_w = 100 * (1 - (df.w * df.carbon_emitted).sum() / (df.w * df.base).sum())
        print(f"{name}: VM 시간 가중 {st['savings_pct']:.2f}% → 코어 가중 {sav_w:.2f}%  (코어 가중 기준 {(df.w*df.base).sum()/1000:,.1f} kg·core, 결과 {(df.w*df.carbon_emitted).sum()/1000:,.1f})")


if __name__ == "__main__":
    main()
