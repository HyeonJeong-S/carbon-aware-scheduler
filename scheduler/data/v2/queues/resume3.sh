#!/bin/zsh
# 10-17 (7b): resume2(B~G·E·F·Caspian) 가 끝난 뒤 H파(도착률 2배·캘리포니아 SN-24)와 조건별 같은 지연 짝(표 6)을 돈다.
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
until ! pgrep -f "resume2.sh" >/dev/null; do sleep 120; done
echo "resume3 start $(date)"
./.venv/bin/python scheduler/data/v2/queues/launch.py scheduler/data/v2/queues/waveH_extra.txt 6
./.venv/bin/python scheduler/data/v2/pair_driver.py --par 3
echo "resume3 done $(date)"
