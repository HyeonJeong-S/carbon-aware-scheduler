"""C3 — 용량이 어디서 무는가. 리전별 귀속을 설계 감사 11번 규약대로 계산한다.

  시간 이동의 이득(리전별) = 시간만(홈 고정) − 기준(홈·즉시), 출발 리전 기준 → 공간 이동이 섞이지 않는다
  용량 충돌(리전별)       = 용량 무시 실행의 초과 시간 / 결합 실행의 초과 시간 (실행 리전 기준)
  리전 변동 폭 σ          = 실측 탄소의 일중 (최대−최소)/평균 의 연평균, day 8+
  현지시각 분포           = 초과가 난 시각을 그 리전의 시간대(DST 포함)로 바꿔 24칸 히스토그램

    ./.venv/bin/python -m scheduler.analysis_regions [--root scheduler/data/v2] [--prefix main/] [--cap 17]
출력: <root>/analysis/regions_<prefix>.json
"""
import argparse
import json
import math
import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from interface import carbon_2025
from interface.regions import REGIONS

from . import capacity, joint

_HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(_HERE, "data", "v2")
TZ = {"US-CAL-CISO": "America/Los_Angeles", "US-TEX-ERCO": "America/Chicago", "US-NY-NYIS": "America/New_York",
      "FR": "Europe/Paris", "DE": "Europe/Berlin", "KR": "Asia/Seoul", "IN": "Asia/Kolkata", "JP": "Asia/Tokyo"}
T0 = datetime(2025, 1, 1, tzinfo=UTC)


def load(path, score_from):
    df = pd.read_csv(path)
    return df[df.submit_time >= score_from]


def kg_by(df, col):
    return (df.groupby(col)["carbon_emitted"].sum() / 1000.0).to_dict()


def hours_over_by_region(df, cap_d):
    out = {r: dict(region=r, scheduled_start=s, duration=d) for r, s, d in zip(df.region, df.scheduled_start, df.duration)}
    # joint.hours_over 는 dict(job_id→rec) 를 받으므로 index 로 키를 만든다
    recs = {i: dict(region=r, scheduled_start=s, duration=d) for i, (r, s, d) in enumerate(zip(df.region, df.scheduled_start, df.duration))}
    return joint.hours_over(recs, REGIONS, cap_d)


def over_hours_local_hist(df, region, cap, score_from, t_hi):
    """리전 region 에서 동시 실행 > cap 인 시각들을 현지시각 24칸으로."""
    sub = df[df.region == region]
    ev = sorted([(s, 1) for s in sub.scheduled_start] + [(s + d, -1) for s, d in zip(sub.scheduled_start, sub.duration)])
    hist = np.zeros(24)
    cur, prev = 0, None
    tz = ZoneInfo(TZ[region])
    for t, d in ev:
        if prev is not None and cur > cap and t > prev:
            a, b = max(prev, score_from), min(t, t_hi)
            h = a
            while h < b:
                nxt = min(math.floor(h) + 1, b)
                local = (T0 + timedelta(hours=h)).astimezone(tz)
                hist[local.hour] += nxt - h
                h = nxt
        cur += d; prev = t
    return hist


def sigma_by_region(actual, score_from, t_hi):
    out = {}
    for r in REGIONS:
        a = actual[r][score_from:t_hi]
        days = a[: len(a) // 24 * 24].reshape(-1, 24)
        out[r] = float(np.mean((days.max(1) - days.min(1)) / np.maximum(days.mean(1), 1e-9)))
    return out


def swing_abs_by_region(actual, score_from, t_hi):
    """절대 변동: 일별(최대−최소)의 평균, gCO₂/kWh. 10-17: 시간 이동 이득은 상대 σ 가 아니라 이것을 따른다
    (프랑스 σ 0.97 인데 이득 0.3%) — 4.5 와 그림 9 의 x 축."""
    out = {}
    for r in REGIONS:
        a = actual[r][score_from:t_hi]
        days = a[: len(a) // 24 * 24].reshape(-1, 24)
        out[r] = float(np.mean(days.max(1) - days.min(1)))
    return out


def mean_by_region(actual, score_from, t_hi):
    return {r: float(np.mean(actual[r][score_from:t_hi])) for r in REGIONS}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=V2)
    ap.add_argument("--prefix", default="main/")
    ap.add_argument("--cap", type=int, default=17)
    ap.add_argument("--score-from", type=float, default=168)
    args = ap.parse_args(argv)
    actual = carbon_2025.load_2025()["actual"]
    t_hi = len(next(iter(actual.values())))
    W = capacity._Windows(actual, joint.sn24_pred24(actual))
    cap_d = dict.fromkeys(REGIONS, args.cap)
    P = lambda n: os.path.join(args.root, args.prefix + n, "jobs.csv.gz")

    time_only = load(P("time_only"), args.score_from)
    base_kg = {}
    for r in REGIONS:
        sub = time_only[time_only.origin == r]
        base_kg[r] = float(sum(W.actual_mean(r, s, d) * d for s, d in zip(sub.submit_time, sub.duration)) / 1000.0)
    to_kg = kg_by(time_only, "origin")
    temporal_gain = {r: base_kg[r] - to_kg.get(r, 0.0) for r in REGIONS}
    tot_gain = sum(temporal_gain.values())

    res = dict(prefix=args.prefix, cap=args.cap, baseline_kg_by_origin=base_kg, time_only_kg_by_origin=to_kg,
               temporal_gain_kg=temporal_gain, temporal_gain_share={r: temporal_gain[r] / tot_gain for r in REGIONS},
               sigma=sigma_by_region(actual, int(args.score_from), t_hi),
               swing_abs=swing_abs_by_region(actual, int(args.score_from), t_hi),
               mean_intensity=mean_by_region(actual, int(args.score_from), t_hi))
    for name in ("ignore", "joint", "decoupled", "ignore_decoupled"):
        p = P(name)
        if not os.path.exists(p):
            continue
        df = load(p, args.score_from)
        ho = hours_over_by_region(df, cap_d)
        tot = sum(ho.values())
        res[name] = dict(hours_over=ho, hours_over_share={r: (ho[r] / tot if tot else 0.0) for r in REGIONS},
                         peak=joint.peak_ends_first({i: dict(region=r, scheduled_start=s, duration=d) for i, (r, s, d) in
                                                     enumerate(zip(df.region, df.scheduled_start, df.duration))}, REGIONS),
                         kg_by_region=kg_by(df, "region"), share_by_region=(df.region.value_counts(normalize=True)).to_dict())
        top = max(ho, key=ho.get)
        res[name]["local_hist_top_region"] = dict(region=top, hist=over_hours_local_hist(df, top, args.cap, args.score_from, t_hi).tolist())
        res[name]["local_hist_CAL"] = over_hours_local_hist(df, "US-CAL-CISO", args.cap, args.score_from, t_hi).tolist()
        res[name]["local_hist_FR"] = over_hours_local_hist(df, "FR", args.cap, args.score_from, t_hi).tolist()
    out = os.path.join(args.root, "analysis", f"regions_{args.prefix.strip('/').replace('/', '_') or 'main'}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1, default=float)
    print("시간 이동 이득 몫:", {r: f"{100*v:.1f}%" for r, v in sorted(res["temporal_gain_share"].items(), key=lambda kv: -kv[1])})
    for name in ("ignore", "joint"):
        if name in res:
            print(f"{name} 초과 시간 몫:", {r: f"{100*v:.1f}%" for r, v in sorted(res[name]["hours_over_share"].items(), key=lambda kv: -kv[1])[:4]})
    print("저장:", out)


if __name__ == "__main__":
    main()
