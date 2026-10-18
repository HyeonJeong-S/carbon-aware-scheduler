sc_c13|./.venv/bin/python -m scheduler.run_v2 --name capx/startcheck_1.00x --engine start_check --cap 1.00
sc_c26|./.venv/bin/python -m scheduler.run_v2 --name capx/startcheck_2.00x --engine start_check --cap 2.00
sc_small|./.venv/bin/python -m scheduler.run_v2 --name capx/startcheck_small --engine start_check --cap-json scheduler/data/v2/scenarios.json:synthetic.cap_clean_small
cm_c13|./.venv/bin/python -m scheduler.run_v2 --name capx/cast_1.00x_rho0_m0.5375 --alpha 0.5375 --cap 1.00 --rho 0
cm_c26|./.venv/bin/python -m scheduler.run_v2 --name capx/cast_2.00x_rho0_m0.5375 --alpha 0.5375 --cap 2.00 --rho 0
cm_small|./.venv/bin/python -m scheduler.run_v2 --name capx/cast_small_rho0_m0.5375 --alpha 0.5375 --rho 0 --cap-json scheduler/data/v2/scenarios.json:synthetic.cap_clean_small
