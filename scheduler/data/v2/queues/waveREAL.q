real_cast_m|./.venv/bin/python -m scheduler.run_v2 --name real/cast_rho0_m0.5375 --alpha 0.5375 --no-lookahead --carbon-now lag1 --forecast 'lstm|US-CAL-CISO=sn24,US-TEX-ERCO=sn24,DE=sn24' --rho 0
real_cast_knee|./.venv/bin/python -m scheduler.run_v2 --name real/cast_rho0_knee --no-lookahead --carbon-now lag1 --forecast 'lstm|US-CAL-CISO=sn24,US-TEX-ERCO=sn24,DE=sn24' --rho 0
real_af_knee|./.venv/bin/python -m scheduler.run_v2 --name real/af_rho0_knee --engine arrival_fixed --no-lookahead --carbon-now lag1 --forecast 'lstm|US-CAL-CISO=sn24,US-TEX-ERCO=sn24,DE=sn24' --rho 0
real_fb_knee|./.venv/bin/python -m scheduler.run_v2 --name real/fb_rho0_knee --engine start_admit_fb --no-lookahead --carbon-now lag1 --forecast 'lstm|US-CAL-CISO=sn24,US-TEX-ERCO=sn24,DE=sn24' --rho 0
casper_cap17|./.venv/bin/python -m scheduler.run_priors_v2 --policies casper_cap --cap 17
