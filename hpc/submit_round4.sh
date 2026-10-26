#!/bin/bash
# Round 4 (review): equally informed baselines, long holds, random trial order, per-slice template
# errors and held-out workload families.
#
#   bash /home/USER/echoslice/hpc/submit_round4.sh
#
# Submits (job IDs go to logs/submitted_jobs.txt):
#   1. PPO training, regime 'prior' (action = log-multiplier of EchoSlice's template rates)
#   2. three experiment jobs without DRL runs: E15+E16, E17, E18+E19
#   3. the DRL evaluation (PPO-Prior, and PPO-Loop/Replay in the held-out families) after training
#   4. a report after everything
# Re-running is safe: finished runs are skipped. Options as in submit_final.sh (ES_SKIP_TRAIN=1,
# ES_SKIP_EVAL=1, ES_ONLY=E17, ES_AFTER=id:id, ES_DRL_CPUS=32, ES_SMOKE=1).
set -euo pipefail
ROOT="${ES_ROOT:-/home/USER/echoslice}"
B="$ROOT/Batch"
NT="${ES_NTASKS:-40}"
PART="${ES_PARTITION:-longq}"
TIME="${ES_TIME:-23:00:00}"
DCPU="${ES_DRL_CPUS:-32}"
ITERS="${ES_DRL_ITERS:-150}"
EPS="${ES_DRL_EPISODES:-40}"
SEEDS="${ES_SEEDS:-30}"
SMOKE="${ES_SMOKE:-0}"
pre=""; [[ "$SMOKE" == "1" ]] && pre="smoke-"
if [[ "$SMOKE" == "1" ]]; then ITERS="${ES_DRL_ITERS:-3}"; EPS="${ES_DRL_EPISODES:-8}"; fi
mkdir -p "$ROOT/logs" "$ROOT/policies"
REC="$ROOT/logs/submitted_jobs.txt"
sub() {   # sub <name> <sbatch options...>
  local name=$1; shift
  local id
  id=$(sbatch --parsable --job-name="${pre}${name}" "$@")
  id=${id%%;*}
  echo "submitted ${pre}${name} as job $id"
  echo "$(date '+%F %T') ${pre}${name} $id" >> "$REC"
  LAST=$id
}
EXP_OPTS=(--partition="$PART" --time="$TIME" --ntasks="$NT" --cpus-per-task=1 --mem-per-cpu=2G)
ENVX="ALL,ES_SEEDS=$SEEDS,ES_SMOKE=$SMOKE"

train_ids=()
if [[ "${ES_SKIP_TRAIN:-0}" != "1" ]]; then
  sub "es-drl-train-prior" --partition="$PART" --time="$TIME" --ntasks=1 --cpus-per-task="$DCPU" --mem-per-cpu=2G \
      --export="$ENVX,ES_DRL_ITERS=$ITERS,ES_DRL_EPISODES=$EPS" "$B" DRLTRAIN prior
  train_ids+=("$LAST")
fi

all_ids=()
declare -a EXP_GROUPS=("E15,E16:es-R4a-baselines-holds" "E17:es-R4b-heldout-families" "E18,E19:es-R4c-conv-telemetry")
for g in "${EXP_GROUPS[@]}"; do
  exps=${g%%:*}; name=${g#*:}
  if [[ -n "${ES_ONLY:-}" ]]; then
    keep=0
    for e in ${ES_ONLY//,/ }; do [[ ",$exps," == *",$e,"* ]] && keep=1; done
    (( keep )) || continue
  fi
  sub "$name" "${EXP_OPTS[@]}" --export="$ENVX,ES_DRL=skip" "$B" "$exps"
  all_ids+=("$LAST")
done

dep_opt=()
if (( ${#train_ids[@]} )); then dep_opt=(--dependency="afterany:$(IFS=:; echo "${train_ids[*]}")"); fi
if [[ "${ES_SKIP_EVAL:-0}" != "1" ]]; then
  sub "es-R4-drl-eval" "${EXP_OPTS[@]}" ${dep_opt[@]+"${dep_opt[@]}"} --export="$ENVX,ES_DRL=only" "$B" "E15,E17,E18,E19"
  all_ids+=("$LAST")
fi

dep=$(IFS=:; echo "${all_ids[*]} ${train_ids[*]:-} ${ES_AFTER:-}" | tr ' ' ':' | sed 's/::*/:/g; s/^://; s/:*$//')
if ! sub "es-R4-report" --partition="$PART" --time=04:00:00 --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G \
       --dependency="afterany:$dep" --export="$ENVX" "$B" REPORT "E15,E16,E17,E18,E19"; then
  echo "WARNING: report job not accepted; when the jobs above have ended run:"
  echo "  sbatch --job-name=es-R4-report --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G --time=04:00:00 $B REPORT E15,E16,E17,E18,E19"
fi
echo "job IDs saved in $REC"
