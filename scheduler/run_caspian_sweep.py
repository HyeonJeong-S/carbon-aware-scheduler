# -*- coding: utf-8 -*-
"""prior_caspian.py를 ω1 스윕으로 돌려 harness.score()로 채점하고 JSON에 쓴다.

사용법: ./.venv/bin/python -m scheduler.run_caspian_sweep <omega1> [fractional]
("fractional" 문자열을 두 번째 인자로 주면 r_i=min(duration,1) 대조 모드로 돈다.)
(ω1 하나씩 별도 프로세스로 돌려 병렬화한다 — scheduler/caspian_sweep_결과/ 에
 omega1 값·모드별로 파일을 남긴다.)
"""
import json
import sys
import time
from pathlib import Path

from . import prior_caspian as C
from . import prior_harness as H

OUT_DIR = Path(__file__).parent / "caspian_sweep_results"


def main():
    omega1 = float(sys.argv[1])
    fractional = len(sys.argv) > 2 and sys.argv[2] == "fractional"
    mode = "fractional" if fractional else "ceiling"
    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f"omega1_{omega1}_{mode}.json"

    print(f"[omega1={omega1},{mode}] 데이터 로딩...", flush=True)
    jobs, actual, pred24, W, latency = H.load_all()
    print(f"[omega1={omega1},{mode}] {len(jobs):,}건 시작", flush=True)

    t0 = time.time()
    decisions, run_stats = C.run_caspian(jobs, W, omega1=omega1, omega2=1.0, omega3=1.0,
                                          fractional=fractional, verbose=True)
    wall = time.time() - t0
    print(f"[omega1={omega1},{mode}] run_caspian 완료 {wall:.1f}s, 채점 시작", flush=True)

    score = H.score(decisions, jobs, W, latency, label=f"Caspian(ω1={omega1},{mode})")
    result = dict(omega1=omega1, mode=mode, wall_seconds=wall, run_stats=run_stats, score=score)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(OUT_DIR / f"omega1_{omega1}_{mode}_decisions.json", "w", encoding="utf-8") as f:
        json.dump({k: list(v) for k, v in decisions.items()}, f)
    print(f"[omega1={omega1},{mode}] 완료 → {out_path}", flush=True)
    print(json.dumps(score, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
