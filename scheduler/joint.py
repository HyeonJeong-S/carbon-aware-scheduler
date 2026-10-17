"""결합 롤링 스케줄러 — v2 의 CAST.  (2026-10-16 코드·설계·통계 감사 반영판)

매 슬롯 t 마다 아직 시작하지 않은 작업 전부에 대해 (리전 r, 시작 오프셋 i) 를 한 문제로 푼다.
용량은 입장 때 거르는 조건이 아니라 모든 작업이 함께 보는 제약이다.

문제 (슬롯 t):
    min  Σ_j Σ_{r,i} d_j [ α·C̃(r,t,i) + (1−α)·ℓ̃(o_j,r) ] x_{j,r,i}
         + M_A Σ z^A + M_B Σ z^B + ε Σ i·x
    s.t. Σ_{r,i} x_{j,r,i} = 1                                            ∀j
         [지금]   Σ_{(j,r,0) 가 순간 u 를 덮음} x + n_r(u)  ≤ cap_r + z^A_{r,u}
                  u ∈ {t} ∪ {s_j : 이번 슬롯 도착}  — 시작 순간마다 한 행 (연속 시각 정의와 같음)
         [미래]   Σ_{(j,r,i) 가 슬롯 τ 를 덮음} x + n_r(τ) ≤ cap_r + z^A_{r,τ}         τ ∈ [t+1, t+H]
         [예약]   Σ_{미룰 수 있는 (j,r,i) 가 τ 를 덮음} x + n_r(τ) ≤ cap_r − ρ_r + z^B_{r,τ}   τ ∈ [t+1, t+H]
         0 ≤ x ≤ 1,  z ≥ 0
  n_r(·) : 이미 시작해 그 순간/슬롯에 돌고 있는 작업 수 (장부)
  예약 ρ_r 의 뜻: 슬롯 τ 가 시작될 때 **이전에 시작해 아직 도는 작업(carry-over)** 이 cap_r − ρ_r 을
  넘지 않게 하여, τ 에 도착하는 작업에 ρ_r 자리가 남게 한다. (현재 슬롯 도착은 슬롯 머리에서 다 알므로
  τ = t 에는 예약이 필요 없다.)
  미래 슬롯 행은 슬롯 단위 덮음(보수적 근사)이고 매 슬롯 다시 풀며, 지금 슬롯 행만 순간 단위로 정확하다.
  M_B > max_j d_j, M_A = 100·M_B  — 비용이 작업당 d_j 로 유계라 사전식 순서(물리 → 예약 → 탄소·지연)가 보장.

  α : 슬롯마다 파레토 무릎점. 후보 α 마다 LP 를 풀어 (d 가중 평균 지연, 예측 배출) 을 얻고 둘을
      후보 사이에서 0~1 로 정규화해 원점 거리 최소. 축이 퇴화하면(지연 전부 0) α = 1.
  mode : "joint"     리전·시작 슬롯 모두 매 슬롯 다시 결정 (새 CAST)
         "decoupled" 도착 슬롯의 LP 가 고른 리전을 고정, 시작 슬롯만 롤링 (설계 감사: 결합의 몫을 가르는 대조)
         "greedy"    LP 없이 LLF 순서로 각 작업이 최선 (r,i) 를 잡음 (탐욕 대조)

  i = 0 인 작업만 확정. 마감: (D_j − d_j) − t < 1 이면 i = 0 만 → 구성상 마감 위반 0.
  미룰 수 없는 작업(⌊D_j − d_j⌋ ≤ ⌊s_j⌋): i = 0 만, 리전은 자유.
  슬롯 t 의 도착(⌊s_j⌋ = t)은 슬롯 머리에서 모두 안다(최대 1시간 선견) — 모든 엔진에 같다.

회계 capacity._Windows.actual_mean, 위반 정의 capacity._over_cap_admissions 와 같은 규약(리전별 상한).
"""
import math
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

from . import capacity

HORIZON = capacity.HORIZON            # 24
ALPHA_GRID = tuple(round(0.1 * k, 1) for k in range(11))
L_NET_MAX_MS = 244.0                  # load_balancer.framework.config.L_NET_MAX_MS
EPS_EARLY = 1e-4


