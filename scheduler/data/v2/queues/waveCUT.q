az_fb_rho0|./.venv/bin/python -m scheduler.run_v2 --name azure/fb_rho0_m0.5375 --engine start_admit_fb --alpha 0.5375 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_cap2_rho0|./.venv/bin/python -m scheduler.run_v2 --name azure/cap_2.00x_rho0 --cap 2.00 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_knee_dw_rho0|./.venv/bin/python -m scheduler.match_alpha --axis dw --target 39.35 --lo 0.52 --hi 0.6 --prefix azure/rho0_dw --extra "--rho 0 --jobs load_balancer/data/jobs_azure.csv" --max-runs 4
