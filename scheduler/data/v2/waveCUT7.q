seed1_rho0|./.venv/bin/python -m scheduler.run_v2 --name seed/1_rho0_m0.5750 --engine joint --alpha 0.5750 --rho 0 --jobs load_balancer/data/variants/jobs_seed1.csv
seed2_rho0|./.venv/bin/python -m scheduler.run_v2 --name seed/2_rho0_m0.5750 --engine joint --alpha 0.5750 --rho 0 --jobs load_balancer/data/variants/jobs_seed2.csv
seed3_rho0|./.venv/bin/python -m scheduler.run_v2 --name seed/3_rho0_m0.5750 --engine joint --alpha 0.5750 --rho 0 --jobs load_balancer/data/variants/jobs_seed3.csv
seed4_rho0|./.venv/bin/python -m scheduler.run_v2 --name seed/4_rho0_m0.5750 --engine joint --alpha 0.5750 --rho 0 --jobs load_balancer/data/variants/jobs_seed4.csv
fb_rho0_dw|./.venv/bin/python -m scheduler.match_alpha --engine start_admit_fb --axis dw --target 39.20 --lo 0.52 --hi 0.5375 --tol 0.3 --max-runs 5 --prefix startadmit/fb_rho0_dw --extra '--rho 0'
