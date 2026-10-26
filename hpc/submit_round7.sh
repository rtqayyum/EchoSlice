#!/bin/bash
# Fourth review round: Zipper-like provisioning, a bulk floor, Bayesian optimisation and frame-stacked PPO.
#
#   bash /home/tariq.qayyum/echoslice/hpc/submit_round7.sh
#
# Submits (job IDs go to logs/submitted_jobs.txt):
#   1. PPO trainings: frame-stacked PPO-Loop with seeds 1 and 2, and PPO-Loop seed 2 again (it failed in round 6)
#   2. tuning runs on seeds 101-104 (E28), then a step that writes diagnostics/round6/tuned.json
#   3. after the tuning: E29 (all 72 scenarios), E30 (departures and cell changes), E31 (template sweep)
#   4. after the trainings: E32 (frame-stacked PPO) and the missing E26 runs (PPO-Loop seed 2)
#   5. a report after everything
# Re-running is safe: finished runs are skipped.
set -euo pipefail
ROOT="${ES_ROOT:-/home/tariq.qayyum/echoslice}"
B="$ROOT/Batch"
PART="${ES_PARTITION:-longq}"
TIME="${ES_TIME:-23:00:00}"
DCPU="${ES_DRL_CPUS:-32}"
SEEDS="${ES_SEEDS:-30}"
mkdir -p "$ROOT/logs" "$ROOT/policies" "$ROOT/diagnostics/round6"
REC="$ROOT/logs/submitted_jobs.txt"
sub() {
  local name=$1; shift
  local id
  id=$(sbatch --parsable --job-name="${name}" "$@")
  id=${id%%;*}
  echo "submitted ${name} as job $id"
  echo "$(date '+%F %T') ${name} $id" >> "$REC"
  LAST=$id
}
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=0"
opts() { echo --partition="$PART" --time="$TIME" --ntasks="$1" --cpus-per-task=1 --mem-per-cpu=2G; }

train_ids=()
for RS in "loopstack 1" "loopstack 2" "loop 2"; do
  set -- $RS
  sub "es-drl-train-$1-s$2" --partition="$PART" --time="$TIME" --ntasks=1 --cpus-per-task="$DCPU" \
      --mem-per-cpu=2G --export="$ENVX,ES_DRL_ITERS=150,ES_DRL_EPISODES=40" "$B" DRLTRAIN "$1" "$2"
  train_ids+=("$LAST")
done

sub "es-R7-tune" $(opts 40) --export="$ENVX,ES_DRL=all" "$B" E28
tune_id=$LAST
sub "es-R7-tuneselect" --partition="$PART" --time=01:00:00 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=4G \
    --dependency="afterany:$tune_id" --export="$ENVX" "$B" TUNESELECT6
sel_id=$LAST
AFT=(--dependency="afterok:$sel_id")

all_ids=("$tune_id" "$sel_id")
sub "es-R7a-overall" $(opts 80) "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" E29
all_ids+=("$LAST")
sub "es-R7b-depart-change" $(opts 40) "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" E30
all_ids+=("$LAST")
sub "es-R7c-tfactor" $(opts 40) "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" E31
all_ids+=("$LAST")
dep=$(IFS=:; echo "${train_ids[*]}")
sub "es-R7d-ppo" $(opts 40) --dependency="afterany:$dep" --export="$ENVX,ES_DRL=only" "$B" "E32,E26"
all_ids+=("$LAST")

dep=$(IFS=:; echo "${all_ids[*]}:${train_ids[*]}" | tr ' ' ':')
sub "es-R7-report" --partition="$PART" --time=04:00:00 --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G \
    --dependency="afterany:$dep" --export="$ENVX" "$B" REPORT "E26,E28,E29,E30,E31,E32"
echo "job IDs saved in $REC"
