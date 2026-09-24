# -*- coding: utf-8 -*-
"""2d 지시(2026-09-24, f6 제기) — 표5(선행 정책 재현) 네 행이 전부 같은
회계 함수(prior_harness.score, 내부적으로 capacity._Windows.actual_mean)를
타는지 확인하고, actual_mean(=slot 정수경계 평균근사)이 아니라 §5.7/§3.5가
서술한 "겹침 길이 가중 정확 적분"으로 다시 채점했을 때 얼마나 달라지는지 잰다.

**스케줄(각 정책의 배정 결과)은 절대 다시 안 만든다** — 각 prior_*.py 모듈의
기존 결정-생성 함수를 그대로 호출해서 받은 decisions를 두 가지 잣대로만
다시 센다:
  (a) 지금 표에 쓴 값 — prior_harness.score()(=actual_mean 근사)
  (b) 겹침 길이 가중 정확 적분 — exact_score()(아래)

actual_mean 근사의 정의(capacity._Windows.actual_mean, 참고용 재게재):
    a = floor(start), b = a + max(1, ceil(dur))
    return (cumsum[b]-cumsum[a]) / (b-a)      # 정수 시간 a~b 구간의 "단순 평균"
정확 적분:
    각 정수 시간 h가 [start, start+dur) 와 겹치는 길이 × 그 시간의 실측값,
    전부 더한 값 (= §5.7 식(16)이 산문으로 서술한 그대로).
"""
import math

from interface.regions import REGIONS, LB_TO_REGION
from load_balancer.framework.config import JOBS_CSV, RESULTS_DIR, load_latency_matrix

from . import capacity, data_loader
from . import prior_harness as H

BASELINE_KG = 29225.6


def exact_integral(actual_series, start, dur):
    """겹침 길이 가중 정확 적분 — §5.7/§3.5가 서술한 그대로. 총합(구간 적분값)을 반환."""
    if dur <= 0:
        return 0.0
    end = start + dur
    h0 = int(math.floor(start))
    h1 = int(math.ceil(end))
    n = len(actual_series)
    total = 0.0
    for h in range(h0, h1):
        hh = min(max(h, 0), n - 1)
        seg = min(end, h + 1) - max(start, h)
        if seg > 0:
            total += actual_series[hh] * seg
    return total


def exact_score(decisions, jobs, actual, latency, label=""):
    ri = {r: i for i, r in enumerate(REGIONS)}
    by_id = {j["id"]: j for j in jobs}
    tot_g, lat_sum, miss = 0.0, 0.0, 0
    recs = {}
    for jid, (r, start) in decisions.items():
        j = by_id[jid]
        d = j["duration"]
        g = exact_integral(actual[r], start, d)
        tot_g += g
        home = j["region"]
        lat_sum += float(latency[ri[home]][ri[r]])
        if start + d > j["deadline"] + 1e-9:
            miss += 1
        recs[jid] = dict(region=r, scheduled_start=start, duration=d)
    from .prior_harness import _over_cap
    return dict(
        label=label, n=len(decisions), total_carbon_kg=tot_g / 1000.0,
        avg_latency_ms=lat_sum / len(decisions), deadline_misses=miss,
        capacity_violations=_over_cap(recs, H.CAP),
    )


def compare(name, decisions, jobs, actual, W, latency):
    approx = H.score(decisions, jobs, W, latency, label=name)
    exact = exact_score(decisions, jobs, actual, latency, label=name)
    delta_pct = 100 * (exact["total_carbon_kg"] - approx["total_carbon_kg"]) / approx["total_carbon_kg"]
    savings_approx = 100 * (1 - approx["total_carbon_kg"] / BASELINE_KG)
    savings_exact = 100 * (1 - exact["total_carbon_kg"] / BASELINE_KG)
    return dict(name=name, approx=approx, exact=exact, delta_pct=delta_pct,
                savings_approx=savings_approx, savings_exact=savings_exact)


def format_result(r):
    a, e = r["approx"], r["exact"]
    lines = [
        f"[{r['name']}]",
        f"  근사(actual_mean, 현재 표 값): {a['total_carbon_kg']:,.1f} kg, 절감률 {r['savings_approx']:.2f}%, "
        f"지연 {a['avg_latency_ms']:.1f} ms, 마감위반 {a['deadline_misses']:,}, 용량위반 {a['capacity_violations']:,}",
        f"  정확 적분(겹침가중):          {e['total_carbon_kg']:,.1f} kg, 절감률 {r['savings_exact']:.2f}%, "
        f"지연 {e['avg_latency_ms']:.1f} ms, 마감위반 {e['deadline_misses']:,}, 용량위반 {e['capacity_violations']:,}",
        f"  배출량 차이: {r['delta_pct']:+.3f}%  (절감률 차이 {r['savings_exact']-r['savings_approx']:+.3f}%p)",
    ]
    return "\n".join(lines)


