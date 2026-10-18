az_sc_rho0|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure_rho0 --engine start_check --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_sc_rho0_or|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure_oracle_rho0 --engine start_check --rho 0 --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_sa_rho0|./.venv/bin/python -m scheduler.run_v2 --name startadmit/azure_rho0 --engine start_admit --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_sa_rho0_or|./.venv/bin/python -m scheduler.run_v2 --name startadmit/azure_oracle_rho0 --engine start_admit --rho 0 --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_fb_rho0_knee|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_azure_rho0 --engine start_admit_fb --rho 0 --jobs load_balancer/data/jobs_azure.csv
