af_knee|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed --engine arrival_fixed --alpha knee
af_oracle_knee|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed_oracle --engine arrival_fixed --alpha knee --forecast oracle
af_a1|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed_a1 --engine arrival_fixed --alpha 1.0
af_azure|./.venv/bin/python -m scheduler.run_v2 --name azure/arrival_fixed --engine arrival_fixed --alpha knee --jobs load_balancer/data/jobs_azure.csv
af_azure_a1|./.venv/bin/python -m scheduler.run_v2 --name azure/arrival_fixed_a1 --engine arrival_fixed --alpha 1.0 --jobs load_balancer/data/jobs_azure.csv
afm_main|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 41.01 --prefix arrival/fixed_m
afm_oracle|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 39.40 --prefix arrival/oracle_af_m --extra "--forecast oracle"
afm_s1|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 48.07 --prefix seed/1_af_m --extra "--jobs load_balancer/data/variants/jobs_seed1.csv"
afm_s2|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 48.06 --prefix seed/2_af_m --extra "--jobs load_balancer/data/variants/jobs_seed2.csv"
afm_s3|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 47.76 --prefix seed/3_af_m --extra "--jobs load_balancer/data/variants/jobs_seed3.csv"
afm_s4|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --lo 0.45 --hi 0.7 --max-runs 5 --target 47.94 --prefix seed/4_af_m --extra "--jobs load_balancer/data/variants/jobs_seed4.csv"
sc_lstm|./.venv/bin/python -m scheduler.run_v2 --name startcheck/lstm --engine start_check --alpha knee --forecast lstm
sc_mix0.75|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.75 --engine start_check --alpha knee --forecast mix0.75
sc_mix0.5|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.5 --engine start_check --alpha knee --forecast mix0.5
sc_mix0.25|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.25 --engine start_check --alpha knee --forecast mix0.25
sc_oracle|./.venv/bin/python -m scheduler.run_v2 --name startcheck/oracle --engine start_check --alpha knee --forecast oracle
sc_sn24|./.venv/bin/python -m scheduler.run_v2 --name startcheck/sn24 --engine start_check --alpha knee --forecast sn24
sc_s1|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed1 --engine start_check --alpha knee --jobs load_balancer/data/variants/jobs_seed1.csv
sc_s1_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed1_oracle --engine start_check --alpha knee --forecast oracle --jobs load_balancer/data/variants/jobs_seed1.csv
sc_s2|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed2 --engine start_check --alpha knee --jobs load_balancer/data/variants/jobs_seed2.csv
sc_s2_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed2_oracle --engine start_check --alpha knee --forecast oracle --jobs load_balancer/data/variants/jobs_seed2.csv
sc_s3|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed3 --engine start_check --alpha knee --jobs load_balancer/data/variants/jobs_seed3.csv
sc_s3_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed3_oracle --engine start_check --alpha knee --forecast oracle --jobs load_balancer/data/variants/jobs_seed3.csv
sc_s4|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed4 --engine start_check --alpha knee --jobs load_balancer/data/variants/jobs_seed4.csv
sc_s4_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed4_oracle --engine start_check --alpha knee --forecast oracle --jobs load_balancer/data/variants/jobs_seed4.csv
sc_azure|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure --engine start_check --alpha knee --jobs load_balancer/data/jobs_azure.csv
sc_azure_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure_oracle --engine start_check --alpha knee --forecast oracle --jobs load_balancer/data/jobs_azure.csv
