#!/bin/bash
# Round 5 (second review): session counts taken from radio activity instead of a session counter.
#
#   bash /home/USER/echoslice/hpc/submit_round5.sh
#
# Submits one experiment job (E20, 720 runs, no DRL) and a report after it.
set -euo pipefail
ROOT="${ES_ROOT:-/home/USER/echoslice}"
B="$ROOT/Batch"
NT="${ES_NTASKS:-40}"
PART="${ES_PARTITION:-longq}"
SEEDS="${ES_SEEDS:-30}"
mkdir -p "$ROOT/logs"
REC="$ROOT/logs/submitted_jobs.txt"
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=0,ES_DRL=skip"
id=$(sbatch --parsable --job-name=es-R5-counts --partition="$PART" --time=23:00:00 --ntasks="$NT" \
     --cpus-per-task=1 --mem-per-cpu=2G --export="$ENVX" "$B" E20); id=${id%%;*}
echo "submitted es-R5-counts as job $id"; echo "$(date '+%F %T') es-R5-counts $id" >> "$REC"
rid=$(sbatch --parsable --job-name=es-R5-report --partition="$PART" --time=04:00:00 --ntasks=1 --cpus-per-task=4 \
      --mem-per-cpu=8G --dependency="afterany:$id" --export="$ENVX" "$B" REPORT E20); rid=${rid%%;*}
echo "submitted es-R5-report as job $rid"; echo "$(date '+%F %T') es-R5-report $rid" >> "$REC"
