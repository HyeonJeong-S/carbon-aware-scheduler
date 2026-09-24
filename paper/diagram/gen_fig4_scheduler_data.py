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

2026-09-24(4c 배분, 세 번째 개정): 레일을 넣으니 한 행에 작업을 여럿(그리디
구간 배정) 같이 두는 예전 방식이 성립하지 않았다 — 레일 여러 개가 한 줄로
붙어 보여 오히려 더 헷갈렸다. **한 행에 한 작업**으로 바꾸고(gen_figs_data.py
쪽), 표본은 실행시간이 아니라 **창(window = (D_j-d_j)-s_j) >= 22시간** 문턱
하나로 다시 골랐다(여전히 단일 문턱, 손으로 고른 것 없음) — j_132777(창
22.1h, "창은 넓은데 용량 때문에 16시로 밀린" 이 그림의 핵심 사례, 무제약
재실행 대조: capacity=12면 16시·27.2 gCO2/kWh, capacity=100000이면 제출
즉시·21.0 gCO2/kWh)을 반드시 포함해야 했기 때문이다 — 실행시간 기준으로는
어떤 문턱을 잡아도 "j_132777 포함"과 "~8건" 둘을 동시에 만족시킬 수 없었다
(직접 스윕해 확인: 실행시간>=3.15h는 14건이라 이 건을 포함하지만 너무 많고,
문턱을 조금만 올려도 이 건부터 먼저 빠진다 — 이 건의 실행시간 3.20h가 표본
안에서 짧은 축에 속해서다).

9건이 나온다. 창>=22h로 걸렀으므로 전부 "창이 넉넉한" 축에만 있다(창/실행시간
비율 5.1~45.7배) — "창이 빡빡한데 눈에 보이는" 예는 이 표본엔 없다. 가능한 한
낮은 문턱(실행시간 기준)으로 훑어봐도 창이 좁고 실행시간이 1시간 넘는 작업
자체가 이 날 이 리전엔 없었다(전부 실행시간 1시간 미만) — 억지로 만들지
않고 있는 그대로 report한다. 강제 편입(forced) 작업도 이 표본엔 없다 —
강제 편입은 정의상 창이 좁아서(마감 임박) 생기는 일이라 창>=22h인 작업과는
서로 배타적에 가깝다(이 날 강제 편입 2건의 창은 각각 16.97h·18.21h로 22h에
못 미친다).

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
# 2026-09-24(4c, 세 번째 개정): 실행시간 문턱→창(window) 문턱으로 바꿨다.
# 이유는 파일 docstring 참고 — j_132777을 반드시 포함해야 했다.
GANTT_WINDOW_THRESHOLD_H = 22.0   # 간트에 얹을 작업의 최소 창 길이(단일 문턱, 솎아내기 없음)


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

    def window_of(v):
        deadline = job_by_id[v["job_id"]]["deadline"]
        return (deadline - v["duration"]) - v["submit_time"]

    sel = sorted([v for v in overlapping if window_of(v) >= GANTT_WINDOW_THRESHOLD_H],
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
            "window": round(window_of(v), 4),
            "forced": bool(v["forced"]), "k": v["k"],
        })
    gantt_path = os.path.join(_HERE, "fig4_gantt_data.json")
    json.dump({"day": DAY, "region": REGION, "window_threshold_h": GANTT_WINDOW_THRESHOLD_H,
               "jobs": gantt},
              open(gantt_path, "w"), ensure_ascii=False, indent=1)
    has_132777 = any(g["id"] == "j_132777" for g in gantt)
    print(f"wrote {gantt_path}  ({len(gantt)}건, 창 문턱 {GANTT_WINDOW_THRESHOLD_H}h, "
          f"forced {sum(g['forced'] for g in gantt)}건, j_132777 포함={has_132777})")
    assert has_132777, "j_132777이 표본에서 빠졌다 — 이 그림의 핵심 사례라 반드시 있어야 한다"


if __name__ == "__main__":
    main()
