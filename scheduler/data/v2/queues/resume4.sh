#!/bin/zsh
# 10-18 06:30 (2c): Caspian 이 홀로 도는 동안 코어가 놀아서 resume3 을 끊고 H파를 바로 띄운다. H파 뒤 시드 짝 이분법.
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
echo "resume4 start $(date)"
./.venv/bin/python scheduler/data/v2/queues/launch.py scheduler/data/v2/queues/waveH_extra.txt 6
./.venv/bin/python scheduler/data/v2/pair_driver.py --only seed1,seed2,seed3,seed4 --par 4
echo "resume4 done $(date)"
