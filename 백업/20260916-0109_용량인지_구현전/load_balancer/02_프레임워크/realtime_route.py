"""
실시간 라우팅 CLI — LSTM 예측을 실시간으로 호출해 슬롯 하나를 라우팅하고 JSON으로 내보낸다.

run_experiments.py가 1년치를 통째로 재생하는 오프라인 시뮬레이터라면,
이 스크립트는 "지금 이 슬롯"만 처리하는 실시간 서빙 데모다:

    1. interface.carbon_forecast_api.get_forecast(t_hour) 호출
       → 실제 LSTM 모델(torch)이 있으면 LSTM, 없거나 범위 밖이면 더미로 자동 폴백
    2. 슬롯의 job 배치 확보 (jobs.csv 슬롯 재생 또는 --jobs-json)
    3. simulator.assign_slot(ILP) / knee_slot_alpha(α 자동)로 배정
    4. 예측값 + 배정 결과를 JSON으로 출력 (stdout 또는 --out 파일)

사용법:
    .venv/bin/python realtime_route.py --t-hour 200                    # jobs.csv 슬롯 재생
    .venv/bin/python realtime_route.py --t-hour 200 --alpha 0.5        # α 고정
    .venv/bin/python realtime_route.py --t-hour 200 --jobs-json my.json --out result.json

--jobs-json 형식: [{"job_name": "j1", "region": "Korea", "duration": 3600}, ...]
    region은 LB 표기(Korea)와 표준 코드(KR) 모두 허용. "-"를 주면 stdin에서 읽는다.

시간축: t_hour=0 ↔ 2026-01-01 00:00 UTC (LSTM 데모 데이터 규약).
LSTM 백엔드는 이력 168h가 쌓인 t_hour>=168부터, 데이터 끝-24h까지 응답한다.
단일 슬롯 독립 실행이라 리전 점유 상태(running)는 비어 있다고 가정한다.
"""
import argparse
import contextlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from config import (EVAL_REGION_MAP, JOBS_CSV, L_NET_MAX_MS, REGIONS,
                    load_latency_matrix)
from simulator import SimConfig, assign_slot, auto_capacity, knee_slot_alpha

# interface 패키지(LSTM 경계 레이어)는 저장소 루트에서 import.
# 모델 로드 시 stdout에 상태 메시지를 찍으므로 stderr로 돌린다 (stdout = 순수 JSON).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

with contextlib.redirect_stdout(sys.stderr):
    from interface import carbon_forecast_api  # noqa: E402
    from interface.carbon_history import BASE_TIME  # noqa: E402

SLOT_S = 3600.0
HORIZON = 24

# job의 region 입력은 LB 표기·표준 코드 둘 다 허용
_NAME_TO_IDX = {r: i for i, r in enumerate(REGIONS)}
_NAME_TO_IDX.update({std: _NAME_TO_IDX[lb] for std, lb in EVAL_REGION_MAP.items()})


def fetch_forecast(t_hour: int) -> tuple[dict, np.ndarray]:
    """LSTM 경계 레이어에서 예측을 받아 (LB표기 dict, 현재슬롯 벡터)로 변환."""
    fc = carbon_forecast_api.get_forecast(t_hour, horizon=HORIZON)
    fc_lb = {EVAL_REGION_MAP[k]: [round(float(v), 2) for v in vals]
             for k, vals in fc.items() if k in EVAL_REGION_MAP}
    m_hat = np.array([fc_lb[r][0] for r in REGIONS])  # index 0 = 이 슬롯의 예측
    return fc_lb, m_hat


