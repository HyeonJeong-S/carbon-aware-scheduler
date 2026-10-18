safb_lstm|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_lstm --engine start_admit_fb
safb_mix075|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_mix0.75 --engine start_admit_fb --forecast mix0.75
safb_mix05|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_mix0.5 --engine start_admit_fb --forecast mix0.5
safb_mix025|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_mix0.25 --engine start_admit_fb --forecast mix0.25
safb_oracle|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_oracle --engine start_admit_fb --forecast oracle
safb_sn24|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_sn24 --engine start_admit_fb --forecast sn24
safb_az|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_azure --engine start_admit_fb --jobs load_balancer/data/jobs_azure.csv
safb_az_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/fb_azure_oracle --engine start_admit_fb --forecast oracle --jobs load_balancer/data/jobs_azure.csv
