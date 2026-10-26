#!/bin/bash
# Fourth review round, part c: a bulk floor that scales with the cell (E34 tuning, E35 final design).
#
#   bash /home/tariq.qayyum/echoslice/hpc/submit_round8.sh
#
# 1. E34: 200 tuning runs on seeds 101-104
# 2. a short step that writes diagnostics/round7/tuned.json
# 3. E35: 10,440 runs (72 scenarios, template sweep, cell changes, departures)
# Re-running is safe: finished runs are skipped.
set -euo pipefail
ROOT="${ES_ROOT:-/home/tariq.qayyum/echoslice}"
B="$ROOT/Batch"
PART="${ES_PARTITION:-longq}"
SEEDS="${ES_SEEDS:-30}"
mkdir -p "$ROOT/logs" "$ROOT/diagnostics/round7"
REC="$ROOT/logs/submitted_jobs.txt"
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=0,ES_DRL=all"
sub() {
  local name=$1; shift
  local id
  id=$(sbatch --parsable --job-name="$name" "$@")
  id=${id%%;*}
  echo "submitted $name as job $id"
  echo "$(date '+%F %T') $name $id" >> "$REC"
  LAST=$id
}
sub es-R8-tune --partition="$PART" --time=04:00:00 --ntasks=40 --cpus-per-task=1 --mem-per-cpu=2G --export="$ENVX" "$B" E34
sub es-R8-tuneselect --partition="$PART" --time=00:30:00 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=4G \
    --dependency="afterany:$LAST" --output="$ROOT/logs/%x_%j.out" \
    --wrap="module load anaconda3 2>/dev/null || true; $ROOT/.venv/bin/python $ROOT/diagnostics/round7/select_tuned7.py $ROOT && test -s $ROOT/diagnostics/round7/tuned.json"
sub es-R8-final --partition="$PART" --time=12:00:00 --ntasks=80 --cpus-per-task=1 --mem-per-cpu=2G \
    --dependency="afterok:$LAST" --export="$ENVX" "$B" E35
echo "job IDs saved in $REC"
