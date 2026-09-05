"""대시보드 데이터 로더 — 무거운 것은 한 번만 읽고 프로세스 안에 캐시한다.

    로드밸런서 결과   : lb_load_all()                 results/summary.json + run별 CSV
    스케줄러 검증     : start_validation_async() ·    2025년 1년치 3개 비교군 시뮬레이션
                        validation_state()           (약 1분 — 서버 기동 시 백그라운드로 미리 돌린다)
    실시간 라우팅     : realtime_route_slot()         LSTM 라이브 + ILP (슬롯 1개)
    실험 재실행       : start_experiments() ·         run_experiments.py 를 백그라운드 프로세스로
                        experiments_state()

시간축 두 개가 공존한다 (문서 참고):
    2025 축 — 로드밸런서 1년 실험 · 스케줄러 검증 (eval_records, t=0 ↔ 2025-01-01)
    2026 축 — 메인 화면 · LSTM 라이브 · 실시간 라우팅 (carbon_intensity_demo.csv, t=0 ↔ 2026-01-01)
"""

import contextlib
import functools
import json
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pandas as pd

from interface import carbon_forecast_api as api
from interface.regions import LB_TO_REGION, REGIONS
from load_balancer.framework import config as lb_config

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))

LB_REGIONS = lb_config.REGIONS                      # LB 표기 순서 (US_West …)
LB_T0 = pd.Timestamp("2025-01-01 00:00:00")         # 로드밸런서 실험 t=0 (UTC)
RT_BASE = pd.Timestamp("2026-01-01 00:00:00")       # LSTM 라이브 데모 t=0 (UTC)

YEAR_JOBS_CSV = str(lb_config.JOBS_CSV)
YEAR_ASSIGN_CSV = str(lb_config.RESULTS_DIR / "assign_alpha_auto.csv")


def lb_ts(series_s):
    """초 단위(2025 축) → 실제 UTC 시각."""
    return LB_T0 + pd.to_timedelta(series_s, unit="s")


def lb_results_available() -> bool:
    return (lb_config.RESULTS_DIR / "summary.json").exists()


def lb_summary_mtime():
    p = lb_config.RESULTS_DIR / "summary.json"
    return p.stat().st_mtime if p.exists() else 0.0


@functools.lru_cache(maxsize=2)
def _lb_load_all(mtime):
    """mtime 은 캐시 키 — summary.json 이 바뀌면 자동 재로딩."""
    from load_balancer.framework.simulator import CarbonSeries

    summary = json.loads((lb_config.RESULTS_DIR / "summary.json").read_text())
    carbon = CarbonSeries().frame()            # time_s + LB 리전 8열 (실측)
    jobs = pd.read_csv(lb_config.JOBS_CSV)
    latency = lb_config.load_latency_matrix()
    slots = {name: pd.read_csv(lb_config.RESULTS_DIR / f"slots_{name}.csv") for name in summary}
    assigns = {}
    for name in summary:
        a = pd.read_csv(lb_config.RESULTS_DIR / f"assign_{name}.csv")
        if "submit_time" not in a.columns:
            a = a.merge(jobs[["job_name", "submit_time"]], on="job_name")
        assigns[name] = a
    return dict(summary=summary, carbon=carbon, jobs=jobs, latency=latency,
                slots=slots, assigns=assigns)


def lb_load_all() -> dict:
    return _lb_load_all(lb_summary_mtime())


def lb_alpha_runs(summary: dict) -> tuple[list[str], str | None]:
    """summary 의 run 이름 중 α run 을 숫자 오름차순, auto 는 맨 뒤로."""
    def key(run):
        part = run.split("_")[1]
        return 1.5 if part == "auto" else float(part)
    runs = sorted([k for k in summary if k.startswith("alpha_") and "_l" not in k], key=key)
    auto = next((k for k in runs if k.split("_")[1] == "auto"), None)
    return runs, auto


# ── 스케줄러 검증 (2025년 1년치, 백그라운드) ──────────────────────
_val = {"status": "idle", "started": None, "elapsed": None, "error": None,
        "results": None, "comparison": None, "n_jobs": 0, "horizon_hours": 0,
        "carbon_is_real": None, "backend": None}
_val_lock = threading.Lock()


def _run_validation():
    from scheduler import carbon_forecast, data_loader, metrics, simulator

    t0 = time.time()
    try:
        jobs = data_loader.load_jobs_with_assignment(YEAR_JOBS_CSV, YEAR_ASSIGN_CSV)
        horizon = max(j["deadline"] for j in jobs) + 24
        carbon_series, is_real = carbon_forecast.load_actual_series(int(horizon) + 48)
        results = simulator.run_all_modes(jobs, carbon_series)
        comparison = metrics.compare_modes(results)
        with _val_lock:
            _val.update(status="done", results=results, comparison=comparison,
                        n_jobs=len(jobs), horizon_hours=horizon, carbon_is_real=is_real,
                        backend=carbon_forecast.backend_info(),
                        elapsed=time.time() - t0, error=None)
    except Exception as e:
        with _val_lock:
            _val.update(status="error", error=f"{type(e).__name__}: {e}",
                        elapsed=time.time() - t0)


