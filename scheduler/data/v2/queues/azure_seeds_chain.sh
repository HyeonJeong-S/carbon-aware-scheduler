#!/bin/zsh
# vmtable 내려받기가 끝나면 Azure 시드 1·2 워크로드를 만든다(G파 azure/seed1·2 여섯 판용).
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
G=load_balancer/data/generator
until ! pgrep -f "curl.*vmtable" >/dev/null; do sleep 30; done
sz=$(stat -f %z $G/vmtable.csv.gz.part 2>/dev/null || echo 0)
echo "download ended, size $sz"
if [ "$sz" -lt 400000000 ]; then echo "DOWNLOAD FAILED (size $sz)"; cat scheduler/data/v2/logs/_vmtable_dl.log; exit 1; fi
mv $G/vmtable.csv.gz.part $G/vmtable.csv.gz
for s in 1 2; do
  ./.venv/bin/python $G/gen_jobs_azure.py --seed $s --out load_balancer/data/variants/jobs_azure_seed$s.csv > scheduler/data/v2/logs/_gen_azure_seed$s.log 2>&1 && echo "seed $s ok: $(wc -l < load_balancer/data/variants/jobs_azure_seed$s.csv) lines" || echo "seed $s FAILED"
done
rm -f $G/stats_azure.txt   # report() 가 쓰는 부산물(주 워크로드의 것이 아님)
echo "AZURE SEEDS DONE"
