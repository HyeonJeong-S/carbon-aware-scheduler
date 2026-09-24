# -*- coding: utf-8 -*-
"""그림 7(fig4_scheduler)의 실측 데이터 생성기 — day101·캘리포니아.

왜 필요한가
-----------
fig4_slot_data.json(시각별 탄소·동시 실행 수)은 이미 레포에 있었지만 만든
스크립트가 없었다(2026-09-24, fd가 그림 7에 작업 막대를 얹으려다 발견 — 재현성
구멍이라 여기서 메운다). 이 스크립트는 scheduler.reproduce가 쓰는 것과 정확히
같은 파이프라인(capacity.run_rolling, capacity=12, 표2 ④의 그 실행)을 다시 돌려
1) 기존 fig4_slot_data.json과 같은 값이 나오는지 검산하고
2) 그 위에 얹을 개별 작업 간트 데이터(fig4_gantt_data.json)를 새로 뽑는다.

간트 표본 선정
--------------
2026-09-24(4c 배분, 두 번째 개정): 사용자가 "이해가 안 된다"고 지적 — 예전 판은
실행 구간(tau_j~tau_j+d_j)만 막대로 그려 "왜 하필 거기서 실행됐는가"가 안
보였다. 이번 판은 각 작업의 s_j(제출 시각)~D_j(마감)이라는 "레일"을 같이
실어, 창이 넓은데도 저탄소 시각으로 못 간 작업(용량이 막은 경우)이 보이게 한다.

문턱을 3.5h→3.0h로 낮췄다(여전히 단일 문턱, 손으로 고른 것 없음) — 3.5h에서는
j_132777(실행시간 3.20h, 창 22.1h)이 문턱에 걸려 빠졌는데, 이 작업이 바로
"창은 넓은데 용량 때문에 밀린" 사례다(무제약 재실행 대조: capacity=12일 때
16시·27.2 gCO2/kWh로 실행되지만 capacity=100000이면 제출 즉시·21.0 gCO2/kWh로
실행된다 — 용량이 없었다면 갔을 자리가 있었다는 뜻). 14건이 나온다(10~20건
권장 범위 안), 강제 편입 2건 포함, 창/실행시간 비율이 2.3~6.9배로 다양하다.
(더 촘촘한 창을 가진 작업은 전부 실행시간이 1시간 미만으로 막대가 안 보일
만큼 작아 표본에서 자연히 빠진다 — 이 자체가 "60%는 구조적으로 시간 이동에
못 낀다"는 §4.1 발견과 같은 결이다.)

실행: ./.venv/bin/python paper/diagram/gen_fig4_scheduler_data.py
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO_ROOT)

from interface import carbon_2025
from interface.regions import REGIONS
from load_balancer.framework.config import JOBS_CSV as YEAR_JOBS_CSV
from load_balancer.framework.config import RESULTS_DIR as LB_RESULTS_DIR
from scheduler import capacity, data_loader

YEAR_ASSIGN_CSV = LB_RESULTS_DIR / "assign_alpha_auto.csv"
CAP = 12       # 유효 상한 — scheduler/reproduce.py의 CAP과 동일(표2 ④ 재현)
DAY = 101      # fig4_slot_data.json이 이미 쓰고 있던 날
REGION = "US-CAL-CISO"
GANTT_THRESHOLD_H = 3.0   # 간트에 얹을 작업의 최소 실행시간(단일 문턱, 솎아내기 없음)


def main():
    jobs = data_loader.load_jobs_with_assignment(YEAR_JOBS_CSV, YEAR_ASSIGN_CSV)
    data = carbon_2025.load_2025()
    actual, pred24 = data["actual"], data["pred24"]

    # ── 표2 ④와 정확히 같은 실행 (scheduler/reproduce.py:174) ──
    out, stats = capacity.run_rolling(jobs, actual, pred24, capacity=CAP, regions=REGIONS)

    day_start, day_end = DAY * 24, (DAY + 1) * 24
    car = actual[REGION][day_start:day_end]
    cal_jobs = [v for v in out.values() if v["region"] == REGION]

    occ = np.zeros(24, dtype=int)
    for v in cal_jobs:
        s, e = v["scheduled_start"], v["scheduled_start"] + v["duration"]
        for h in range(24):
            hs, he = day_start + h, day_start + h + 1
            if s < he and e > hs:
                occ[h] += 1

    # ── 검산: 기존 fig4_slot_data.json과 동일해야 한다 ──
    slot_path = os.path.join(_HERE, "fig4_slot_data.json")
    if os.path.exists(slot_path):
        old = json.load(open(slot_path))
        assert occ.tolist() == old["occ"], f"occ 불일치: {occ.tolist()} vs {old['occ']}"
        assert np.allclose(car, old["carbon"], atol=0.01), "carbon 불일치"
        assert old["cap"] == CAP
        print("검산 통과 — 기존 fig4_slot_data.json과 occ·carbon·cap 전부 일치")
    else:
        print("주의: fig4_slot_data.json이 없어 검산을 못 함 (이번이 최초 생성)")

    slot_data = {"day": DAY, "carbon": [round(float(c), 5) for c in car],
                 "occ": occ.tolist(), "cap": CAP}
    json.dump(slot_data, open(slot_path, "w"), ensure_ascii=False)
    print(f"wrote {slot_path}")

    # ── 간트 표본 ──
    # 2026-09-24(4c): 레일(s_j~D_j)을 그리려면 제출 시각·마감이 필요하다.
    # capacity.run_rolling()의 출력(out/cal_jobs)에는 submit_time은 있지만
    # deadline은 없어 jobs 원본에서 id로 찾는다.
    job_by_id = {j["id"]: j for j in jobs}

    overlapping = [v for v in cal_jobs
                   if v["scheduled_start"] < day_end and v["scheduled_start"] + v["duration"] > day_start]
    sel = sorted([v for v in overlapping if v["duration"] >= GANTT_THRESHOLD_H],
                 key=lambda v: v["scheduled_start"])

    gantt = []
    for v in sel:
        deadline = job_by_id[v["job_id"]]["deadline"]
        gantt.append({
            "id": v["job_id"],
            "s": round(v["submit_time"] - day_start, 4),       # 제출 시각(레일 왼쪽 끝)
            "tau": round(v["scheduled_start"] - day_start, 4), # 실제 실행 시작(블록 왼쪽 끝)
            "dur": round(v["duration"], 4),                     # 실행 시간(블록 길이)
            "D": round(deadline - day_start, 4),                # 마감(레일 오른쪽 끝)
            "forced": bool(v["forced"]), "k": v["k"],
        })
    gantt_path = os.path.join(_HERE, "fig4_gantt_data.json")
    json.dump({"day": DAY, "region": REGION, "threshold_h": GANTT_THRESHOLD_H, "jobs": gantt},
              open(gantt_path, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {gantt_path}  ({len(gantt)}건, 문턱 {GANTT_THRESHOLD_H}h, "
          f"forced {sum(g['forced'] for g in gantt)}건)")


if __name__ == "__main__":
    main()
