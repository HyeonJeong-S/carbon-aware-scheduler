# -*- coding: utf-8 -*-
"""그림 9 · 시간 이동 전후 CAL 리전 동시실행수 — 41 -> 17(2026-09-24 b6 배분,
그림 10장 통합 점검에서 낡은 "19" 발견해 데이터 파일 기준으로 고침).

(2026-09-22, be 알림: §6.3에 그림7 비교 그림이 신설되며 문서 등장 순서가
1234-7-56으로 밀렸던 걸 be가 바로잡아 지금은 이 그림이 그림6, 용량
스윕(옛 gen_capacity_sweep.py)이 그림7이다 — 파일명도 맞춰 갱신함.)

데이터 출처: scheduler.simulator(mode="carbon_lb_timeshift", 무제약) 과
scheduler.capacity.run_rolling(capacity=12, 온라인) 을 2025년 1년치 job
146,000건에 대해 직접 실행해 CAL(US-CAL-CISO) 리전의 (start,end) 배정을
연속 시각 이벤트 스윕한 결과다 (§6.4 정의: tau_j<=t<tau_j+d_j).
독립 재계산 결과가 정리.txt [26]의 41건/19건, 초과시간 867h/12h 와 정확히
일치함을 확인했다 (scratchpad/run_c5.py).

레포 코드(scheduler/, capacity.py)는 실행만 했을 뿐 수정하지 않았다.
데이터는 이 스크립트 옆의 c5_cal_concurrency.json 에서 읽는다
(run_c5.py 로 재생성 가능 — 8초 내외).

실행: ./.venv/bin/python paper/diagram/gen_concurrency.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_HERE, "c5_cal_concurrency.json")

for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "Noto Sans KR"):
    if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

INK = "#000000"


def step_xy(events):
    xs, ys = [], []
    for t, v in events:
        if xs:
            xs.append(t)
            ys.append(ys[-1])
        xs.append(t)
        ys.append(v)
    return xs, ys


def main():
    with open(DATA_PATH) as f:
        d = json.load(f)

    win_lo, win_hi = d["win_lo"], d["win_hi"]
    ev_a, ev_b = d["win_events_a"], d["win_events_b"]
    cap = d["cap"]
    day0 = win_lo // 24

    xa, ya = step_xy(ev_a)
    xb, yb = step_xy(ev_b)

    # 215pt = 단내(single-column) 폭 — gen_figs.py 관례와 동일, 2.99in @300dpi.
    # 2026-09-21까지 239pt로 잘못 잡혀 있었음(수정).
    W_IN, H_IN = 215 / 72.0, 184 / 72.0
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=300)

    ax.plot(xa, ya, color=INK, lw=0.9, ls=(0, (3, 1.5)), label="무제약 (시간이동, 용량 미인지)")
    ax.plot(xb, yb, color=INK, lw=1.3, label="온라인 (용량 인지, Algorithm 1)")
    ax.axhline(cap, color=INK, lw=0.6, ls=(0, (1, 1)))
    ax.text(win_hi - win_lo, cap + 0.8, f"상한 {cap}", ha="right", va="bottom", fontsize=7,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

    # 이 구간(1주)의 국소 최대값을 그대로 표시한다 — 연중 최대(41/19)는
    # 서로 다른 주에서 나오므로 혼동을 막기 위해 아래 각주에 따로 밝힌다.
    pa = max(ya)
    ia = ya.index(pa)
    ax.annotate(f"{pa}", (xa[ia], pa), textcoords="offset points", xytext=(2, 3),
                fontsize=7.5, fontweight="bold")
    pb = max(yb)
    ib = yb.index(pb)
    ax.annotate(f"{pb}", (xb[ib], pb), textcoords="offset points", xytext=(2, -9),
                fontsize=7.5, fontweight="bold")

    ax.set_xlim(0, win_hi - win_lo)
    ax.set_ylim(0, max(ya) * 1.12)
    xt = list(range(0, win_hi - win_lo + 1, 24))
    ax.set_xticks(xt)
    ax.set_xticklabels([f"{day0 + i // 24}" for i in xt], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_xlabel("연중 일수 (day)", fontsize=8)
    ax.set_ylabel("캘리포니아 동시 실행 수", fontsize=8)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_linewidth(0.7)
    ax.grid(axis="y", color="#dddddd", lw=0.4)

    ax.legend(loc="upper right", fontsize=6.5, frameon=False, handlelength=2.2)

    # 2026-09-24 b6 배분(그림 10장 통합 점검): 둘째 줄의 "41건→17건"이 캡션과
    # 겹쳤다 — 41은 이 주의 곡선 위 숫자(pa)와도 같은 값이라 그림 자체가 이미
    # 보여준다. 다만 "(다른 주)"라는 사실은 캡션에 없어 반드시 남겨야 한다 —
    # 없으면 독자가 이 그림 안에서 17을 찾다가 못 찾는다. 그 사실만 남긴다.
    fig.text(0.02, 0.012,
              f"위 구간은 연중 한 주(day {day0}–{win_hi // 24})의 예시다.\n"
              f"온라인의 연중 최대 {d['peak_b']}건은 이 주가 아닌 다른 주에서 난다(4.3절 정의).",
              fontsize=6.2, ha="left", linespacing=1.4)

    fig.tight_layout(rect=(0, 0.10, 1, 1), pad=0.5)
    out = os.path.join(_HERE, "fig6_concurrency.png")
    fig.savefig(out)
    fig.savefig(out.replace(".png", ".pdf"))  # KCI 인쇄 대비 벡터판
    print("wrote", out)


if __name__ == "__main__":
    main()
