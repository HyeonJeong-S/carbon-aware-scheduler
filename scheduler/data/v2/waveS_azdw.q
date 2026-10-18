azs1_dw|./.venv/bin/python -m scheduler.match_alpha --axis dw --target 42.87 --lo 0.55 --hi 0.62 --prefix azure/seed1_m --extra "--jobs load_balancer/data/variants/jobs_azure_seed1.csv" --max-runs 4
azs2_dw|./.venv/bin/python -m scheduler.match_alpha --axis dw --target 38.45 --lo 0.55 --hi 0.6 --prefix azure/seed2_m --extra "--jobs load_balancer/data/variants/jobs_azure_seed2.csv" --max-runs 4
