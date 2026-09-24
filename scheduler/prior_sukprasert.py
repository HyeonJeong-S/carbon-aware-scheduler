"""Sukprasert 등(EuroSys'24, "On the Limitations of Carbon-Aware Temporal and
Spatial Workload Shifting in the Cloud")의 정책을 원문 코드 그대로 우리 데이터에
적용한다.

원본 코드: https://github.com/umassos/decarbonization-potential
  (Zenodo 스냅샷 10.5281/zenodo.10790855, 재현성 배지 Available/Functional/
  Results Reproduced)

원본 알고리즘 (코드 기준, 논문 §3 산문이 아니라 실제 구현을 따름)
------------------------------------------------------------
1. 시간 이동 — sim_temporal/experiment_vary_job_slack.py `task()`:
     rolling_df = carbon[zone].iloc[i : i+slack+job].rolling(job).sum()
     lowest_non_interrupt = rolling_df.min()
   즉 [제출시각, 제출시각+slack+작업길이) 창 안에서, 작업 길이만큼 연속된
   구간의 탄소집약도 합이 최소인 시작점을 고른다(비-중단형). 리전은 고정.

2. 공간+시간 결합 — sim_what_ifs/temporal_spatial_combined/calculate_combined_savings.py:
     spatial_savings = carbon_df.subtract(carbon_df[dest], axis=0)
     combined_savings = spatial_savings.add(temporal_savings, axis=0)
   목적지 리전을 먼저 정하고 그 리전 안에서 시간 이동을 더하는 구조 — 논문
   §3.2.2 "the optimal spatial shifting policy is simply to run the job in
   the lowest carbon region"과 일치. 리전 선택에 제약이 없으므로(Table 1에
   capacity 차원이 아예 없음), 개별 작업 단위로 다시 쓰면 "(리전, 시작시각)
   격자 전수 탐색에서 구간 합이 최소인 조합을 고른다"와 동치다.

우리 데이터에 적용하며 그대로 지킨 것
--------------------------------------
- **완전예지**: §3.2.1 "we assume perfect knowledge of the future
  carbon-intensity and job length." → `actual` 계열만 쓴다. pred24(LSTM)는
  이 파일에서 참조하지 않는다.
- **용량 제약 없음**: Table 1(워크로드 특성 차원 표)에 용량 항목이 없다.
  → 리전별 동시 실행 수를 전혀 확인하지 않는다.
- **비-중단형(non-interruptible)**: 원본의 `lowest_interrupt`(전 구간에서
  가장 싼 시간만 골라 붙이는 중단형) 대신 `lowest_non_interrupt`(연속 구간)를
  썼다 — CAST의 작업은 연속 실행을 전제하므로 이쪽이 대응된다. 원본 코드도
  두 값을 다 계산해 두지만, 우리가 재현하는 건 non-interrupt 쪽이다.

우리 데이터에 맞추며 바꾼 것 (알고리즘 자체는 안 건드림)
--------------------------------------------------------
- **slack 값**: 원 논문 실험은 집계 분석을 위해 slack을 24/168/480/.../8760h로
  고정해 스윕한다. §3.1(Table 1)은 애초에 slack을 "job이 갖는 한 차원"으로
  일반화해 두었으므로, 여기서는 작업마다 실제 deadline(k등급별 L_max)을
  그 작업의 slack으로 그대로 대입한다 — 고정 스윕값은 저자들의 "집계용" 선택일
  뿐 알고리즘의 제약이 아니다.
- **시간 해상도**: 원본은 정수 시간 rolling(hour 단위 판다스 인덱스)이다.
  CAST 작업 duration은 분·초 단위도 있는 실수(hour)다. `rolling(job).sum()`을
  `actual_mean(r, t, dur) * dur`(구간 평균 × 길이 = 구간 합, capacity.py의
  누적합 함수 그대로 사용)로 대체했다 — 정수 시간에서는 두 계산이 완전히
  동일한 값을 낸다.
- **탐색 시작시각 해상도**: 원본처럼 1시간 격자(정수 시)로 시작시각을 스캔한다
  (원본 rolling 인덱스와 동일한 해상도).

회계는 이 파일이 하지 않는다 — `{job_id: (region, start_hour)}`만 반환하고,
`scheduler.prior_harness.score()`가 §5.7 식(16) 그대로 채점한다.
"""
import numpy as np

from interface.regions import REGIONS

from . import capacity


def _search(jobs, W, regions):
    """(리전, 시작시각) 격자 전수 탐색 — 원본 rolling(job).sum().min()의
    실수-시간·다중-리전 버전. regions가 한 개짜리 dict-getter면 시간 이동
    단독(리전 고정), REGIONS 전체면 공간+시간 결합이 된다."""
    out = {}
    for j in jobs:
        s, d, dl = j["submit_time"], j["duration"], j["deadline"]
        t0 = int(np.floor(s))
        t1 = int(np.floor(dl - d))
        if t1 < t0:
            t1 = t0
        cand_regions = regions(j)
        best_val, best_r, best_t = None, None, None
        for r in cand_regions:
            for t in range(t0, t1 + 1):
                val = W.actual_mean(r, t, d) * d
                if best_val is None or val < best_val:
                    best_val, best_r, best_t = val, r, t
        out[j["id"]] = (best_r, best_t)
    return out


def temporal_decisions(jobs, actual):
    """시간 이동 단독 — 리전은 작업의 출발 리전(carbon_region, LB가 이미
    정한 실행 리전)으로 고정, 그 리전 안에서만 원 논문의 창 탐색을 한다."""
    W = _windows(actual)
    return _search(jobs, W, lambda j: (j.get("carbon_region") or j["region"],))


def spatiotemporal_decisions(jobs, actual):
    """공간+시간 결합 — 8개 리전 전체를 대상으로 (리전, 시작시각) 전수 탐색."""
    W = _windows(actual)
    return _search(jobs, W, lambda j: REGIONS)


def _windows(actual):
    """capacity._Windows는 pred24도 요구하므로, 안 쓸 더미 배열로 생성한다
    (완전예지 원칙상 예측 계열은 절대 읽지 않음 — act만 쓴다)."""
    dummy_pred = {r: np.zeros((len(v), capacity.HORIZON)) for r, v in actual.items()}
    return capacity._Windows(actual, dummy_pred)


if __name__ == "__main__":
    import time

    from . import prior_harness as H

    jobs, actual, pred24, W, latency = H.load_all()
    print(f"작업 {len(jobs):,}건")

    t0 = time.time()
    dec_t = temporal_decisions(jobs, actual)
    print(f"시간 이동 단독 탐색: {time.time()-t0:.1f}s")
    s = H.score(dec_t, jobs, W, latency, label="Sukprasert 시간이동단독(완전예지·무용량)")
    print(f"{s['label']}: {s['total_carbon_kg']:,.1f} kg, 지연 {s['avg_latency_ms']:.1f} ms, "
          f"마감위반 {s['deadline_misses']}, 용량위반 {s['capacity_violations']}")

    t0 = time.time()
    dec_st = spatiotemporal_decisions(jobs, actual)
    print(f"공간+시간 결합 탐색: {time.time()-t0:.1f}s")
    s = H.score(dec_st, jobs, W, latency, label="Sukprasert 공간+시간결합(완전예지·무용량)")
    print(f"{s['label']}: {s['total_carbon_kg']:,.1f} kg, 지연 {s['avg_latency_ms']:.1f} ms, "
          f"마감위반 {s['deadline_misses']}, 용량위반 {s['capacity_violations']}")
