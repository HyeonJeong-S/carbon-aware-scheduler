from interface.regions import (
    LB_TO_REGION,
    REGION_LABELS,
    REGION_TO_ISO3,
    REGION_TO_LB,
    REGIONS,
    label,
    to_iso3,
    to_region,
)


def test_eight_regions_in_fixed_order():
    assert REGIONS == ["US-CAL-CISO", "US-TEX-ERCO", "US-NY-NYIS", "FR", "DE", "KR", "IN", "JP"]


def test_mappings_are_bijective():
    assert {to_region(lb) for lb in LB_TO_REGION} == set(REGIONS)
    assert {REGION_TO_LB[r] for r in REGIONS} == set(LB_TO_REGION)
    assert set(REGION_LABELS) == set(REGIONS) == set(REGION_TO_ISO3)


def test_to_region_accepts_every_notation():
    assert to_region("Korea") == "KR"          # 로드밸런서 표기
    assert to_region("KR") == "KR"             # 이미 표준
    assert to_region("IN-NO") == "IN"          # 과거 스케줄러 코드
    assert to_region("US-MIDA-PJM") == "US-NY-NYIS"
    assert to_region("US_West") == "US-CAL-CISO"


def test_unknown_region_passes_through():
    assert to_region("Mars") == "Mars"


def test_iso3_merges_us_regions():
    assert {to_iso3(r) for r in ("US-CAL-CISO", "US-TEX-ERCO", "US-NY-NYIS")} == {"USA"}
    assert to_iso3("Korea") == "KOR"


def test_label_is_human_readable():
    assert label("US-NY-NYIS") == "US East (New York)"
    assert label("Japan") == "Japan"
