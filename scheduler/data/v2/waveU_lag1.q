lag1_knee|./.venv/bin/python -m scheduler.run_v2 --name lag1/joint --carbon-now lag1
lag1_a1|./.venv/bin/python -m scheduler.run_v2 --name lag1/joint_a1 --alpha 1.0 --carbon-now lag1
lag1_sn24|./.venv/bin/python -m scheduler.run_v2 --name lag1/joint_sn24 --forecast sn24 --carbon-now lag1
lag1_time|./.venv/bin/python -m scheduler.run_v2 --name lag1/time_only --engine joint --home-region --carbon-now lag1
lag1_azure|./.venv/bin/python -m scheduler.run_v2 --name lag1/azure --jobs load_balancer/data/jobs_azure.csv --carbon-now lag1