def main():
    import time

    jobs, actual, pred24, W, latency = H.load_all()
    out_lines = []
    out_lines.append("표5(선행 정책 재현) 회계 검증 — actual_mean 근사 vs 겹침가중 정확적분")
    out_lines.append("=" * 70)
    out_lines.append("")
    out_lines.append("0) 회계 함수 공용 사용 여부 확인")
    out_lines.append("-" * 40)
    out_lines.append("소스 검사 결과: CASPER·CICS·Sukprasert 세 모듈 전부 자기 회계 없이 "
                      "prior_harness.score()만 호출한다(grep으로 확인, 세 파일 다 "
                      "'회계는 이 파일이 하지 않는다' 류의 주석과 함께 H.score() 호출 1곳뿐).")
    out_lines.append("Caspian은 prior_harness.score()를 쓰되 내부 결정 과정(용량 판단)에서만 "
                      "별도의 근사(capacity._Windows.pred_mean, 예측용 — 회계와는 무관)를 쓴다. "
                      "실측 회계는 전부 H.score() 하나로 통일돼 있다.")
    out_lines.append("")

    results = []

    # --- CASPER ---
    print("CASPER 실행 중...", flush=True)
    from . import prior_casper as CASPER
    t0 = time.time()
    dec = CASPER.run_casper(jobs, actual, latency, CASPER.ALPHA_CAP, policy="carbon")
    print(f"  CASPER: {time.time()-t0:.1f}s", flush=True)
    results.append(compare("CASPER(CAP, α=0.9)", dec, jobs, actual, W, latency))

    # --- CICS ---
    print("CICS 실행 중...", flush=True)
    from . import prior_cics as CICS
    t0 = time.time()
    _, dec = CICS.run(lam_ratio=0.0, verbose=False)
    print(f"  CICS: {time.time()-t0:.1f}s", flush=True)
    results.append(compare("CICS(λp/λe=0.0)", dec, jobs, actual, W, latency))

    # --- Sukprasert ---
    print("Sukprasert 실행 중...", flush=True)
    from . import prior_sukprasert as SUK
    t0 = time.time()
    dec_t = SUK.temporal_decisions(jobs, actual)
    print(f"  Sukprasert(시간단독): {time.time()-t0:.1f}s", flush=True)
    results.append(compare("Sukprasert(시간이동단독)", dec_t, jobs, actual, W, latency))

    t0 = time.time()
    dec_st = SUK.spatiotemporal_decisions(jobs, actual)
    print(f"  Sukprasert(공간+시간): {time.time()-t0:.1f}s", flush=True)
    results.append(compare("Sukprasert(공간+시간결합)", dec_st, jobs, actual, W, latency))

    # --- Caspian: 아직 전체스케일 미완료 — 이용 가능한 60일 표본으로 예비 확인 ---
    import json
    from pathlib import Path
    sweep_dir = Path(__file__).parent / "caspian_sweep_results"
    for label, fname in [("Caspian(60일 표본, 올림)", "bind_study_ceiling_decisions.json"),
                          ("Caspian(60일 표본, 분수)", "bind_study_fractional_decisions.json")]:
        p = sweep_dir / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            dec = {k: tuple(v) for k, v in raw.items()}
            sub_ids = set(dec.keys())
            sub_jobs = [j for j in jobs if j["id"] in sub_ids]
            results.append(compare(label, dec, sub_jobs, actual, W, latency))
    # 전체스케일 준비되면 자동으로 잡힌다(run_caspian_sweep.py가 남기는 실제 파일명 패턴)
    for label, fname in [("Caspian(전체, ω1=1, 올림)", "omega1_1.0_ceiling_decisions.json"),
                          ("Caspian(전체, ω1=1, 분수)", "omega1_1.0_fractional_decisions.json")]:
        p = sweep_dir / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            dec = {k: tuple(v) for k, v in raw.items()}
            results.append(compare(label, dec, jobs, actual, W, latency))

    out_lines.append("1) 정책별 근사 vs 정확적분 비교")
    out_lines.append("-" * 40)
    for r in results:
        out_lines.append(format_result(r))
        out_lines.append("")

    out_lines.append("2) 가설 검증 — '프랑스 몰빵'(격차 작은 리전 집중) 정책일수록 차이가 작은가?")
    out_lines.append("-" * 40)
    max_abs = max(abs(r["delta_pct"]) for r in results)
    min_abs = min(abs(r["delta_pct"]) for r in results)
    out_lines.append(f"관측된 |배출량 차이| 범위: {min_abs:.4f}% ~ {max_abs:.4f}%")
    for r in results:
        out_lines.append(f"  {r['name']}: {r['delta_pct']:+.4f}%")

    text = "\n".join(out_lines)
    print(text)
    out_path = Path(__file__).parent.parent / "paper" / "문서" / "회계검증_표5.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n완료 → {out_path}")


if __name__ == "__main__":
    main()