def start_validation_async(force: bool = False) -> bool:
    """스케줄러 검증 시뮬레이션을 백그라운드 스레드로 시작한다 (이미 돌고 있으면 무시)."""
    with _val_lock:
        if _val["status"] == "running":
            return False
        if _val["status"] == "done" and not force:
            return False
        _val.update(status="running", started=time.time(), error=None)
    threading.Thread(target=_run_validation, daemon=True, name="sched-validation").start()
    return True


def validation_state() -> dict:
    with _val_lock:
        return dict(_val)


def validation_detail(val: dict) -> str:
    """검증 상태 한 줄 설명. 상태마다 채워지는 필드가 달라(elapsed 등) 반드시 분기해서 포맷한다."""
    status = val["status"]
    if status == "done":
        return f"2025년 1년치 검증 완료 — job {val['n_jobs']:,}개, {val['elapsed']:.0f}초"
    if status == "running":
        return "2025년 1년치 검증 시뮬레이션 실행 중… (스케줄러 화면에서 확인)"
    if status == "error":
        return f"검증 실패: {val['error']}"
    return "검증 미실행"


# ── 실시간 라우팅 (로드밸런서 ④) ───────────────────────────────
def rt_t_range() -> tuple[int, int]:
    """LSTM 라이브가 응답 가능한 슬롯 범위 (2026 축, 시간). 이력 168h 이후 ~ 데이터 끝-24h."""
    st = api.status()
    t_min = 168
    if st["history_end"] is not None:
        t_max = int((st["history_end"] - RT_BASE).total_seconds() // 3600) - 24
    else:
        t_max = t_min + 24 * 30
    return t_min, max(t_min, t_max)


@functools.lru_cache(maxsize=512)
def realtime_route_slot(t_hour: int, alpha: str) -> dict:
    """슬롯 하나를 지금 LSTM 예측 + ILP 로 배정 (realtime_route.py 위임)."""
    from load_balancer.framework import realtime_route as rt

    jobs_slot = rt.load_slot_jobs(int(t_hour), None)
    return rt.route_slot(int(t_hour), jobs_slot, str(alpha), None, 0.8, None)


# ── 로드밸런서 실험 재실행 (백그라운드 프로세스, ~40분) ───────────
_exp = {"status": "idle", "proc": None, "log": None, "started": None, "returncode": None}
_exp_lock = threading.Lock()
_EXP_LOG = os.path.join(str(lb_config.RESULTS_DIR), "run_experiments.log")


def start_experiments() -> bool:
    with _exp_lock:
        if _exp["proc"] is not None and _exp["proc"].poll() is None:
            return False
        os.makedirs(str(lb_config.RESULTS_DIR), exist_ok=True)
        # 프로세스가 끝날 때까지 열어 둬야 하므로 with 를 쓸 수 없다 — experiments_state() 가 닫는다
        log = open(_EXP_LOG, "w", encoding="utf-8")  # noqa: SIM115
        proc = subprocess.Popen(
            [sys.executable, "-m", "load_balancer.framework.run_experiments"],
            cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT)
        _exp.update(status="running", proc=proc, log=log, started=time.time(), returncode=None)
        return True


def experiments_state() -> dict:
    with _exp_lock:
        proc = _exp["proc"]
        if proc is not None and _exp["status"] == "running" and proc.poll() is not None:
            _exp["status"] = "done" if proc.returncode == 0 else "error"
            _exp["returncode"] = proc.returncode
            with contextlib.suppress(Exception):
                _exp["log"].close()
            _lb_load_all.cache_clear()
        tail = ""
        if os.path.exists(_EXP_LOG):
            with open(_EXP_LOG, encoding="utf-8", errors="replace") as f:
                tail = "".join(f.readlines()[-30:])
        return dict(status=_exp["status"], started=_exp["started"],
                    returncode=_exp["returncode"], log_tail=tail)


# ── 서버 기동 시 미리 데우기 ─────────────────────────────────────
def warm_up_async() -> None:
    """첫 화면이 빨리 뜨도록 무거운 로딩을 백그라운드에서 미리 한다."""
    def _warm():
        try:
            api.status()                    # LSTM 모델 로드 (~10초)
            from interface.dashboard import live as core
            core.load_map_jobs()            # 146k job
            core.load_map_actual()
        except Exception as e:
            print(f"[warm-up] 메인 화면 준비 실패: {e}", file=sys.stderr)
        try:
            if lb_results_available():
                lb_load_all()
        except Exception as e:
            print(f"[warm-up] 로드밸런서 결과 로딩 실패: {e}", file=sys.stderr)
        start_validation_async()
    threading.Thread(target=_warm, daemon=True, name="warm-up").start()


def to_std(region_lb: str) -> str:
    """LB 표기 → 표준 코드 (이미 표준이면 그대로)."""
    return LB_TO_REGION.get(region_lb, region_lb)


__all__ = [
    "LB_REGIONS",
    "LB_T0",
    "REGIONS",
    "REPO_ROOT",
    "RT_BASE",
    "experiments_state",
    "lb_alpha_runs",
    "lb_load_all",
    "lb_results_available",
    "lb_ts",
    "np",
    "realtime_route_slot",
    "rt_t_range",
    "start_experiments",
    "start_validation_async",
    "to_std",
    "validation_state",
    "warm_up_async",
]
