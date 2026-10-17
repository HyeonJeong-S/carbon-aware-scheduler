# -*- coding: utf-8 -*-
"""C2 검정 — 슬롯별 무릎점 vs 고정 α 11점의 하부 볼록 껍질 (통계 감사 2026-10-16 규약).

  점 = (지연, 실측 kg) 연간 합산. x축 둘: (a) 작업당 평균 지연, (b) 실행 시간 가중 Σd·ℓ/Σd.
  수직 거리 = 무릎의 지연에서 껍질을 보간한 kg − 무릎 kg (양수 = 무릎이 껍질보다 아래 = 더 좋음)
  수평 거리 = 무릎 kg 에서 껍질의 지연 − 무릎 지연 (양수 = 같은 kg 을 더 짧은 지연으로)
  7일 블록 짝 부트스트랩 B=2000: 같은 날 집합을 12개 실행에서 재표집, 매번 껍질을 다시 만든다.
  판정: 두 x축 모두 수직 CI 하한 > 0 → "이긴다"; 0 포함 → "껍질 위"; 상한 < 0 → "뒤진다".

    ./.venv/bin/python -m scheduler.analysis_alpha [--root scheduler/data/v2] [--prefix ""] [--knee main/joint]
Azure: --prefix azure/ --knee azure/joint --fixed azure/alpha_0.0,...,azure/joint_a1
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(_HERE, "data", "v2")
BLOCK, B = 7, 2000


def lower_hull(pts):
    """x 오름차순 하부 볼록 껍질 (왼쪽 아래 전선). pts: [(x, y)]."""
    p = sorted(set(pts))
    if len(p) <= 2:
        return p
    h = []
    for q in p:
        while len(h) >= 2:
            (x1, y1), (x2, y2) = h[-2], h[-1]
            if (x2 - x1) * (q[1] - y1) - (y2 - y1) * (q[0] - x1) <= 0:   # 비볼록(위로 꺾임)이면 제거
                h.pop()
            else:
                break
        h.append(q)
    # 하부 껍질에서 오른쪽으로 갈수록 y 가 다시 오르는 꼭짓점은 전선이 아니다 — 최소 y 이후는 자른다
    ymin_i = int(np.argmin([y for _, y in h]))
    return h[: ymin_i + 1]


def hull_y(H, x):
    xs = [a for a, _ in H]; ys = [b for _, b in H]
    if x < xs[0] or x > xs[-1]:
        return float("nan")
    return float(np.interp(x, xs, ys))


def hull_x(H, y):
    """껍질이 y 에 닿는 가장 작은 x (껍질은 x 증가에 y 감소)."""
    for (x1, y1), (x2, y2) in zip(H[:-1], H[1:]):
        if y2 <= y <= y1:
            return x1 + (y1 - y) / (y1 - y2) * (x2 - x1) if y1 != y2 else x1
    return float("nan")


def dominated_by(k, pts):
    return [p for p in pts if p[0] <= k[0] + 1e-9 and p[1] <= k[1] + 1e-9 and p != k]


def per_day(path, score_from):
    df = pd.read_csv(path)
    df = df[df.submit_time >= score_from]
    day = (df.submit_time // 24).astype(int)
    g = df.assign(day=day, dl=df.duration * df.latency_ms).groupby("day")
    return g.agg(n=("job_id", "size"), lat=("latency_ms", "sum"), dl=("dl", "sum"), d=("duration", "sum"),
                 kg=("carbon_emitted", lambda s: s.sum() / 1000.0))


def point(agg, days, weighted):
    a = agg.loc[days]
    x = a.dl.sum() / a.d.sum() if weighted else a.lat.sum() / a.n.sum()
    return (float(x), float(a.kg.sum()))


def analyse(fixed, knee, days, weighted):
    pts = {k: point(a, days, weighted) for k, a in fixed.items()}
    kp = point(knee, days, weighted)
    H = lower_hull(list(pts.values()))
    return dict(dy=hull_y(H, kp[0]) - kp[1], dx=hull_x(H, kp[1]) - kp[0], knee=kp, pts=pts, hull=H)


def pair_mode(args):
    """무릎점 vs 같은 지연의 실측 고정 α 한 판. 1년 합계와 7일 블록 부트스트랩 CI(Δkg, Δ지연). 양수 Δkg = 무릎점이 덜 배출."""
    knee = per_day(os.path.join(args.root, args.knee, "jobs.csv.gz"), args.score_from)
    pair = per_day(os.path.join(args.root, args.pair, "jobs.csv.gz"), args.score_from)
    days = sorted(set(knee.index) & set(pair.index))
    res = {}
    for weighted in (False, True):
        label = "d가중" if weighted else "작업당평균"
        kp, pp = point(knee, days, weighted), point(pair, days, weighted)
        rng = np.random.default_rng(0); nb = len(days) // BLOCK
        blocks = [days[i * BLOCK:(i + 1) * BLOCK] for i in range(nb)]
        dk, dl = [], []
        for _ in range(B):
            samp = [d for bi in rng.integers(0, nb, nb) for d in blocks[bi]]
            a, b = point(knee, samp, weighted), point(pair, samp, weighted)
            dk.append(b[1] - a[1]); dl.append(b[0] - a[0])
        dk, dl = np.array(dk), np.array(dl)
        ci = (float(np.percentile(dk, 2.5)), float(np.percentile(dk, 97.5)))
        verdict = "무릎점이 덜 배출" if ci[0] > 0 else ("무릎점이 더 배출" if ci[1] < 0 else "차이 없음")
        res[label] = dict(knee=kp, pair=pp, d_kg=pp[1] - kp[1], ci_d_kg=ci, d_lat=pp[0] - kp[0],
                          ci_d_lat=(float(np.percentile(dl, 2.5)), float(np.percentile(dl, 97.5))), verdict=verdict)
        print(f"[{label}] 무릎 ({kp[0]:.2f} ms, {kp[1]:,.1f} kg) vs 짝 {args.pair} ({pp[0]:.2f} ms, {pp[1]:,.1f} kg)  "
              f"Δkg(짝−무릎) {pp[1]-kp[1]:+.1f} CI [{ci[0]:+.1f}, {ci[1]:+.1f}]  Δ지연 {pp[0]-kp[0]:+.2f} ms  → {verdict}")
    out = args.out or os.path.join(args.root, "analysis", f"alpha_pair_{args.knee.replace('/', '_')}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1, default=float); print("저장:", out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=V2)
    ap.add_argument("--knee", default="main/joint")
    ap.add_argument("--fixed", default=None, help="쉼표 목록. 기본: alpha/0.0..0.9 + main/joint_a1")
    ap.add_argument("--score-from", type=float, default=168)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pair", default=None, help="같은 지연 짝(match_alpha 로 찾은 고정 α 실행) — 보간 없는 비교: Δkg = 짝 − 무릎, 블록 CI")
    args = ap.parse_args(argv)
    if args.pair:
        return pair_mode(args)
    if args.fixed:
        names = args.fixed.split(",")
    else:
        names = [f"alpha/{a/10:.1f}" for a in range(10)] + ["main/joint_a1"]
    fixed = {}
    for n in names:
        p = os.path.join(args.root, n, "jobs.csv.gz")
        if os.path.exists(p):
            fixed[n] = per_day(p, args.score_from)
    knee = per_day(os.path.join(args.root, args.knee, "jobs.csv.gz"), args.score_from)
    days = sorted(set.intersection(*[set(a.index) for a in list(fixed.values()) + [knee]]))
    print(f"고정점 {len(fixed)}개, 날 {len(days)}일, 무릎 {args.knee}")
    res = {}
    for weighted in (False, True):
        r = analyse(fixed, knee, days, weighted)
        label = "d가중" if weighted else "작업당평균"
        rng = np.random.default_rng(0)
        nb = len(days) // BLOCK
        blocks = [days[i * BLOCK:(i + 1) * BLOCK] for i in range(nb)]
        dys, dxs = [], []
        for _ in range(B):
            samp = [d for bi in rng.integers(0, nb, nb) for d in blocks[bi]]
            rr = analyse(fixed, knee, samp, weighted)
            dys.append(rr["dy"]); dxs.append(rr["dx"])
        dys, dxs = np.array(dys), np.array(dxs)
        ci = (float(np.nanpercentile(dys, 2.5)), float(np.nanpercentile(dys, 97.5)))
        verdict = "이긴다" if ci[0] > 0 else ("뒤진다" if ci[1] < 0 else "껍질 위")
        res[label] = dict(knee=r["knee"], dy=r["dy"], dx=r["dx"], ci_dy=ci,
                          ci_dx=(float(np.nanpercentile(dxs, 2.5)), float(np.nanpercentile(dxs, 97.5))),
                          p_dy_le_0=float(np.nanmean(dys <= 0)), verdict=verdict,
                          points=r["pts"], hull=r["hull"], dominated_by=dominated_by(r["knee"], list(r["pts"].values())))
        print(f"[{label}] 무릎 ({r['knee'][0]:.1f} ms, {r['knee'][1]:,.1f} kg)  수직 {r['dy']:+.1f} kg CI [{ci[0]:+.1f}, {ci[1]:+.1f}]  "
              f"수평 {r['dx']:+.1f} ms  P(수직≤0)={res[label]['p_dy_le_0']:.3f}  → {verdict}")
    out = args.out or os.path.join(args.root, "analysis", f"alpha_hull_{args.knee.replace('/', '_')}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1, default=float)
    print("저장:", out)


if __name__ == "__main__":
    main()
