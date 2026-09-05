"""로드밸런서 탭들이 공유하는 상수 — 리전 순서·색·UTC 오프셋."""

from interface.dashboard import data, theme

R = data.LB_REGIONS                                            # LB 표기 순서 (그래프 축에 그대로 사용)
RC = {lb: theme.REGION_COLORS[data.to_std(lb)] for lb in R}    # LB 표기 → 리전 색
UTC_OFFSET = data.lb_config.UTC_OFFSET
