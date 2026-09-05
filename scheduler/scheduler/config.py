"""상수 정의: L_max 테이블, 리전 목록, 시뮬레이션 기본 파라미터.

리전 관련 정의는 저장소 루트의 interface/ 패키지가 단일 출처(single source)다.
여기서는 그것을 그대로 가져다 쓰고, 스케줄러 고유의 상수만 직접 정의한다.
"""

import os
import sys

# 저장소 루트를 import 경로에 추가 (interface 패키지 사용을 위해)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from interface.regions import (  # noqa: E402
    REGIONS,
    REGION_LABELS as ZONE_LABELS,
    REGION_TO_ISO3 as ZONE_TO_ISO3,
    LB_TO_REGION as LB_TO_ZONE,
    to_region,
)

# k(중요도)별 대표 지연 예산(L_max)은 코드 상수가 아니라 job 데이터에 들어 있다
# (jobs.csv의 L_max 열 — k별 범위 내 job마다 랜덤). 범위 정의는
# scheduler/data/job/README_jobs.md 참고.

SLOT_HOURS = 1
FORECAST_HORIZON = 24  # LSTM 예측 범위 (시간)

MODES = {
    "simple_lb_immediate": "비교군1: 단순 LB + 즉시 실행",
    "carbon_lb_immediate": "비교군2: 탄소 LB + 즉시 실행",
    "carbon_lb_timeshift": "비교군3(ours): 탄소 LB + time shift",
}

__all__ = [
    "REGIONS", "ZONE_LABELS", "ZONE_TO_ISO3", "LB_TO_ZONE", "to_region",
    "SLOT_HOURS", "FORECAST_HORIZON", "MODES",
]
