"""
Azure 2019 VM trace (AzurePublicDatasetV2, vmtable.csv.gz) → jobs_azure.csv
synthetic jobs.csv(load_balancer/data/jobs.csv)와 같은 8열 스키마.

열: job_name, submit_time[s, UTC, t=0 = 2025-01-01 00:00], duration[s], region,
    k(1..5), L_max[s], submit_local_hour[h], band(day/night)

매핑 요약 (자세한 근거는 README.md)
  필터    : created==0(좌측 절단) / deleted==T(우측 절단) / created>=29d(마지막 날, 우측절단 편향) 제거
  duration: deleted-created (300초 양자화 그대로). 0이면 150초(미해상 (0,300) 구간의 중앙값)
  k       : 라벨(Delay-insensitive→{1,2}, Interactive→{4,5}; 쌍 안에서는 duration 순위로
            synthetic 비율 3:1 / 2:3) ; Unknown(99.5%)→ synthetic 사전비율 3:1:1:2:3 난수
            (--unknown-rule duration : 긴 순서대로 k1..k5 할당, 할당량은 3:1:1:2:3)
  L_max   : gen_jobs.py와 같은 k별 범위에서 log-uniform
  region  : VM마다 균등 난수 (--region-rule subscription : 구독 단위 greedy 균형 배정)
  arrival : 29일 타일 13장 (0,29,...,348일) → 365일. 트레이스 시각을 '현지시각'으로 해석,
            submit_time = (tile + t_local + U[0,300) - offset) mod 365d
  규모    : 타일마다 11,600 VM 비복원 추출 (= 146,000 × 29/365)  → 총 ≈146,000
"""
import argparse
import hashlib
import pathlib

import numpy as np
import pandas as pd

SEED = 42
HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "vmtable.csv.gz"
OUT = HERE / "jobs_azure.csv"
PROV = HERE / "jobs_azure_provenance.csv"
STATS = HERE / "stats_azure.txt"

