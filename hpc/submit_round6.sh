#!/bin/bash
# Final review round: mid-run mismatch (E21), count estimators (E22), share-dependent departures (E23),
# template error sweep (E24), gated variant and QoE feedback in all 72 scenarios (E25), extra PPO seeds (E26).
#
#   bash /home/USER/echoslice/hpc/submit_round6.sh
#
# Submits (job IDs go to logs/submitted_jobs.txt):
#   0. tuning runs on seeds 101-104 (E27), then a step that writes diagnostics/round5/tuned.json
#   1. four PPO trainings: PPO-Loop and PPO-Prior with training seeds 1 and 2
#   2. after the tuning: three experiment jobs E21 (120 tasks), E22+E23, E24+E25
#   3. E26 (the new PPO policies) after the trainings
#   4. a report after everything
# Re-running is safe: finished runs are skipped.
set -euo pipefail
ROOT="${ES_ROOT:-/home/USER/echoslice}"
B="$ROOT/Batch"
PART="${ES_PARTITION:-longq}"
TIME="${ES_TIME:-23:00:00}"
DCPU="${ES_DRL_CPUS:-32}"
SEEDS="${ES_SEEDS:-30}"
SMOKE="${ES_SMOKE:-0}"
pre=""; [[ "$SMOKE" == "1" ]] && pre="smoke-"
ITERS="${ES_DRL_ITERS:-150}"; EPS="${ES_DRL_EPISODES:-40}"
if [[ "$SMOKE" == "1" ]]; then ITERS="${ES_DRL_ITERS:-3}"; EPS="${ES_DRL_EPISODES:-8}"; fi
mkdir -p "$ROOT/logs" "$ROOT/policies"
REC="$ROOT/logs/submitted_jobs.txt"
sub() {
  local name=$1; shift
  local id
  id=$(sbatch --parsable --job-name="${pre}${name}" "$@")
  id=${id%%;*}
  echo "submitted ${pre}${name} as job $id"
  echo "$(date '+%F %T') ${pre}${name} $id" >> "$REC"
  LAST=$id
}
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=$SMOKE"
opts() { echo --partition="$PART" --time="$TIME" --ntasks="$1" --cpus-per-task=1 --mem-per-cpu=2G; }

train_ids=()
for REG in loop prior; do
  for S in 1 2; do
    sub "es-drl-train-${REG}-s${S}" --partition="$PART" --time="$TIME" --ntasks=1 --cpus-per-task="$DCPU" \
        --mem-per-cpu=2G --export="$ENVX,ES_DRL_ITERS=$ITERS,ES_DRL_EPISODES=$EPS" "$B" DRLTRAIN "$REG" "$S"
    train_ids+=("$LAST")
  done
done

sub "es-R6-tune" $(opts 40) --export="$ENVX,ES_DRL=all" "$B" E27
tune_id=$LAST
sub "es-R6-tuneselect" --partition="$PART" --time=01:00:00 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=4G \
    --dependency="afterany:$tune_id" --export="$ENVX" "$B" TUNESELECT
sel_id=$LAST
AFT=(--dependency="afterok:$sel_id")

all_ids=("$tune_id" "$sel_id")
sub "es-R6a-mismatch" $(opts "${ES_NTASKS_E21:-120}") "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" E21
all_ids+=("$LAST")
sub "es-R6b-counts-departures" $(opts 40) "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" "E22,E23"
all_ids+=("$LAST")
sub "es-R6c-tfactor-gated" $(opts 40) "${AFT[@]}" --export="$ENVX,ES_DRL=all" "$B" "E24,E25"
all_ids+=("$LAST")
dep=$(IFS=:; echo "${train_ids[*]}")
sub "es-R6d-ppo-seeds" $(opts 40) --dependency="afterany:$dep" --export="$ENVX,ES_DRL=only" "$B" E26
all_ids+=("$LAST")

dep=$(IFS=:; echo "${all_ids[*]}:${train_ids[*]}" | tr ' ' ':')
sub "es-R6-report" --partition="$PART" --time=04:00:00 --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G \
    --dependency="afterany:$dep" --export="$ENVX" "$B" REPORT "E21,E22,E23,E24,E25,E26,E27"
echo "job IDs saved in $REC"
