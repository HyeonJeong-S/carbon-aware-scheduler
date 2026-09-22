"""§2.1 실측 수치 재현 — 연평균 탄소집약도와 일변동비.

논문 §2.1 문단(paraId 75C94F3D)의 수치를 원자료에서 재계산한다.
일변동비는 "하루 최댓값/최솟값 비의 중앙값" 정의를 쓴다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from interface import carbon_2025


def main() -> None:
    act = carbon_2025.load_2025()["actual"]
    means = {r: float(np.mean(np.asarray(v, dtype=float))) for r, v in act.items()}
    hi_r = max(means, key=means.get)
    lo_r = min(means, key=means.get)
    print("연평균 탄소집약도 (gCO2/kWh)")
    for r, m in sorted(means.items(), key=lambda x: -x[1]):
        print(f"  {r:14s} {m:8.2f}")
    print(f"공간 격차: {means[hi_r]/means[lo_r]:.2f}배  ({hi_r} / {lo_r})")

    print("\n일변동비 (하루 max/min 의 중앙값)")
    for r, v in act.items():
        a = np.asarray(v, dtype=float)
        days = a[: len(a) // 24 * 24].reshape(-1, 24)
        ratios = days.max(axis=1) / np.maximum(days.min(axis=1), 1e-9)
        print(f"  {r:14s} {np.median(ratios):.3f}")


if __name__ == "__main__":
    main()
