"""로드밸런서 → 스케줄러 경계: 세 가지 CSV 형식이 같은 dict 로 읽히는지."""

import pytest

from interface.lb_assignment import attach_to_jobs, load_assignments


@pytest.mark.parametrize("header, row", [
    ("job_name,submit_time,origin,assigned,k,duration,latency_ms,carbon_g,dropped",
     "j_1,0,Korea,France,1,10,146,5,False"),                       # A) assign_*.csv
    ("job_name,submit_time,duration,region,k,L_max,α,배정", "j_1,0,10,Korea,1,5,0.6,France"),   # B) 초기 공유본
    ("job_name,submit_time,duration,region,k,L_max,submit_local_hour,band,alpha,assigned_region",
     "j_1,0,10,Korea,1,5,9,day,0.6,France"),                        # C) routed/jobs_routed_*.csv
])
def test_all_three_formats_normalize_to_standard_codes(tmp_path, header, row):
    p = tmp_path / "a.csv"
    p.write_text(f"{header}\n{row}\n", encoding="utf-8")
    assert load_assignments(p) == {"j_1": {"origin": "KR", "assigned": "FR"}}


def test_missing_region_columns_is_an_error(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("job_name,foo\nj_1,1\n")
    with pytest.raises(ValueError, match="리전 컬럼"):
        load_assignments(p)


def test_attach_to_jobs_keeps_unmatched_jobs():
    jobs = [{"id": "j_1", "region": "KR", "carbon_region": None},
            {"id": "j_2", "region": "JP", "carbon_region": None}]
    attach_to_jobs(jobs, {"j_1": {"origin": "KR", "assigned": "FR"}})
    assert jobs[0]["carbon_region"] == "FR" and jobs[0]["region"] == "KR"
    assert jobs[1] == {"id": "j_2", "region": "JP", "carbon_region": None}
