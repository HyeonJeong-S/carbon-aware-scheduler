"""위반 순간에 다른 리전에 빈자리가 있었는지(10-19, 1회차 D 출처 없음 N-출처 셋의 근거).
    ./.venv/bin/python -m scheduler.violation_free_check <run> [<run> ...]
결과는 scheduler/data/v2/analysis/violation_free_<run>.json. 상한은 stats.json 의 cap(정수)."""
import json
import os
import sys

import numpy as np
import pandas as pd

V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "v2")


def check(run):
    d = pd.read_csv(os.path.join(V2, run, "jobs.csv.gz"))
    cap = json.load(open(os.path.join(V2, run, "stats.json")))["cap"]
    d["end"] = d.scheduled_start + d.duration
    S = {r: np.sort(g.scheduled_start.values) for r, g in d.groupby("region")}
    E = {r: np.sort(g.end.values) for r, g in d.groupby("region")}

    def running(r, t):
        return int(np.searchsorted(S[r], t, side="right") - np.searchsorted(E[r], t, side="right"))

    v = d[d.over_cap.notna()]
    free_elsewhere = sum(1 for _, j in v.iterrows() if any(running(r, j.scheduled_start) < cap for r in S if r != j.region))
    inst = v.groupby(["region", "scheduled_start"]).forced.any() if len(v) else pd.Series(dtype=bool)
    out = dict(run=run, cap=cap, violations=int(len(v)), by_kind={k: int(x) for k, x in v.over_cap.value_counts().items()},
               free_elsewhere=int(free_elsewhere), no_free_anywhere=int(len(v) - free_elsewhere),
               violation_instants=int(len(inst)), instants_without_forced=int((~inst).sum()) if len(inst) else 0)
    json.dump(out, open(os.path.join(V2, "analysis", "violation_free_" + run.replace("/", "_") + ".json"), "w"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    for r in sys.argv[1:]:
        print(check(r))
