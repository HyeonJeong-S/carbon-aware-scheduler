# -*- coding: utf-8 -*-
"""2d 지시(2026-09-24) l_i 올림 부풀림 진단 — 축소 규모(60일) 대조 실행.

전체 146,000건/8,760시간 스윕 5개가 이미 코어를 쓰고 있어, 이 진단은
대표성 있는 부분집합(첫 60일, ω1=1·ω2=ω3=1 — 원문 §V "sustainable mode"
기본값)으로 축소해서 돈다. 결과: 올림 모델 vs 실측(분수 점유) 모델의
배출량·마감위반·용량위반 비교 + bind 진단.
"""
import json
import time
from pathlib import Path

from . import caspian_bind_analysis as bind
from . import prior_caspian as C
from . import prior_harness as H

OUT_DIR = Path(__file__).parent / "caspian_sweep_results"
DAYS = 60


def main():
    OUT_DIR.mkdir(exist_ok=True)
    jobs, actual, pred24, W, latency = H.load_all()
    sub = [dict(j) for j in jobs if j["submit_time"] < DAYS * 24]
    print(f"부분집합(첫 {DAYS}일): {len(sub):,}건", flush=True)

    results = {}
    for label, frac in (("ceiling", False), ("fractional", True)):
        sub2 = [dict(j) for j in sub]
        t0 = time.time()
        decisions, run_stats = C.run_caspian(sub2, W, omega1=1.0, omega2=1.0, omega3=1.0,
                                              fractional=frac, verbose=True)
        wall = time.time() - t0
        score = H.score(decisions, sub, W, latency, label=f"Caspian({label},60d)")
        b = bind.analyze(decisions, sub)
        results[label] = dict(wall_seconds=wall, run_stats=run_stats, score=score, bind=b)
        with open(OUT_DIR / f"bind_study_{label}_decisions.json", "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in decisions.items()}, f)
        print(f"[{label}] {json.dumps(score, ensure_ascii=False)}", flush=True)
        print(f"[{label}] bind={json.dumps({k: v for k, v in b.items() if k != 'per_region'}, ensure_ascii=False)}",
              flush=True)

    inflation = {}
    import numpy as np
    durs = np.array([j["duration"] for j in sub])
    ceils = np.array([C._slots(j["duration"]) for j in sub])
    ks = np.array([j["k"] for j in sub])
    inflation["overall"] = float(ceils.sum() / durs.sum())
    for k in range(1, 6):
        m = ks == k
        if m.sum():
            inflation[f"k={k}"] = float(ceils[m].sum() / durs[m].sum())
    results["inflation_ratio"] = inflation

    with open(OUT_DIR / "bind_study_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("완료 →", OUT_DIR / "bind_study_summary.json", flush=True)


if __name__ == "__main__":
    main()
