#!/bin/zsh
# 10-17 00:50 (32): resume_detached.sh 를 끊고(탐욕 둘이 A파를 붙들어 B파가 못 시작) 직접 돌리는 2차 재개 스크립트.
# 지금 따로 돌고 있는 B파 런처(waveB_early/waveB_joint)가 끝나길 기다린 뒤, 남은 파를 차례로 돈다. stats.json 있으면 건너뜀.
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
until ! pgrep -f "waveB_early.txt|waveB_joint.txt" >/dev/null; do sleep 60; done
echo "resume2 start $(date)"
for w in waveB_alpha waveC_herding waveD_sweeps waveG_azure waveE_seeds waveF_phi; do
  ./.venv/bin/python scheduler/data/v2/launch.py scheduler/data/v2/$w.txt 6
done
[ -f scheduler/data/v2/priors/caspian_w1.0_frac.json ] || ./.venv/bin/python -m scheduler.run_priors_v2 --policies caspian --caspian-omega1 1.0 --caspian-fractional --cap 17 > scheduler/data/v2/logs/priors_caspian2.log 2>&1
echo "resume2 done $(date)"
