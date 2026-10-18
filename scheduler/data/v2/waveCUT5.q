af_sn24|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed_sn24 --engine arrival_fixed --forecast sn24
az_af_or|./.venv/bin/python -m scheduler.run_v2 --name azure/arrival_fixed_rho0_oracle --engine arrival_fixed --rho 0 --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_af_sn|./.venv/bin/python -m scheduler.run_v2 --name azure/arrival_fixed_rho0_sn24 --engine arrival_fixed --rho 0 --forecast sn24 --jobs load_balancer/data/jobs_azure.csv
az_fb_or|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_azure_rho0_oracle --engine start_admit_fb --rho 0 --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_fb_sn|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_azure_rho0_sn24 --engine start_admit_fb --rho 0 --forecast sn24 --jobs load_balancer/data/jobs_azure.csv
az_no_or|./.venv/bin/python -m scheduler.run_v2 --name nowonly/azure_oracle --engine now_only --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_no_sn|./.venv/bin/python -m scheduler.run_v2 --name nowonly/azure_sn24 --engine now_only --forecast sn24 --jobs load_balancer/data/jobs_azure.csv
az_j_or|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_oracle --engine joint --rho 0 --forecast oracle --jobs load_balancer/data/jobs_azure.csv
az_j_sn|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_sn24 --engine joint --rho 0 --forecast sn24 --jobs load_balancer/data/jobs_azure.csv
