"""같은 지연 짝(CAST vs 비교 설계)을 탄소 회계 여러 개로 다시 채점한 짝표. 배정은 그대로, 채점만 바꾼다.

회계(공식은 기존 스크립트 그대로 가져다 쓴다):
  avg          평균 계수 — 저장된 carbon_emitted
  tx_dest      전송 목적지 귀속 (transfer_sensitivity.py) — 옮긴 작업마다 + 0.06 kWh × 목적지 강도(carbon_emitted/duration)
  tx_origin    전송 출발지 귀속 (transfer_breakeven.py) — 옮긴 작업마다 + 1 GB × 0.06 kWh/GB × 출발 리전 actual_mean(origin, 시작, 길이)
  lca          전과정 근사 (lca_rescore.lca_actual)
  marg_fr      한계 상한, 프랑스만 (marginal_rescore.py) — 프랑스로 옮긴 작업을 같은 시각 독일 강도로
  fossil_f     대칭 화석 몫 대리 (fossil_rescore.fossil_actual), FLOOR f ∈ {0.05(본), 0.02, 0.1, 0.2}
  pue_adv      PUE 불리 — FR·US-CAL-CISO 에서 × 1.6, 나머지 × 1.1 (기준도 같은 계수)
  pue_fav      PUE 유리 — 거꾸로 (FR·US-CAL-CISO × 1.1, 나머지 × 1.6)
  exact        정확 겹침 — 실행 구간과 각 시간의 겹친 길이로 실측을 가중 적분(accounting_check_table5.exact_integral)
  fossil_med   대칭 화석 대리에서 하한(0.05)이 걸리는 시각만 그 리전의 하한 밖 시각 C/(1−f) 중앙값으로(프랑스 약 400 g) — 10-19 5회차 A
  adv_comb     불리 겹침 — 프랑스만 한계 상한 + 출발지 전송 1 GB + PUE 불리(PUE 는 실행 전력에만; 전송은 망 에너지라 곱하지 않음) — 10-19 5회차 A
기준 kg = 집에서 바로 도는 실행(합성 frontier/cast_rho0_a0.0, Azure azure/rho0_alpha_0.0; 둘 다 절감 0.00%)을 같은 회계로 다시 채점한 값.
Δ(pp) = (비교 kg − CAST kg) ÷ 기준 kg × 100 (양수 = CAST 가 덜 배출).
CI = analysis_alpha.pair_mode 와 같은 7일 블록 부트스트랩(B=2000, seed 0, score_from 168, 날 = submit_time//24)으로 Δkg 의 2.5/97.5 백분위를 낸 뒤
1년 기준 kg 으로 나눈다(기존 pair json 의 Δ 0.96 [0.51, 1.46] 이 이렇게 나온 값).
    ./.venv/bin/python -m scheduler.pair_accounting_table
"""
import json
import os

import numpy as np
import pandas as pd

from interface import carbon_2025
from scheduler import capacity, fossil_rescore
from scheduler.accounting_check_table5 import exact_integral
from scheduler.analysis_alpha import BLOCK, B
from scheduler.lca_rescore import lca_actual
from scheduler.marginal_rescore import PROXY, SINK

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "scheduler", "data", "v2")
OUT_JSON = os.path.join(V2, "analysis", "pair_accounting_table.json")
OUT_TXT = os.path.join(ROOT, "paper", "v2", "보관", "점검", "28쪽보강_2회차", "회계별_짝표.txt")
SCORE_FROM = 168
E_TX = 0.06          # kWh / 옮긴 작업 (목적지 귀속), = 1 GB × 0.06 kWh/GB (출발지 귀속)
FLOORS = (0.05, 0.02, 0.1, 0.2)
PUE_HI, PUE_LO, PUE_HOT = 1.6, 1.1, ("FR", "US-CAL-CISO")

