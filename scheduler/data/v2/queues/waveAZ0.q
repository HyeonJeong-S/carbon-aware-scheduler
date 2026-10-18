az0_dec|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_decoupled --engine decoupled --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_dec_a1|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_decoupled_a1 --engine decoupled --alpha 1.0 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_greedy|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_greedy --engine greedy --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_spatial|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_spatial_only --spatial-only --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_time|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_time_only --home-region --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_cap100|./.venv/bin/python -m scheduler.run_v2 --name azure/cap_1.00x_rho0 --cap 1.00 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_cap150|./.venv/bin/python -m scheduler.run_v2 --name azure/cap_1.50x_rho0 --cap 1.50 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_s1_joint|./.venv/bin/python -m scheduler.run_v2 --name azure/seed1_rho0_joint --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed1.csv
az0_s1_a1|./.venv/bin/python -m scheduler.run_v2 --name azure/seed1_rho0_joint_a1 --alpha 1.0 --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed1.csv
az0_s1_af|./.venv/bin/python -m scheduler.run_v2 --name azure/seed1_rho0_arrival_fixed --engine arrival_fixed --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed1.csv
az0_s1_dec|./.venv/bin/python -m scheduler.run_v2 --name azure/seed1_rho0_decoupled --engine decoupled --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed1.csv
az0_s2_joint|./.venv/bin/python -m scheduler.run_v2 --name azure/seed2_rho0_joint --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed2.csv
az0_s2_a1|./.venv/bin/python -m scheduler.run_v2 --name azure/seed2_rho0_joint_a1 --alpha 1.0 --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed2.csv
az0_s2_af|./.venv/bin/python -m scheduler.run_v2 --name azure/seed2_rho0_arrival_fixed --engine arrival_fixed --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed2.csv
az0_s2_dec|./.venv/bin/python -m scheduler.run_v2 --name azure/seed2_rho0_decoupled --engine decoupled --rho 0 --jobs load_balancer/data/variants/jobs_azure_seed2.csv
az0_a0.0|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.0 --alpha 0.0 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.25|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.25 --alpha 0.25 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.4|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.4 --alpha 0.4 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.5|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.5 --alpha 0.5 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.6|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.6 --alpha 0.6 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.7|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.7 --alpha 0.7 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.8|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.8 --alpha 0.8 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az0_a0.9|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_alpha_0.9 --alpha 0.9 --rho 0 --jobs load_balancer/data/jobs_azure.csv
