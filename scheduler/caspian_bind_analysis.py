# -*- coding: utf-8 -*-
"""2d 지시(2026-09-24) — l_i 올림 부풀림이 식(5)(용량, 하드제약)를 얼마나
자주 "실제로는 안 묶였을 걸 묶인 것처럼" 만드는지 측정한다.

방법: 이미 나온 decisions(=Caspian이 실제로 고른 (region,start))를 그대로 두고,
같은 배정을 두 가지 잣대로 다시 센다.
  (a) 올림 모델  — Caspian 내부가 쓴 것과 같음: 각 작업이 ceil(duration)
      "시간 슬롯 전체"를 점유한다고 보고, 정수 시간 h마다 리전별 점유 수를 센다.
  (b) 실측 모델  — 각 작업이 실제 [start, start+duration) 구간만 점유한다고
      보고, 같은 정수 시간 h 순간의 "그 순간 실행 중인 작업 수"를 센다
      (harness._over_cap과 같은 연속시간 정의).
(a)에서 점유가 cap에 도달한(=식(5)가 타이트하게 묶인) (리전,시간) 조합 중,
(b)에서는 cap 미만이었던 비율이 곧 "올림 때문에 생긴 가짜 bind" 비율이다.
"""
import math
from collections import defaultdict


def analyze(decisions, jobs, cap=12, regions=None):
    by_id = {j["id"]: j for j in jobs}
    if regions is None:
        regions = sorted({r for r, _ in decisions.values()})

    ceil_occ = defaultdict(lambda: defaultdict(int))     # region -> hour -> count
    real_iv = defaultdict(list)                           # region -> [(start,end)]

    max_h = 0
    for jid, (region, start) in decisions.items():
        j = by_id[jid]
        d = j["duration"]
        l_i = max(1, math.ceil(d - 1e-9))
        s = int(math.floor(start))
        for h in range(s, s + l_i):
            ceil_occ[region][h] += 1
        real_iv[region].append((start, start + d))
        max_h = max(max_h, s + l_i)

    total_bind = 0
    fake_bind = 0
    per_region = {}
    for region in regions:
        ivs = real_iv[region]
        occ_h = ceil_occ[region]
        r_bind = r_fake = 0
        for h, cnt in occ_h.items():
            if cnt >= cap:
                r_bind += 1
                real_cnt = sum(1 for s, e in ivs if s <= h < e)
                if real_cnt < cap:
                    r_fake += 1
        per_region[region] = dict(bind=r_bind, fake_bind=r_fake,
                                   fake_ratio=(r_fake / r_bind if r_bind else 0.0))
        total_bind += r_bind
        fake_bind += r_fake

    return dict(
        total_bind_hours=total_bind,
        fake_bind_hours=fake_bind,
        fake_ratio=(fake_bind / total_bind if total_bind else 0.0),
        per_region=per_region,
    )


if __name__ == "__main__":
    import json
    import sys

    from . import prior_harness as H

    if len(sys.argv) < 2:
        print("사용법: python -m scheduler.caspian_bind_analysis <decisions_json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        raw = json.load(f)
    decisions = {k: tuple(v) for k, v in raw.items()}

    jobs, actual, pred24, W, latency = H.load_all()
    result = analyze(decisions, jobs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
