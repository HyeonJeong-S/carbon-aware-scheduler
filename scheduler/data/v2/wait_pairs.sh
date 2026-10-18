#!/bin/zsh
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
while pgrep -f "match_alpha.*seed/" >/dev/null || pgrep -f -- "--name rate/100_joint_a1" >/dev/null; do sleep 120; done
for s in 1 2 3 4; do grep -E "BEST|MATCHED" scheduler/data/v2/logs/pair_seed$s.log | tail -1; done
[ -f scheduler/data/v2/rate/100_joint_a1/stats.json ] && echo "rate/100_joint_a1 done" || echo "rate/100_joint_a1 MISSING"
