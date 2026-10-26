#!/bin/bash
# Fourth review round, part b: the gated long-hold design (E33, 3,900 runs).
# It reads the bulk floor from diagnostics/round6/tuned.json, so it waits for the round-7 tuning step
# if that step is still queued or running. Run it after submit_round7.sh:
#
#   bash /home/tariq.qayyum/echoslice/hpc/submit_round7b.sh
#
# Re-running is safe: finished runs are skipped.
set -euo pipefail
ROOT="${ES_ROOT:-/home/tariq.qayyum/echoslice}"
B="$ROOT/Batch"
PART="${ES_PARTITION:-longq}"
TIME="${ES_TIME:-23:00:00}"
SEEDS="${ES_SEEDS:-30}"
mkdir -p "$ROOT/logs"
REC="$ROOT/logs/submitted_jobs.txt"
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=0"

DEP=()
sel=$(squeue -u "$USER" -h -n es-R7-tuneselect -o %i | head -1 || true)
if [ -n "$sel" ]; then
  DEP=(--dependency="afterok:$sel")
  echo "waiting for the tuning step (job $sel)"
elif [ ! -f "$ROOT/diagnostics/round6/tuned.json" ]; then
  echo "diagnostics/round6/tuned.json is missing and no tuning step is queued. Run submit_round7.sh first." >&2
  exit 1
fi

id=$(sbatch --parsable --job-name=es-R7e-rapp --partition="$PART" --time="$TIME" --ntasks=40 \
     --cpus-per-task=1 --mem-per-cpu=2G "${DEP[@]}" --export="$ENVX,ES_DRL=all" "$B" E33)
id=${id%%;*}
echo "submitted es-R7e-rapp as job $id"
echo "$(date '+%F %T') es-R7e-rapp $id" >> "$REC"
id2=$(sbatch --parsable --job-name=es-R7e-report --partition="$PART" --time=04:00:00 --ntasks=1 \
      --cpus-per-task=4 --mem-per-cpu=8G --dependency="afterany:$id" --export="$ENVX" "$B" REPORT "E33")
id2=${id2%%;*}
echo "submitted es-R7e-report as job $id2"
echo "$(date '+%F %T') es-R7e-report $id2" >> "$REC"