PAIRS = [  # (열 이름, CAST, 비교, 기준 실행, 대조할 기존 pair json)
    ("합성 도착 고정형", "rho0/m0.5375", "arrival/fixed_rho0_dw0.5444", "frontier/cast_rho0_a0.0", "pair_rho0_cast0.5375_vs_af_dw.json"),
    ("합성 빈 리전", "rho0/m0.5375", "startadmit/fb_rho0_dw0.5353", "frontier/cast_rho0_a0.0", "pair_rho0_cast0.5375_vs_fb_dw.json"),
    ("Azure 도착 고정형", "azure/rho0_m0.5375", "azure/af_rho0_dw0.5381", "azure/rho0_alpha_0.0", "alpha_pair_azure_rho0_m0.5375.json"),
    ("Azure 빈 리전", "azure/rho0_m0.5375", "azure/fb_rho0_dw0.5184", "azure/rho0_alpha_0.0", "pair_azure_rho0_cast0.5375_vs_fb0.5184.json"),
]
ACC = [("avg", "평균 계수"), ("exact", "정확 겹침"), ("tx_dest", "전송 목적지 귀속 0.06 kWh"), ("tx_origin", "전송 출발지 귀속 1 GB"),
       ("lca", "전과정 근사"), ("marg_fr", "한계 상한(프랑스만)"), ("fossil_0.05", "대칭 화석 대리 floor 0.05"),
       ("fossil_0.02", "  〃 floor 0.02"), ("fossil_0.1", "  〃 floor 0.1"), ("fossil_0.2", "  〃 floor 0.2"),
       ("pue_adv", "PUE 불리(FR·CAL 1.6)"), ("pue_fav", "PUE 유리(FR·CAL 1.1)"),
       ("fossil_med", "대칭 화석 대리, 하한 시각은 하한 밖 중앙값"), ("adv_comb", "불리 겹침(프랑스만+출발지 1 GB+PUE 불리)")]
# 기존 스크립트가 찍은 절감률(소수 둘째 자리) — 다시 채점한 합계가 이것을 재현해야 믿는다
EXPECT = {("rho0/m0.5375", "marg_fr"): 37.59, ("arrival/fixed_rho0_dw0.5444", "marg_fr"): 38.49,
          ("startadmit/fb_rho0_dw0.5353", "marg_fr"): 39.75,
          ("rho0/m0.5375", "fossil_0.05"): 34.81, ("arrival/fixed_rho0_dw0.5444", "fossil_0.05"): 33.62,
          ("rho0/m0.5375", "lca"): 64.03, ("arrival/fixed_rho0_dw0.5444", "lca"): 63.08,
          ("rho0/m0.5375", "tx_dest"): 67.82, ("arrival/fixed_rho0_dw0.5444", "tx_dest"): 66.79,
          ("azure/rho0_m0.5375", "tx_dest"): 49.41}


def windows():
    data = carbon_2025.load_2025()
    a, p = data["actual"], data["pred24"]
    W = {"avg": capacity._Windows(a, p), "lca": capacity._Windows(lca_actual(a), p)}
    for f in FLOORS:
        fossil_rescore.FLOOR = f                      # fossil_actual 은 모듈 전역 FLOOR 를 부를 때 읽는다
        W[f"fossil_{f}"] = capacity._Windows(fossil_rescore.fossil_actual(a), p)
    W["fossil_med"] = capacity._Windows(fossil_median(a), p)
    W["_actual"] = a
    return W


def fossil_median(actual):
    """fossil_actual 과 같되, 1−CFE 가 0.05 아래인 시각은 하한 대신 그 리전의 하한 밖 시각 C/(1−CFE) 중앙값을 쓴다."""
    df = pd.read_csv(os.path.join(ROOT, "lstm_source", "data", "carbon_intensity_test_2025.csv"), parse_dates=["timestamp"])
    df["h"] = ((df.timestamp - carbon_2025.BASE_TIME).dt.total_seconds() / 3600).round().astype(int)
    out = {}
    for r, arr in actual.items():
        s = df[df.region == r].set_index("h")
        frac = np.full(len(arr), np.nan)
        idx = s.index[(s.index >= 0) & (s.index < len(arr))]
        frac[idx] = 1 - s.loc[idx, "cfe_pct"].values / 100
        frac = pd.Series(frac).ffill().bfill().values
        ok = frac >= 0.05
        raw = arr / np.where(ok, frac, 1.0)
        out[r] = np.where(ok, raw, np.median(raw[ok]))
    return out


def load(name):
    st = json.load(open(os.path.join(V2, name, "stats.json")))
    assert st["score_from"] == SCORE_FROM, (name, st["score_from"])
    d = pd.read_csv(os.path.join(V2, name, "jobs.csv.gz"))
    d = d[d.submit_time >= SCORE_FROM].sort_values("job_id").reset_index(drop=True)
    assert abs(d.carbon_emitted.sum() / 1000 - st["total_carbon_kg"]) < 0.05, name
    return st, d


