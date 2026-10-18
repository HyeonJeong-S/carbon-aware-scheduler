#!/bin/zsh
# 지정한 실행들이 모두 끝나면 한 번 알린다. 사용: zsh wait_runs.sh 이름1 이름2 ...
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
while true; do
  left=0; for n in "$@"; do [ -f "scheduler/data/v2/$n/stats.json" ] || left=$((left+1)); done
  [ $left -eq 0 ] && { echo "ALL DONE: $*"; exit 0; }
  pgrep -f "scheduler.run_v2|match_alpha" >/dev/null || { echo "NO RUNNER, $left left"; exit 1; }
  sleep 120
done