def covered_slots(start, d):
    a = math.floor(start)
    b = max(a + 1, math.ceil(start + d))
    return range(a, b)


def _as_region_dict(v, regions, default=None):
    if isinstance(v, dict):
        return {r: v.get(r, default) for r in regions}
    return dict.fromkeys(regions, v)


def over_cap_flags(out, regions, cap_d):
    """작업별 위반 플래그 — capacity._over_cap_admissions 와 같은 정의(리전별 상한), 작업 id 를 돌려준다.
    j 가 시작할 때 같은 리전에서 돌고 있는 다른 작업이 cap_r 이상이면 위반. 동시각 시작은 서로를 본다.
    동시각이면 종료를 먼저 처리(반개구간)."""
    flags = {}
    for r in regions:
        cap = cap_d[r]
        items = [v for v in out.values() if v["region"] == r]
        ev = []
        for idx, v in enumerate(items):
            ev.append((v["scheduled_start"], 0, idx))
            ev.append((v["scheduled_start"] + v["duration"], 1, idx))
        ev.sort(key=lambda x: (x[0], -x[1]))
        cur, i, n = 0, 0, len(ev)
        while i < n:
            t = ev[i][0]
            j2 = i
            while j2 < n and ev[j2][0] == t and ev[j2][1] == 1:
                cur -= 1; j2 += 1
            before = cur
            k2 = j2
            while k2 < n and ev[k2][0] == t and ev[k2][1] == 0:
                cur += 1; k2 += 1
            batch = k2 - j2
            if before + (batch - 1) >= cap:
                for _, _, idx in ev[j2:k2]:
                    v = items[idx]
                    flags[v["job_id"]] = "forced" if v["forced"] else ("immediate" if v["immediate"] else "normal")
            i = k2
    return flags


def peak_ends_first(out, regions):
    peaks = {}
    for r in regions:
        ev = []
        for v in out.values():
            if v["region"] != r:
                continue
            ev.append((v["scheduled_start"], 1))
            ev.append((v["scheduled_start"] + v["duration"], -1))
        ev.sort(key=lambda x: (x[0], x[1]))
        cur = mx = 0
        for _, d in ev:
            cur += d
            mx = max(mx, cur)
        peaks[r] = mx
    return peaks


def hours_over(out, regions, cap_d):
    res = {}
    for r in regions:
        led = capacity.CapacityLedger([r], cap_d[r])
        for v in out.values():
            if v["region"] == r:
                led.reserve(r, v["scheduled_start"], v["duration"])
        res[r] = led.hours_over(r)
    return res


def summarize(out, regions, cap_d, score_from=0.0, alpha_log=None, extra=None):
    """out 전체(t=0 부터 시뮬레이션)에서 submit ≥ score_from 인 작업만 채점. 동시 실행은 전체 스케줄로 센다."""
    flags = over_cap_flags(out, regions, cap_d)
    win = {k: v for k, v in out.items() if v["submit_time"] >= score_from}
    for k, v in out.items():
        v["over_cap"] = flags.get(k, "")
    def cnt(cat):
        return sum(1 for k in win if flags.get(k) == cat)
    delays = np.array([v["delay"] for v in win.values()]) if win else np.zeros(1)
    lats = np.array([v["latency_ms"] for v in win.values()]) if win else np.zeros(1)
    durs = np.array([v["duration"] for v in win.values()]) if win else np.ones(1)
    by_k = {}
    for k in sorted({v["k"] for v in win.values()}):
        sub = [v for v in win.values() if v["k"] == k]
        by_k[k] = dict(n=len(sub), carbon_kg=sum(v["carbon_emitted"] for v in sub) / 1000,
                       avg_delay_h=float(np.mean([v["delay"] for v in sub])),
                       p95_delay_h=float(np.percentile([v["delay"] for v in sub], 95)),
                       avg_latency_ms=float(np.mean([v["latency_ms"] for v in sub])),
                       forced=sum(1 for v in sub if v["forced"]),
                       over_cap=sum(1 for v in sub if flags.get(v["job_id"])))
    st = dict(
        n=len(win), n_all=len(out),
        total_carbon_kg=sum(v["carbon_emitted"] for v in win.values()) / 1000.0,
        slo_violations=int(sum(1 for v in win.values() if not v["slo_satisfied"])),
        forced_admissions=int(sum(1 for v in win.values() if v["forced"])),
        immediate=int(sum(1 for v in win.values() if v["immediate"])),
        capacity_violations=cnt("forced") + cnt("immediate") + cnt("normal"),
        over_cap_forced=cnt("forced"), over_cap_immediate=cnt("immediate"), over_cap_normal=cnt("normal"),
        scored_cap=cap_d, peak_by_region=peak_ends_first(win, regions),
        hours_over_by_region=hours_over(out, regions, cap_d),
        avg_delay_h=float(delays.mean()), p95_delay_h=float(np.percentile(delays, 95)),
        avg_latency_ms=float(lats.mean()), p95_latency_ms=float(np.percentile(lats, 95)),
        dw_latency_ms=float((lats * durs).sum() / durs.sum()),
        home_share=float(np.mean([v["region"] == v["origin"] for v in win.values()])) if win else 0.0,
        by_k=by_k,
    )
    if alpha_log is not None:
        al = [a for (t, a, _) in alpha_log if t >= score_from]
        st["alpha_mean"] = float(np.mean(al)) if al else None
        st["alpha_log"] = alpha_log
    if extra:
        st.update(extra)
    return st


