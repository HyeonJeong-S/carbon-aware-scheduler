sar_lstm|./.venv/bin/python -m scheduler.run_v2 --name startadmit/replan_lstm --engine start_admit_replan
sar_oracle|./.venv/bin/python -m scheduler.run_v2 --name startadmit/replan_oracle --engine start_admit_replan --forecast oracle
sar_mix05|./.venv/bin/python -m scheduler.run_v2 --name startadmit/replan_mix0.5 --engine start_admit_replan --forecast mix0.5
sar_az|./.venv/bin/python -m scheduler.run_v2 --name startadmit/replan_azure --engine start_admit_replan --jobs load_balancer/data/jobs_azure.csv
mb01_az|./.venv/bin/python -m scheduler.run_v2 --name azure/mb0.1 --mb-scale 0.1 --jobs load_balancer/data/jobs_azure.csv
mb10_az|./.venv/bin/python -m scheduler.run_v2 --name azure/mb10 --mb-scale 10 --jobs load_balancer/data/jobs_azure.csv
degen17|./.venv/bin/python -m scheduler.run_v2 --name grid/degen_check_30d_cap17 --days 30 --cap-mode abs --cap 17