N_DAYS = 365
TILE_DAYS = 29                       # 30일 트레이스 중 마지막 날(29일째) 제외
N_TILES = -(-N_DAYS // TILE_DAYS)    # 13
TARGET_JOBS = 146_000
PER_TILE = round(TARGET_JOBS * TILE_DAYS / N_DAYS)   # 11,600
QUANTUM = 300                        # 트레이스 시각 해상도 [s]
DAY_START_H, DAY_END_H = 8, 20

# gen_jobs.py의 K_TABLE과 동일한 L_max 범위·가중치
K_TABLE = {
    5: dict(w=3, l_rng=(1, 5)),
    4: dict(w=2, l_rng=(15, 60)),
    3: dict(w=1, l_rng=(120, 600)),
    2: dict(w=1, l_rng=(7200, 28800)),
    1: dict(w=3, l_rng=(43200, 86400)),
}
REGIONS = {  # LB 표기 : UTC offset[h]  (gen_jobs.py와 동일)
    "US_West": -8.0, "US_Central": -6.0, "US_East": -5.0, "France": 1.0,
    "Germany": 1.0, "Korea": 9.0, "India": 5.5, "Japan": 9.0,
}
COLS = ["vmid", "subid", "depid", "created", "deleted", "maxcpu", "avgcpu",
        "p95maxcpu", "cat", "cores", "mem"]


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def load_pool():
    df = pd.read_csv(SRC, header=None, names=COLS,
                     usecols=["vmid", "subid", "created", "deleted", "cat"])
    n_raw = len(df)
    T = int(df.deleted.max())
    left = df.created == 0
    right = df.deleted == T
    last = df.created >= TILE_DAYS * 86400
    pool = df[~left & ~right & ~last].reset_index(drop=True)
    info = dict(n_raw=n_raw, T=T, n_left=int(left.sum()), n_right=int(right.sum()),
                n_both=int((left & right).sum()), n_lastday=int((last & ~left & ~right).sum()),
                n_pool=len(pool))
    pool["dur_raw"] = pool.deleted - pool.created
    return pool, info


def assign_k_labelled(df, rng):
    """라벨 있는 VM: 쌍 안에서 duration 내림차순 순위로 나눈다 (동률은 난수)."""
    k = pd.Series(0, index=df.index, dtype=int)
    for cat, (k_long, k_short, frac_long) in {
        "Delay-insensitive": (1, 2, 3 / 4),   # synthetic k1:k2 = 3:1
        "Interactive": (4, 5, 2 / 5),         # synthetic k4:k5 = 2:3
    }.items():
        idx = df.index[df.cat == cat]
        if len(idx) == 0:
            continue
        tie = rng.random(len(idx))
        order = np.lexsort((tie, -df.loc[idx, "duration"].to_numpy()))  # duration desc
        n_long = int(round(frac_long * len(idx)))
        k.loc[idx[order[:n_long]]] = k_long
        k.loc[idx[order[n_long:]]] = k_short
    return k


def assign_k_unknown(df, k, rule, rng):
    idx = df.index[k == 0]
    ks = np.array([5, 4, 3, 2, 1])
    w = np.array([K_TABLE[x]["w"] for x in ks], float)
    w /= w.sum()
    if rule == "prior":
        k.loc[idx] = rng.choice(ks, size=len(idx), p=w)
        return k
    # rule == "duration": 전체 혼합이 3:1:1:2:3이 되도록 할당량을 잡고, 긴 순서로 k1→k5
    n_total = len(df)
    quota = {x: int(round(n_total * wx)) for x, wx in zip(ks, w)}
    for x in ks:
        quota[x] = max(0, quota[x] - int((k == x).sum()))
    tie = rng.random(len(idx))
    order = np.lexsort((tie, -df.loc[idx, "duration"].to_numpy()))
    ordered = idx[order]
    pos = 0
    for x in [1, 2, 3, 4, 5]:
        take = ordered[pos:pos + quota[x]]
        k.loc[take] = x
        pos += quota[x]
    k.loc[ordered[pos:]] = 5   # 반올림 잔여
    return k


def assign_region(df, rule, rng):
    names = list(REGIONS)
    if rule == "uniform":
        return pd.Series(rng.choice(names, size=len(df)), index=df.index)
    # subscription: 구독(테넌트) 단위, 큰 구독부터 가장 적게 찬 리전에 (greedy balance)
    sizes = df.subid.value_counts()
    load = {r: 0 for r in names}
    sub2reg = {}
    for sub, n in sizes.items():
        r = min(names, key=lambda x: (load[x], x))
        sub2reg[sub] = r
        load[r] += int(n)
    return df.subid.map(sub2reg)


def build(unknown_rule, region_rule):
    rng = np.random.default_rng(SEED)
    pool, info = load_pool()
    n_pool = len(pool)

    # 1) 타일별 비복원 추출 (타일마다 다른 VM 집합)
    parts = []
    for tile in range(N_TILES):
        pick = rng.choice(n_pool, size=PER_TILE, replace=False)
        p = pool.iloc[pick].copy()
        p["tile"] = tile
        parts.append(p)
    df = pd.concat(parts, ignore_index=True)

    # 2) 현지시각 축: 타일 오프셋 + 트레이스 시각 + 5분 버킷 안 균등 지터
    jitter = rng.uniform(0, QUANTUM, size=len(df))
    t_local = df.tile.to_numpy() * TILE_DAYS * 86400.0 + df.created.to_numpy() + jitter
    df["t_local"] = t_local
    df = df[df.t_local < N_DAYS * 86400.0].reset_index(drop=True)   # 13번째 타일 절단

    # 3) duration: 양자화 그대로, 0 → 150초
    df["duration"] = df.dur_raw.astype(float).where(df.dur_raw > 0, QUANTUM / 2)

    # 4) region
    df["region"] = assign_region(df, region_rule, rng)
    off = df.region.map(REGIONS).to_numpy() * 3600.0

    # 5) k
    k = assign_k_labelled(df, rng)
    k = assign_k_unknown(df, k, unknown_rule, rng)
    df["k"] = k.astype(int)

    # 6) L_max: k별 범위 log-uniform
    u = rng.random(len(df))
    lo = df.k.map(lambda x: K_TABLE[x]["l_rng"][0]).to_numpy(float)
    hi = df.k.map(lambda x: K_TABLE[x]["l_rng"][1]).to_numpy(float)
    df["L_max"] = np.exp(np.log(lo) + u * (np.log(hi) - np.log(lo)))

    # 7) UTC 제출시각 (연 단위 순환), 현지시각·band
    df["submit_time"] = np.mod(df.t_local.to_numpy() - off, N_DAYS * 86400.0)
    lh = np.mod(df.t_local.to_numpy(), 86400.0) / 3600.0
    df["submit_local_hour"] = lh
    df["band"] = np.where((lh >= DAY_START_H) & (lh < DAY_END_H), "day", "night")

    df = df.sort_values(["submit_time", "vmid"], kind="mergesort").reset_index(drop=True)
    df["job_name"] = [f"az_{i:06d}" for i in range(len(df))]

    out = pd.DataFrame({
        "job_name": df.job_name,
        "submit_time": df.submit_time.round(1),
        "duration": df.duration.round(1),
        "region": df.region,
        "k": df.k,
        "L_max": df.L_max.round(1),
        "submit_local_hour": df.submit_local_hour.round(2),
        "band": df.band,
    })
    prov = pd.DataFrame({
        "job_name": df.job_name, "vmid": df.vmid, "tile": df.tile,
        "created_raw": df.created, "deleted_raw": df.deleted, "vmcategory": df.cat,
    })
    # 검증
    for kk, cfg in K_TABLE.items():
        s = out[out.k == kk]
        assert s.L_max.between(*cfg["l_rng"]).all()
    assert (out.duration > 0).all() and out.submit_time.between(0, N_DAYS * 86400).all()
    assert out.job_name.is_unique
    return out, prov, info, df


def report(out, prov, info, df, unknown_rule, region_rule):
    L = []
    P = L.append
    n = len(out)
    P(f"source  : {SRC.name}  sha256={sha256(SRC)}")
    P(f"rules   : unknown={unknown_rule}  region={region_rule}  seed={SEED}")
    P(f"raw rows {info['n_raw']:,} | T={info['T']} s ({info['T']/86400:.3f} d) | "
      f"left-censored {info['n_left']:,} | right-censored {info['n_right']:,} (both {info['n_both']:,}) | "
      f"last-day(>=29d) {info['n_lastday']:,} | pool {info['n_pool']:,}")
    P(f"tiles {N_TILES} x {TILE_DAYS} d, {PER_TILE:,}/tile = {N_TILES*PER_TILE:,} drawn, "
      f"{n:,} kept (<365 d)  | subsample rate per tile {PER_TILE/info['n_pool']*100:.3f}%  "
      f"| target {TARGET_JOBS:,} ({(n/TARGET_JOBS-1)*100:+.2f}%)")
    P("")
    P("tier mix (k=1..5)  count  share%   [synthetic 30/10/10/20/30]")
    for kk in [1, 2, 3, 4, 5]:
        P(f"  k{kk}: {int((out.k==kk).sum()):7,}  {(out.k==kk).mean()*100:5.2f}")
    P(f"  deferrable (L_max>=1h = k1,k2): {(out.L_max>=3600).mean()*100:.2f}%  [synthetic 40%]")
    P("")
    P("vmcategory of sampled jobs: " + ", ".join(f"{c}={v:,}" for c, v in prov.vmcategory.value_counts().items()))
    ct = pd.crosstab(prov.vmcategory, out.k)
    P("category x k:\n" + ct.to_string())
    P("")
    q = [0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
    P("duration quantiles [s] per tier (p5/p25/p50/p75/p90/p95/p99/max) + mean")
    for kk in [1, 2, 3, 4, 5, "all"]:
        s = out.duration if kk == "all" else out.duration[out.k == kk]
        P(f"  k{kk}: " + " ".join(f"{v:>9.0f}" for v in s.quantile(q)) + f"  mean={s.mean():.0f}")
    P(f"  total job-hours = {out.duration.sum()/3600:,.0f} h  (mean {out.duration.mean()/3600:.2f} h/job)")
    P("")
    day = (out.submit_time // 86400).astype(int)
    g = out.groupby(["region", day]).size().unstack(fill_value=0)
    P("jobs per region per day: mean / sd / min / max  [synthetic 50 exact]")
    for r in REGIONS:
        row = g.loc[r].reindex(range(N_DAYS), fill_value=0)
        P(f"  {r:11s} {row.mean():6.2f} {row.std():6.2f} {row.min():4d} {row.max():4d}   total {int(row.sum()):,}")
    P("")
    hl = out.submit_local_hour.astype(int).value_counts().sort_index()
    hu = ((out.submit_time % 86400) // 3600).astype(int).value_counts().sort_index()
    P("arrivals by hour-of-day: local (trace clock) / UTC")
    for h in range(24):
        P(f"  {h:02d}h  {int(hl.get(h,0)):6,}  {int(hu.get(h,0)):6,}")
    P(f"band day share: {(out.band=='day').mean()*100:.2f}%")
    P("")
    P("sampled jobs per source trace day (0..28):")
    P("  " + " ".join(str(int(v)) for v in (df.groupby(df.created // 86400).size().reindex(range(TILE_DAYS), fill_value=0))))
    text = "\n".join(L)
    STATS.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--unknown-rule", choices=["prior", "duration"], default="prior")
    ap.add_argument("--region-rule", choices=["uniform", "subscription"], default="uniform")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seed", type=int, default=SEED, help="타일별 VM 추출·지터·k 배정 시드 (기본 42)")
    ap.add_argument("--src", default=str(SRC), help="vmtable.csv.gz 경로 (저장소에는 넣지 않는다 — 437 MB)")
    a = ap.parse_args()
    SEED = a.seed
    SRC = pathlib.Path(a.src)
    out, prov, info, df = build(a.unknown_rule, a.region_rule)
    out.to_csv(a.out, index=False)
    if a.out == str(OUT):
        prov.to_csv(PROV, index=False)
    print(f"저장: {a.out}  ({len(out):,} rows)\n")
    report(out, prov, info, df, a.unknown_rule, a.region_rule)