def run_joint(jobs, actual, pred24, cap, regions, latency_ms, *,
              rho=0, horizon=HORIZON, alpha="knee", alpha_grid=ALPHA_GRID,
              n_hours=None, l_net_max=None, home_region=False, spatial_only=False,
              t_start=None, score_from=0.0, mode="joint", penalties=None, record_alpha=True, record_slots=None):
    """반환 (out, stats). cap/rho 는 int 또는 {리전: int}."""
    assert mode in ("joint", "decoupled", "greedy")
    W = capacity._Windows(actual, pred24)
    cap_d = _as_region_dict(cap, regions)
    rho_d = _as_region_dict(rho, regions, 0)
    led = {r: capacity.CapacityLedger([r], cap_d[r]) for r in regions}
    ridx = {r: k for k, r in enumerate(regions)}

    if n_hours is None:
        n_hours = int(max(j["deadline"] for j in jobs)) + 2
    T_END = n_hours + horizon + 10
    occ = {r: np.zeros(T_END + 2, dtype=np.int32) for r in regions}
    max_d = max(j["duration"] for j in jobs)
    if penalties is None:
        M_B = max(10.0, 2.0 * max_d)
        M_A = 100.0 * M_B
    else:
        M_A, M_B = penalties

    arrivals = {}
    for j in jobs:
        arrivals.setdefault(math.floor(j["submit_time"]), []).append(j)
    t0 = min(arrivals) if t_start is None else t_start
    assert all(k >= t0 for k in arrivals), "t_start 이전 도착이 있다 — 그 작업은 영원히 배정되지 않는다"

    Q = []
    fixed_region = {}
    out = {}
    forced = immediate = 0
    solve_t, n_mip, n_lp = [], 0, 0
    zA_pos_slots = zB_pos_slots = 0; zA_sum = zB_sum = 0.0
    alpha_log = []
    max_vars = 0
    slot_records = {}          # record_slots 에 든 슬롯의 α 후보별 (지연, 배출, 배정) — 그림 4·표 1 용

    def emit(j, r, start, forced_flag, immediate_flag, a_used):
        d = j["duration"]
        led[r].reserve(r, start, d)
        for tau in covered_slots(start, d):
            if tau < T_END:
                occ[r][tau] += 1
        rate = W.actual_mean(r, start, d)
        out[j["id"]] = dict(
            job_id=j["id"], k=j["k"], region=r, origin=j["region"],
            submit_time=j["submit_time"], duration=d,
            scheduled_start=start, delay=start - j["submit_time"],
            carbon_emitted=rate * d, latency_ms=latency_ms[j["region"]][r],
            slo_satisfied=(start + d) <= j["deadline"] + 1e-9,
            forced=forced_flag, immediate=immediate_flag, alpha=a_used,
        )

    for t in range(t0, n_hours + 2):
        N = []
        for j in arrivals.pop(t, ()):
            if math.floor(j["deadline"] - j["duration"]) <= math.floor(j["submit_time"]):
                N.append(j)
            else:
                Q.append(j)
        if not Q and not N:
            if not arrivals:
                break
            continue

        cmax = 0.0
        for r in regions:
            row = W.prd[r][min(t, W.prd_n[r] - 1)]
            cmax = max(cmax, float(np.max(np.diff(row))))
        cmax = cmax if cmax > 0 else 1.0

        plan = Q + N
        nQ = len(Q)
        # ── 변수 ──
        var_j, var_r, var_i, var_start, var_def = [], [], [], [], []
        c_carb, c_lat, lat_raw, carb_raw, dur_v = [], [], [], [], []
        row_eq = []
        for jj, j in enumerate(plan):
            d = j["duration"]; o = j["region"]
            is_def = jj < nQ
            late = j["deadline"] - d
            if (not is_def) or spatial_only or (late - t) < 1:
                hi = 0
            else:
                hi = max(int(min(late, t + horizon) - t), 0)
            if home_region:
                cand_r = [o]
            elif mode == "decoupled" and j["id"] in fixed_region:
                cand_r = [fixed_region[j["id"]]]
            elif l_net_max is None:
                cand_r = regions
            else:
                cand_r = [r for r in regions if r == o or latency_ms[o][r] <= l_net_max]
            for r in cand_r:
                lt = latency_ms[o][r] / L_NET_MAX_MS
                for i in range(hi + 1):
                    start = max(t, j["submit_time"]) if i == 0 else t + i
                    ch = W.pred_mean(r, t, i, d)
                    var_j.append(jj); var_r.append(r); var_i.append(i)
                    var_start.append(start); var_def.append(is_def)
                    c_carb.append(d * ch / cmax); c_lat.append(d * lt)
                    lat_raw.append(latency_ms[o][r]); carb_raw.append(ch * d); dur_v.append(d)
                    row_eq.append(jj)
        nx = len(var_j)
        max_vars = max(max_vars, nx)
        c_carb = np.asarray(c_carb); c_lat = np.asarray(c_lat)
        var_i_arr = np.asarray(var_i, dtype=float)
        lat_raw = np.asarray(lat_raw); carb_raw = np.asarray(carb_raw); dur_v = np.asarray(dur_v)

        # ── 제약 행 ──
        # 지금 슬롯: 시작 순간 단위 (정확). 순간 = t 와 이번 슬롯 도착들의 s_j.
        instants = sorted({float(t)} | {j["submit_time"] for j in N if j["submit_time"] > t}
                          | {j["submit_time"] for j in Q if t <= j["submit_time"] < t + 1})
        run_now = {r: {u: led[r].running(r, u) for u in instants} for r in regions}   # 오름차순 조회
        rowsA, colsA, valsA, bA = [], [], [], []
        rowsB, colsB, valsB, bB = [], [], [], []
        keyA, keyB = {}, {}
        tau_lim = t + horizon
        for v in range(nx):
            r, st, d, is_def = var_r[v], var_start[v], dur_v[v], var_def[v]
            if var_i[v] == 0:
                for u in instants:
                    if st <= u < st + d:
                        ka = keyA.setdefault((r, "u", u), len(keyA))
                        rowsA.append(ka); colsA.append(v); valsA.append(1.0)
            for tau in covered_slots(st, d):
                if tau <= t:
                    continue
                if tau > tau_lim:
                    break
                ka = keyA.setdefault((r, "s", tau), len(keyA))
                rowsA.append(ka); colsA.append(v); valsA.append(1.0)
                if is_def:
                    kb = keyB.setdefault((r, tau), len(keyB))
                    rowsB.append(kb); colsB.append(v); valsB.append(1.0)
        nA, nB = len(keyA), len(keyB)
        for (r, kind, key), k in keyA.items():
            base = run_now[r][key] if kind == "u" else int(occ[r][key])
            bA.append(cap_d[r] - base)
        for (r, tau), k in keyB.items():
            bB.append(cap_d[r] - rho_d[r] - int(occ[r][tau]))
        n_all = nx + nA + nB
        for k in range(nA):
            rowsA.append(k); colsA.append(nx + k); valsA.append(-1.0)
        for k in range(nB):
            rowsB.append(k); colsB.append(nx + nA + k); valsB.append(-1.0)
        A_ub = coo_matrix((valsA + valsB, (rowsA + [nA + rr for rr in rowsB], colsA + colsB)),
                          shape=(nA + nB, n_all)).tocsr()
        b_ub = np.asarray(bA + bB, dtype=float)
        A_eq = coo_matrix((np.ones(nx), (row_eq, np.arange(nx))), shape=(len(plan), n_all)).tocsr()
        b_eq = np.ones(len(plan))
        lb = np.zeros(n_all)
        ub = np.concatenate([np.ones(nx), np.full(nA + nB, np.inf)])
        pen = np.concatenate([np.zeros(nx), np.full(nA, M_A), np.full(nB, M_B)])

        def cost_for(a):
            return np.concatenate([a * c_carb + (1 - a) * c_lat + EPS_EARLY * var_i_arr, np.zeros(nA + nB)]) + pen

        def plan_metrics(x):
            oa = float(x[nx:nx + nA].sum())
            xs = x[:nx]
            dw_lat = float((xs * lat_raw * dur_v).sum() / max((xs * dur_v).sum(), 1e-12))
            em = float((xs * carb_raw).sum())
            return oa, dw_lat, em

        def solve_lp(a):
            res = linprog(cost_for(a), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                          bounds=list(zip(lb, ub)), method="highs")
            if res.status != 0:
                raise RuntimeError(f"slot {t} LP status {res.status}: {res.message}")
            return res.x

        def solve_greedy(a):
            """LLF 순서로 각 작업이 최선 (r,i). 임시 점유로 용량을 보되 자리가 없으면 벌점 최소 후보."""
            c = cost_for(a)[:nx]
            x = np.zeros(n_all)
            slackA = np.asarray(bA, dtype=float).copy(); slackB = np.asarray(bB, dtype=float).copy()
            A_csc = A_ub.tocsc()
            order = sorted(range(len(plan)), key=lambda jj: (jj < nQ, (plan[jj]["deadline"] - plan[jj]["duration"]) - t))
            vars_of = {}
            for v in range(nx):
                vars_of.setdefault(var_j[v], []).append(v)
            for jj in order:
                best, best_v = None, None
                for v in vars_of[jj]:
                    col = A_csc.getcol(v)
                    rows_v = col.indices
                    overA = sum(max(0.0, 1.0 - slackA[rr]) for rr in rows_v if rr < nA)
                    overB = sum(max(0.0, 1.0 - slackB[rr - nA]) for rr in rows_v if rr >= nA)
                    val = c[v] + M_A * overA + M_B * overB
                    if best is None or val < best - 1e-12:
                        best, best_v = val, v
                x[best_v] = 1.0
                for rr in A_csc.getcol(best_v).indices:
                    if rr < nA:
                        slackA[rr] -= 1.0
                    else:
                        slackB[rr - nA] -= 1.0
            x[nx:nx + nA] = np.maximum(-slackA, 0.0); x[nx + nA:] = np.maximum(-slackB, 0.0)
            return x

        solver = solve_greedy if mode == "greedy" else solve_lp
        tic = time.perf_counter()
        if alpha == "knee":
            cands = []
            for a in alpha_grid:
                xs = solver(a); n_lp += 1
                oa, dwl, em = plan_metrics(xs)
                cands.append((a, oa, dwl, em, xs))
            if record_slots and t in record_slots:
                slot_records[t] = [dict(alpha=c[0], overflow=c[1], dw_lat=c[2], pred_em=c[3],
                                        assign={plan[var_j[v]]["id"]: (var_r[v], var_i[v]) for v in np.nonzero(c[4][:nx] > 0.5)[0]})
                                   for c in cands]
            min_oa = min(c[1] for c in cands)
            pool = [c for c in cands if c[1] <= min_oa + 1e-6]
            lats_ = np.array([c[2] for c in pool]); ems_ = np.array([c[3] for c in pool])
            if lats_.max() - lats_.min() < 1e-9 or ems_.max() - ems_.min() < 1e-9:
                a_used, xs = 1.0, next(c[4] for c in pool if c[0] == 1.0) if any(c[0] == 1.0 for c in pool) else pool[-1][4]
            else:
                ln = (lats_ - lats_.min()) / (lats_.max() - lats_.min())
                en = (ems_ - ems_.min()) / (ems_.max() - ems_.min())
                dist = np.hypot(ln, en)
                best = int(np.argmin(dist + 1e-12 * np.array([c[0] for c in pool])))
                a_used, xs = pool[best][0], pool[best][4]
        else:
            # α 경로(dict t→α): 다른 실행이 슬롯마다 고른 α 를 그대로 쓴다 — 예측기 효과와 무릎점 선택을 떼어 보는 실험(92 제안 10-16)
            a_used = float(alpha[t]) if isinstance(alpha, dict) else float(alpha)
            xs = solver(a_used); n_lp += 1

        x = xs[:nx]
        if mode != "greedy" and np.any((x > 1e-6) & (x < 1 - 1e-6)):
            integrality = np.concatenate([np.ones(nx), np.zeros(nA + nB)])
            cons = [LinearConstraint(A_ub, -np.inf, b_ub), LinearConstraint(A_eq, b_eq, b_eq)]
            res = milp(cost_for(a_used), constraints=cons, integrality=integrality, bounds=Bounds(lb, ub))
            if res.status != 0 or res.x is None:
                raise RuntimeError(f"slot {t} MILP status {res.status}: {res.message}")
            xs = res.x; x = xs[:nx]; n_mip += 1
        solve_t.append(time.perf_counter() - tic)
        # 10-17(모의 심사 [16]): 초과 변수가 양수였던 슬롯 수와 합 — z^A(물리 초과)·z^B(예약 침범)
        _za = float(xs[nx:nx + nA].sum()); _zb = float(xs[nx + nA:nx + nA + nB].sum())
        zA_pos_slots += int(_za > 1e-6); zB_pos_slots += int(_zb > 1e-6); zA_sum += _za; zB_sum += _zb
        if record_alpha:
            alpha_log.append((t, a_used, len(plan)))

        # ── 확정 (i=0) · 분리형은 리전 고정 ──
        started = set()
        for v in np.nonzero(x > 0.5)[0]:
            jj = var_j[v]; j = plan[jj]
            if mode == "decoupled" and jj < nQ and j["id"] not in fixed_region:
                fixed_region[j["id"]] = var_r[v]
            if var_i[v] != 0:
                continue
            is_def = jj < nQ
            start = var_start[v]
            if is_def:
                is_forced = (j["deadline"] - j["duration"] - t) < 1
                emit(j, var_r[v], start, is_forced, False, a_used)
                forced += int(is_forced)
            else:
                emit(j, var_r[v], start, False, True, a_used)
                immediate += 1
            started.add(jj)
        assert all(jj in started for jj in range(nQ, len(plan))), "미룰 수 없는 작업이 확정되지 않음"
        Q = [j for jj, j in enumerate(Q) if jj not in started]

    stats = summarize(out, regions, cap_d, score_from=score_from, alpha_log=alpha_log, extra=dict(
        unplaced=len(Q), solve_ms_mean=1000 * float(np.mean(solve_t)) if solve_t else 0.0,
        solve_ms_p95=1000 * float(np.percentile(solve_t, 95)) if solve_t else 0.0,
        solve_ms_max=1000 * float(np.max(solve_t)) if solve_t else 0.0,
        n_slots=len(solve_t), n_lp=n_lp, n_mip=n_mip, max_vars=max_vars,
        zA_pos_slots=zA_pos_slots, zB_pos_slots=zB_pos_slots, zA_sum=zA_sum, zB_sum=zB_sum,
        penalties=dict(M_A=M_A, M_B=M_B), mode=mode))
    if slot_records:
        stats["slot_records"] = slot_records
    return out, stats


def sn24_pred24(actual, horizon=HORIZON):
    from . import forecasters
    return forecasters.sn24(actual, horizon)


def latency_dict(regions_std):
    from interface.regions import to_region
    from load_balancer.framework import config as C
    M = C.load_latency_matrix()
    lb = [to_region(r) for r in C.REGIONS]
    return {o: {d: float(M[lb.index(o)][lb.index(d)]) for d in regions_std} for o in regions_std}
