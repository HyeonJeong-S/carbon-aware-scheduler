#!/bin/zsh
cd /Users/jongha/Desktop/GitHub/carbon-aware-scheduler
for w in waveA_main waveB_alpha waveC_herding waveD_sweeps waveG_azure waveE_seeds waveF_phi; do
  echo "=== $w start $(date) ==="
  ./.venv/bin/python scheduler/data/v2/launch.py scheduler/data/v2/$w.txt 6
  echo "=== $w done $(date) ==="
done
echo "ALL WAVES DONE $(date)"
