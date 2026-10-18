#!/bin/zsh
# 묶음 단위 완료 대기: 아직 안 끝난 묶음 가운데 하나라도 전부 끝나면 그 이름을 찍고 종료(알림 한 번).
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
bundle_done() {  # $1 = wave file
  while IFS= read -r line; do case "$line" in \#*|"") continue;; esac
    n=$(echo "$line" | sed -n 's/.*--name \([^ ]*\).*/\1/p'); [ -z "$n" ] && continue
    [ -f "scheduler/data/v2/$n/stats.json" ] || return 1
  done < "$1"; return 0
}
pending=()
for w in waveH_extra; do
  bundle_done scheduler/data/v2/$w.txt || pending+=($w)
done
[ -f scheduler/data/v2/main/joint_zcheck/stats.json ] || pending+=(zcheck)
[ -f scheduler/data/v2/priors/caspian_w1.0_frac.json ] || pending+=(caspian)
echo "waiting: $pending"
while true; do
  sleep 120
  for w in $pending; do
    case $w in
      zcheck) [ -f scheduler/data/v2/main/joint_zcheck/stats.json ] && { echo "BUNDLE DONE: zcheck"; exit 0; };;
      caspian) [ -f scheduler/data/v2/priors/caspian_w1.0_frac.json ] && { echo "BUNDLE DONE: caspian"; exit 0; };;
      *) bundle_done scheduler/data/v2/$w.txt && { echo "BUNDLE DONE: $w"; exit 0; };;
    esac
  done
  grep -l "Traceback" scheduler/data/v2/logs/*.log 2>/dev/null | grep -v -E "offline_bound_w4416|_gen_azure_seed" | head -3 | sed 's#^#ERROR in #'
  pgrep -f "launch.py|resume2.sh|resume3.sh|run_v2|run_priors_v2|pair_driver" >/dev/null || { echo "NO LAUNCHER RUNNING"; exit 1; }
done
