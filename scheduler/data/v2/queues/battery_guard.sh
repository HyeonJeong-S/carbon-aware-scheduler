#!/bin/zsh
# 배터리 보호: 15% 아래로 내려가면 실험(run_v2)을 멈추고(SIGSTOP), 40% 위로 오르면 재개(SIGCONT). 2분마다 확인.
paused=0
while true; do
  pct=$(pmset -g batt | grep -o '[0-9]*%' | tr -d '%')
  if [ "$pct" -lt 15 ] && [ $paused -eq 0 ]; then
    for pid in $(pgrep -f "scheduler.run_v2"); do kill -STOP $pid; done; paused=1; echo "$(date +%H:%M) battery $pct% → paused"
  elif [ "$pct" -gt 40 ] && [ $paused -eq 1 ]; then
    for pid in $(pgrep -f "scheduler.run_v2"); do kill -CONT $pid; done; paused=0; echo "$(date +%H:%M) battery $pct% → resumed"
  fi
  sleep 120
done
