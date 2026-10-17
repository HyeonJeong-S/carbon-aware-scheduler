#!/bin/zsh
# 세션이 닫혀도 남은 실험을 이어 돈다. 이미 stats.json 이 있는 실행은 건너뛴다.
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
until ! pgrep -f "launch_all.sh" >/dev/null; do sleep 120; done
echo "resume start $(date)"
for w in waveA_main waveB_alpha waveC_herding waveD_sweeps waveG_azure waveE_seeds waveF_phi; do
  ./.venv/bin/python scheduler/data/v2/launch.py scheduler/data/v2/$w.txt 6
done
[ -f scheduler/data/v2/priors/caspian_w1.0_frac.json ] || ./.venv/bin/python -m scheduler.run_priors_v2 --policies caspian --caspian-omega1 1.0 --caspian-fractional --cap 17 > scheduler/data/v2/logs/priors_caspian2.log 2>&1
echo "resume done $(date)"
