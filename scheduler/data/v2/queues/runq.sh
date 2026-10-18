#!/bin/zsh
# 사용: zsh scheduler/data/v2/queues/runq.sh <큐파일> <동시수>   — 줄마다 "이름|명령", 로그는 logs/<이름>.log (돌고 있는 큐 파일에 줄을 덧붙이지 말 것)
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
Q=$1; N=${2:-8}
while IFS='|' read -r name cmd; do
  [[ -z "$name" ]] && continue
  while (( ${#jobstates} >= N )); do sleep 20; done
  print "$(date '+%H:%M') 시작 $name"
  ( eval "$cmd" > scheduler/data/v2/logs/$name.log 2>&1; print "$(date '+%H:%M') 끝 $name ($?)" ) &
done < $Q
wait
print "$(date '+%H:%M') 큐 끝"
