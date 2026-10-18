sa_lstm|./.venv/bin/python -m scheduler.run_v2 --name startadmit/lstm --engine start_admit --forecast lstm
sa_oracle|./.venv/bin/python -m scheduler.run_v2 --name startadmit/oracle --engine start_admit --forecast oracle
sa_mix0.75|./.venv/bin/python -m scheduler.run_v2 --name startadmit/mix0.75 --engine start_admit --forecast mix0.75
sa_mix0.5|./.venv/bin/python -m scheduler.run_v2 --name startadmit/mix0.5 --engine start_admit --forecast mix0.5
sa_mix0.25|./.venv/bin/python -m scheduler.run_v2 --name startadmit/mix0.25 --engine start_admit --forecast mix0.25
sa_sn24|./.venv/bin/python -m scheduler.run_v2 --name startadmit/sn24 --engine start_admit --forecast sn24
sc_lstm|./.venv/bin/python -m scheduler.run_v2 --name startcheck/lstm --engine start_check --forecast lstm
sc_oracle|./.venv/bin/python -m scheduler.run_v2 --name startcheck/oracle --engine start_check --forecast oracle
sc_mix0.75|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.75 --engine start_check --forecast mix0.75
sc_mix0.5|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.5 --engine start_check --forecast mix0.5
sc_mix0.25|./.venv/bin/python -m scheduler.run_v2 --name startcheck/mix0.25 --engine start_check --forecast mix0.25
sc_sn24|./.venv/bin/python -m scheduler.run_v2 --name startcheck/sn24 --engine start_check --forecast sn24
af_rho0|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed_rho0 --engine arrival_fixed --rho 0
af_az_rho0|./.venv/bin/python -m scheduler.run_v2 --name azure/arrival_fixed_rho0 --engine arrival_fixed --rho 0 --jobs load_balancer/data/jobs_azure.csv
cast_az_rho0_m|./.venv/bin/python -m scheduler.run_v2 --name azure/rho0_m0.5375 --alpha 0.5375 --rho 0 --jobs load_balancer/data/jobs_azure.csv
af_exact_chk|./.venv/bin/python -m scheduler.run_v2 --name arrival/fixed_exact_m0.5437 --engine arrival_fixed_exact --alpha 0.5437
afdw_main|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --axis dw --target 39.22 --lo 0.5437 --hi 0.6 --prefix arrival/fixed_dw --max-runs 4
afdw_az|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --axis dw --target 34.06 --lo 0.5 --hi 0.5438 --prefix azure/af_dw --extra "--jobs load_balancer/data/jobs_azure.csv" --max-runs 4
sa_s1|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed1 --engine start_admit --jobs load_balancer/data/variants/jobs_seed1.csv
sa_s1_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed1_oracle --engine start_admit --forecast oracle --jobs load_balancer/data/variants/jobs_seed1.csv
sa_s2|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed2 --engine start_admit --jobs load_balancer/data/variants/jobs_seed2.csv
sa_s2_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed2_oracle --engine start_admit --forecast oracle --jobs load_balancer/data/variants/jobs_seed2.csv
sa_s3|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed3 --engine start_admit --jobs load_balancer/data/variants/jobs_seed3.csv
sa_s3_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed3_oracle --engine start_admit --forecast oracle --jobs load_balancer/data/variants/jobs_seed3.csv
sa_s4|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed4 --engine start_admit --jobs load_balancer/data/variants/jobs_seed4.csv
sa_s4_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/seed4_oracle --engine start_admit --forecast oracle --jobs load_balancer/data/variants/jobs_seed4.csv
sc_s1|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed1 --engine start_check --jobs load_balancer/data/variants/jobs_seed1.csv
sc_s1_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed1_oracle --engine start_check --forecast oracle --jobs load_balancer/data/variants/jobs_seed1.csv
sc_s2|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed2 --engine start_check --jobs load_balancer/data/variants/jobs_seed2.csv
sc_s2_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed2_oracle --engine start_check --forecast oracle --jobs load_balancer/data/variants/jobs_seed2.csv
sc_s3|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed3 --engine start_check --jobs load_balancer/data/variants/jobs_seed3.csv
sc_s3_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed3_oracle --engine start_check --forecast oracle --jobs load_balancer/data/variants/jobs_seed3.csv
sc_s4|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed4 --engine start_check --jobs load_balancer/data/variants/jobs_seed4.csv
sc_s4_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/seed4_oracle --engine start_check --forecast oracle --jobs load_balancer/data/variants/jobs_seed4.csv
sa_az|./.venv/bin/python -m scheduler.run_v2 --name startadmit/azure --engine start_admit --jobs load_balancer/data/jobs_azure.csv
sa_az_o|./.venv/bin/python -m scheduler.run_v2 --name startadmit/azure_oracle --engine start_admit --forecast oracle --jobs load_balancer/data/jobs_azure.csv
sc_az|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure --engine start_check --jobs load_balancer/data/jobs_azure.csv
sc_az_o|./.venv/bin/python -m scheduler.run_v2 --name startcheck/azure_oracle --engine start_check --forecast oracle --jobs load_balancer/data/jobs_azure.csv
