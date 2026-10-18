ign_sn24|./.venv/bin/python -m scheduler.run_v2 --name main/ignore_sn24 --engine ignore --alpha knee --forecast sn24
ign_lag1|./.venv/bin/python -m scheduler.run_v2 --name lag1/ignore --engine ignore --alpha knee --carbon-now lag1
ign_w3|./.venv/bin/python -m scheduler.run_v2 --name forecast/weather3_sn24_ignore --engine ignore --alpha knee --forecast 'lstm|US-CAL-CISO=sn24,US-TEX-ERCO=sn24,DE=sn24'
ign_lnet|./.venv/bin/python -m scheduler.run_v2 --name lnet/100_ignore --engine ignore --alpha knee --l-net-max 100
ign_h12|./.venv/bin/python -m scheduler.run_v2 --name horizon/12_ignore --engine ignore --alpha knee --horizon 12
ign_h6|./.venv/bin/python -m scheduler.run_v2 --name horizon/6_ignore --engine ignore --alpha knee --horizon 6
