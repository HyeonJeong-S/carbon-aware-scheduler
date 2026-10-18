a1_h6|./.venv/bin/python -m scheduler.run_v2 --name horizon/6_a1 --engine joint --alpha 1.0 --horizon 6
a1_phi20|./.venv/bin/python -m scheduler.run_v2 --name phi/20_joint_a1 --engine joint --alpha 1.0 --jobs load_balancer/data/variants/jobs_phi20.csv
a1_phi30|./.venv/bin/python -m scheduler.run_v2 --name phi/30_joint_a1 --engine joint --alpha 1.0 --jobs load_balancer/data/variants/jobs_phi30.csv
a1_noon|./.venv/bin/python -m scheduler.run_v2 --name arrive/defer_noon_a1 --engine joint --alpha 1.0 --jobs load_balancer/data/variants/jobs_defer_noon.csv
a1_own|./.venv/bin/python -m scheduler.run_v2 --name hetero/own_1.25x_a1 --engine joint --alpha 1.0 --cap 1.25 --cap-mode x-own-peak
a1_large|./.venv/bin/python -m scheduler.run_v2 --name hetero/clean_large_a1 --engine joint --alpha 1.0 --cap-json scheduler/data/v2/scenarios.json:synthetic.cap_clean_large
a1_h12|./.venv/bin/python -m scheduler.run_v2 --name horizon/12_a1 --engine joint --alpha 1.0 --horizon 12
a1_phi50|./.venv/bin/python -m scheduler.run_v2 --name phi/50_joint_a1 --engine joint --alpha 1.0 --jobs load_balancer/data/variants/jobs_phi50.csv
a1_phi60|./.venv/bin/python -m scheduler.run_v2 --name phi/60_joint_a1 --engine joint --alpha 1.0 --jobs load_balancer/data/variants/jobs_phi60.csv
a1_small|./.venv/bin/python -m scheduler.run_v2 --name hetero/clean_small_a1 --engine joint --alpha 1.0 --cap-json scheduler/data/v2/scenarios.json:synthetic.cap_clean_small
