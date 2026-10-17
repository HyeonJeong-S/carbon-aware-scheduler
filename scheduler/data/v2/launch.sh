#!/bin/zsh
# 한 줄 = 한 실행. 6개 동시. 로그는 logs/<name with slash→_>.log
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
LIST=$1; PAR=${2:-6}
cat "$LIST" | xargs -P $PAR -I{} zsh -c 'args="{}"; name=$(echo "$args" | sed -E "s/.*--name ([^ ]+).*/\1/" | tr "/" "_"); ./.venv/bin/python -m scheduler.run_v2 $args > scheduler/data/v2/logs/$name.log 2>&1; echo "done $name $(tail -1 scheduler/data/v2/logs/$name.log | cut -c1-160)"'
