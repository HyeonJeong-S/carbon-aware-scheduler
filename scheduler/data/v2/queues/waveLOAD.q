az_c050_cast|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.50_rho0_knee --cap 0.50 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_c060_cast|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.60_rho0_knee --cap 0.60 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_c050_af|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.50_rho0_af_knee --engine arrival_fixed --cap 0.50 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_c060_af|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.60_rho0_af_knee --engine arrival_fixed --cap 0.60 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_c050_cast_m|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.50_rho0_m0.5375 --alpha 0.5375 --cap 0.50 --rho 0 --jobs load_balancer/data/jobs_azure.csv
az_c060_cast_m|./.venv/bin/python -m scheduler.run_v2 --name load/azure_cap0.60_rho0_m0.5375 --alpha 0.5375 --cap 0.60 --rho 0 --jobs load_balancer/data/jobs_azure.csv