def rescore(d, W):
    """작업별 배출(g) — 회계마다 한 열."""
    ce = d.carbon_emitted.to_numpy(dtype=float)
    moved = (d.region != d.origin).to_numpy()
    at = lambda w, regs, starts: np.array([w.actual_mean(r, s, x) * x for r, s, x in zip(regs, starts, d.duration)])  # noqa: E731
    e = {"avg": ce}
    e["tx_dest"] = ce + np.where(moved, ce / d.duration.to_numpy() * E_TX, 0.0)
    inten_o = np.array([W["avg"].actual_mean(o, s, x) if m else 0.0
                        for o, s, x, m in zip(d.origin, d.scheduled_start, d.duration, moved)])
    e["tx_origin"] = ce + inten_o * E_TX
    e["lca"] = at(W["lca"], d.region, d.scheduled_start)
    mf = ((d.region == SINK) & (d.origin != SINK)).to_numpy()
    mg = ce.copy()
    mg[mf] = [W["avg"].actual_mean(PROXY, s, x) * x for s, x in zip(d.scheduled_start[mf], d.duration[mf])]
    e["marg_fr"] = mg
    for f in FLOORS:
        e[f"fossil_{f}"] = at(W[f"fossil_{f}"], d.region, d.scheduled_start)
    hot = d.region.isin(PUE_HOT).to_numpy()
    e["pue_adv"] = ce * np.where(hot, PUE_HI, PUE_LO)
    e["pue_fav"] = ce * np.where(hot, PUE_LO, PUE_HI)
    e["exact"] = np.array([exact_integral(W["_actual"][r], s, x) for r, s, x in zip(d.region, d.scheduled_start, d.duration)])
    e["fossil_med"] = at(W["fossil_med"], d.region, d.scheduled_start)
    e["adv_comb"] = mg * np.where(hot, PUE_HI, PUE_LO) + inten_o * E_TX
    return e


def baseline_check(d, W):
    """기존 스크립트식 기준(출발 리전·제출 시각) — 집에서 바로 도는 실행의 재채점과 같아야 한다."""
    out = {}
    for k in ("avg", "lca", "fossil_med", *[f"fossil_{f}" for f in FLOORS]):
        out[k] = sum(W[k].actual_mean(o, s, x) * x for o, s, x in zip(d.origin, d.submit_time, d.duration)) / 1000
    out["exact"] = sum(exact_integral(W["_actual"][o], s, x) for o, s, x in zip(d.origin, d.submit_time, d.duration)) / 1000
    return out


