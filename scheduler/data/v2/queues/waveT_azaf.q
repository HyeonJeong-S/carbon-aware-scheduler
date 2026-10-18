afaz_main|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --target 41.59 --lo 0.45 --hi 0.65 --prefix azure/af_m --extra "--jobs load_balancer/data/jobs_azure.csv" --max-runs 5
afaz_s1|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --target 44.36 --lo 0.45 --hi 0.65 --prefix azure/seed1_af_m --extra "--jobs load_balancer/data/variants/jobs_azure_seed1.csv" --max-runs 5
afaz_s2|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --target 43.87 --lo 0.45 --hi 0.65 --prefix azure/seed2_af_m --extra "--jobs load_balancer/data/variants/jobs_azure_seed2.csv" --max-runs 5
afaz_s1_knee|./.venv/bin/python -m scheduler.run_v2 --name azure/seed1_arrival_fixed --engine arrival_fixed --alpha knee --jobs load_balancer/data/variants/jobs_azure_seed1.csv
afaz_s2_knee|./.venv/bin/python -m scheduler.run_v2 --name azure/seed2_arrival_fixed --engine arrival_fixed --alpha knee --jobs load_balancer/data/variants/jobs_azure_seed2.csv
afm_oracle2|./.venv/bin/python -m scheduler.match_alpha --engine arrival_fixed --target 39.40 --lo 0.5359 --hi 0.5437 --prefix arrival/oracle_af_m --extra "--forecast oracle" --max-runs 2