def load_slot_jobs(t_hour: int, jobs_json: str | None) -> pd.DataFrame:
    """슬롯의 job 배치. --jobs-json이 있으면 그걸, 없으면 jobs.csv에서 재생."""
    if jobs_json:
        raw = sys.stdin.read() if jobs_json == "-" else Path(jobs_json).read_text()
        jobs = pd.DataFrame(json.loads(raw))
        for col, default in [("job_name", None), ("region", None),
                             ("duration", 3600.0), ("k", 1)]:
            if col not in jobs.columns:
                if default is None:
                    raise ValueError(f"--jobs-json에 '{col}' 필드가 필요합니다.")
                jobs[col] = default
        bad = jobs[~jobs.region.isin(_NAME_TO_IDX)]
        if not bad.empty:
            raise ValueError(f"알 수 없는 region: {sorted(bad.region.unique())}")
        jobs["region"] = jobs.region.map(
            lambda r: REGIONS[_NAME_TO_IDX[r]])  # 표준 코드 → LB 표기 통일
        jobs["submit_time"] = t_hour * SLOT_S
        return jobs

    all_jobs = pd.read_csv(JOBS_CSV)
    return all_jobs[(all_jobs.submit_time // SLOT_S).astype(int) == t_hour].copy()


def route_slot(t_hour: int, jobs: pd.DataFrame, alpha: str,
               capacity: int | None, headroom: float,
               l_net_max: float | None) -> dict:
    """슬롯 하나 라우팅 → JSON 직렬화 가능한 dict."""
    fc_lb, m_hat = fetch_forecast(t_hour)
    backend = carbon_forecast_api.last_backend()

    latency = load_latency_matrix()
    l_tilde = latency / L_NET_MAX_MS
    blocked = np.zeros((8, 8), dtype=bool)
    if l_net_max is not None:
        blocked |= latency > l_net_max
        np.fill_diagonal(blocked, False)

    if capacity is None:
        capacity = (auto_capacity(pd.read_csv(JOBS_CSV), 1.2)
                    if JOBS_CSV.exists() else 50)
    cfg = SimConfig(alpha=0.5 if alpha == "auto" else float(alpha),
                    headroom=headroom, capacity=capacity, l_net_max=l_net_max,
                    adaptive_alpha=(alpha == "auto"))
    avail = np.full(8, int(np.floor(headroom * capacity)))  # 단독 슬롯: 점유 없음 가정

    assignments = []
    a_slot = None
    if not jobs.empty:
        batch = [dict(origin_idx=_NAME_TO_IDX[r]) for r in jobs.region]
        durations = jobs.duration.to_numpy(dtype=float)
        m_tilde = m_hat / m_hat.max()

        if alpha == "auto":
            a_slot, picks = knee_slot_alpha(batch, durations, m_hat, m_tilde,
                                            l_tilde, latency, avail, cfg, blocked)
        else:
            a_slot = float(alpha)
            picks = assign_slot(batch, m_tilde, l_tilde, avail, cfg, blocked)

        for (_, job), pick in zip(jobs.iterrows(), picks):
            o = _NAME_TO_IDX[job.region]
            rec = dict(job_name=str(job.job_name), origin=REGIONS[o],
                       duration_s=float(job.duration))
            if pick is None:
                rec.update(assigned=None, latency_ms=None,
                           est_carbon_g=None, dropped=True)
            else:
                rec.update(
                    assigned=REGIONS[pick],
                    latency_ms=float(latency[o][pick]),
                    # 예측강도 × 시간 × 1kW 추정치 — 실측 정산은 시뮬레이터 몫
                    est_carbon_g=round(float(m_hat[pick]) * job.duration / 3600.0, 1),
                    dropped=False)
            assignments.append(rec)

    ok = [a for a in assignments if not a["dropped"]]
    return {
        "t_hour": t_hour,
        "timestamp_utc": (BASE_TIME + pd.Timedelta(hours=t_hour)).isoformat(),
        "forecast_backend": backend,          # 'lstm' | 'dummy'
        "backend_detail": carbon_forecast_api.backend_info(),
        "alpha": a_slot,
        "alpha_mode": "auto" if alpha == "auto" else "fixed",
        "forecast_gco2_per_kwh": fc_lb,       # 리전별 24시간 예측 (index 0 = 이 슬롯)
        "assignments": assignments,
        "summary": {
            "n_jobs": len(assignments),
            "dropped": sum(a["dropped"] for a in assignments),
            "avg_latency_ms": (round(float(np.mean([a["latency_ms"] for a in ok])), 2)
                               if ok else None),
            "est_total_carbon_g": round(sum(a["est_carbon_g"] for a in ok), 1),
            "region_load": {r: sum(a["assigned"] == r for a in ok) for r in REGIONS},
            "capacity_per_region": int(np.floor(headroom * capacity)),
        },
    }


def main():
    ap = argparse.ArgumentParser(description="실시간 LSTM 라우팅 → JSON")
    ap.add_argument("--t-hour", type=int, required=True,
                    help="슬롯 시각 (0 = 2026-01-01 00:00 UTC, LSTM은 168 이상부터)")
    ap.add_argument("--jobs-json", default=None,
                    help="job 배치 JSON 파일 ('-' = stdin). 생략 시 jobs.csv 슬롯 재생")
    ap.add_argument("--alpha", default="auto",
                    help="'auto'(무릎점) 또는 0~1 고정값 (기본 auto)")
    ap.add_argument("--capacity", type=int, default=None,
                    help="리전당 동시 실행 한도 (기본: jobs.csv 기준 자동 산정)")
    ap.add_argument("--headroom", type=float, default=0.8)
    ap.add_argument("--l-net-max", type=float, default=None,
                    help="네트워크 SLO 상한(ms). 초과 경로 차단")
    ap.add_argument("--out", default=None, help="JSON 저장 경로 (생략 시 stdout)")
    args = ap.parse_args()

    jobs = load_slot_jobs(args.t_hour, args.jobs_json)
    result = route_slot(args.t_hour, jobs, args.alpha,
                        args.capacity, args.headroom, args.l_net_max)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text)
        print(f"저장: {args.out} (backend={result['forecast_backend']}, "
              f"jobs={result['summary']['n_jobs']})", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