def per_day(d, e):
    day = (d.submit_time // 24).astype(int).to_numpy()
    return pd.DataFrame({k: v / 1000.0 for k, v in e.items()}).groupby(day).sum()


def boot_counts(days):
    """analysis_alpha.pair_mode 와 같은 난수 흐름 — 표본마다 날별 뽑힌 횟수."""
    rng = np.random.default_rng(0); nb = len(days) // BLOCK
    C = np.zeros((B, len(days)))
    for b in range(B):
        for bi in rng.integers(0, nb, nb):
            C[b, bi * BLOCK:(bi + 1) * BLOCK] += 1
    return C


def main():
    W = windows()
    cache = {}

    def get(name):
        if name not in cache:
            st, d = load(name)
            cache[name] = (st, d, rescore(d, W))
            print(f"  채점: {name} ({len(d):,} 작업)", flush=True)
        return cache[name]

    res, problems = {}, []
    for col, cast, comp, base, ref in PAIRS:
        stc, dc, ec = get(cast); _, dp, ep = get(comp); stb, db, eb = get(base)
        assert (db.region == db.origin).all() and (db.scheduled_start == db.submit_time).all(), base
        assert abs(stb["savings_pct"]) < 1e-6
        assert dc.job_id.tolist() == dp.job_id.tolist() == db.job_id.tolist(), "작업 집합이 다름"
        bkg = {k: v.sum() / 1000 for k, v in eb.items()}
        if abs(bkg["avg"] - stc["baseline_kg"]) > 0.05:
            problems.append(f"{col}: 기준 실행 kg {bkg['avg']:.2f} ≠ stats baseline {stc['baseline_kg']:.2f}")
        for k, v in baseline_check(db, W).items():
            if abs(v - bkg[k]) > 0.5:
                problems.append(f"{col}: {k} 기준 재채점 {bkg[k]:.2f} ≠ 기존식 {v:.2f}")
        kc, kp = per_day(dc, ec), per_day(dp, ep)
        days = sorted(set(kc.index) & set(kp.index))
        C = boot_counts(days)
        rows = {}
        for k, _ in ACC:
            ck, pk = float(kc.loc[days, k].sum()), float(kp.loc[days, k].sum())
            dk = (kp.loc[days, k] - kc.loc[days, k]).to_numpy()
            bs = C @ dk
            ci_kg = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
            rows[k] = dict(base_kg=bkg[k], cast_kg=ck, comp_kg=pk, d_kg=pk - ck, ci_d_kg=ci_kg,
                           cast_sav=100 * (1 - ck / bkg[k]), comp_sav=100 * (1 - pk / bkg[k]),
                           d_pp=100 * (pk - ck) / bkg[k], ci_pp=[100 * c / bkg[k] for c in ci_kg])
        # 검증 1: 평균 계수 행이 기존 pair json 을 재현
        old = json.load(open(os.path.join(V2, "analysis", ref)))["작업당평균"]
        r = rows["avg"]
        if abs(old["knee"][1] - r["cast_kg"]) > 1e-3 or abs(old["pair"][1] - r["comp_kg"]) > 1e-3 \
                or max(abs(a - b) for a, b in zip(old["ci_d_kg"], r["ci_d_kg"])) > 1e-3:
            problems.append(f"{col}: 평균 계수 행이 {ref} 와 다름 ({r['d_kg']:.3f} {r['ci_d_kg']} vs {old['d_kg']:.3f} {old['ci_d_kg']})")
        # 검증 2: 기존 스크립트가 찍은 절감률
        for (run, k), want in EXPECT.items():
            for nm, key in ((cast, "cast_sav"), (comp, "comp_sav")):
                if nm == run and round(rows[k][key], 2) != want:
                    problems.append(f"{col}: {run} {k} 절감 {rows[k][key]:.4f} ≠ 기존 {want}")
        res[col] = dict(cast=cast, comp=comp, baseline_run=base, ref_json=ref, n_days=len(days), rows=rows)
        print(f"{col}: 평균 Δ {rows['avg']['d_pp']:.2f} [{rows['avg']['ci_pp'][0]:.2f}, {rows['avg']['ci_pp'][1]:.2f}]", flush=True)

    if problems:
        print("재현 실패 — 표를 쓰지 않는다:\n  " + "\n  ".join(problems))
        raise SystemExit(1)
    meta = dict(score_from=SCORE_FROM, block_days=BLOCK, B=B, seed=0, e_tx_kwh=E_TX, floors=FLOORS,
                pue=dict(hot=PUE_HOT, hi=PUE_HI, lo=PUE_LO),
                ci_note="Δkg 부트스트랩 백분위 ÷ 1년 기준 kg (analysis_alpha.pair_mode 와 같은 난수 흐름)")
    json.dump(dict(meta=meta, pairs=res), open(OUT_JSON, "w"), ensure_ascii=False, indent=1, default=float)

    cols = [p[0] for p in PAIRS]
    L = ["회계별 같은 지연 짝표 — Δ = (비교 kg − CAST kg) ÷ 기준 kg × 100 (%p, 양수 = CAST 가 덜 배출), 괄호는 7일 블록 부트스트랩 95% CI",
         "짝: " + "; ".join(f"{c} = {res[c]['cast']} vs {res[c]['comp']} (기준 {res[c]['baseline_run']})" for c in cols),
         "생성: ./.venv/bin/python -m scheduler.pair_accounting_table  →  scheduler/data/v2/analysis/pair_accounting_table.json", "",
         "회계 | " + " | ".join(f"{c} Δ (CI)" for c in cols)]
    for k, lab in ACC:
        L.append(lab + " | " + " | ".join(
            f"{res[c]['rows'][k]['d_pp']:+.2f} ({res[c]['rows'][k]['ci_pp'][0]:+.2f}~{res[c]['rows'][k]['ci_pp'][1]:+.2f})" for c in cols))
    L += ["", "절감률(%) CAST / 비교", "회계 | " + " | ".join(cols)]
    for k, lab in ACC:
        L.append(lab + " | " + " | ".join(f"{res[c]['rows'][k]['cast_sav']:.2f} / {res[c]['rows'][k]['comp_sav']:.2f}" for c in cols))
    L += ["", "검증: 평균 계수 행은 analysis/ 의 기존 pair json 4개(Δkg·CI)를 재현, 절감률은 marginal/fossil/lca/transfer_sensitivity 의 출력을 재현,",
          "기준 kg 은 집에서 바로 도는 실행의 재채점이 기존 스크립트식(출발 리전·제출 시각) 기준과 일치함을 확인."]
    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    open(OUT_TXT, "w").write("\n".join(L) + "\n")
    print("\n".join(L)); print("저장:", OUT_JSON, OUT_TXT)


if __name__ == "__main__":
    main()
