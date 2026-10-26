#!/bin/bash
# Submit the final EchoSlice campaign as parallel jobs.
#
#   bash /home/USER/echoslice/hpc/submit_final.sh
#
# What it submits (all job IDs are written to logs/submitted_jobs.txt):
#   1. two DRL training jobs (PPO, 1 task x ES_DRL_CPUS CPUs each): loop and twin regimes
#   2. nine experiment jobs (40 tasks each) with DRL-policy runs left out
#   3. one DRL evaluation job that starts when both training jobs have ended
#   4. the DeepORAN audit, if the data directory exists
#   5. the report job, after everything above has ended
# Re-running this script is safe: finished runs are kept and skipped, and a job that finds
# another job of this project already working on the same experiment skips it.
#
# Options (environment):
#   ES_NTASKS=40        tasks per experiment job      ES_PARTITION=longq   ES_TIME=23:00:00
#   ES_DRL_CPUS=32      CPUs per DRL training job (must fit one node: check `sinfo -o "%P %c"`)
#   ES_DRL_ITERS=150    PPO iterations                ES_DRL_EPISODES=40   episodes per iteration
#   ES_SEEDS=30         seeds per configuration       ES_SMOKE=1           quick end-to-end test
#   ES_SKIP_TRAIN=1     do not (re)train DRL; use the policies already in policies/ (or being trained)
#   ES_SKIP_EVAL=1      do not submit the DRL evaluation job (one is already queued)
#   ES_ONLY=E1,E7       submit only these experiment groups' jobs (default: all nine)
#   ES_AFTER=id:id      extra job IDs the report must wait for (e.g. training/eval jobs already queued)
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
sub() {   # sub <name> <sbatch options...> -- <Batch args...>
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

# 1. DRL training
train_ids=()
if [[ "${ES_SKIP_TRAIN:-0}" != "1" ]]; then
  for REG in loop twin; do
    sub "es-drl-train-$REG" --partition="$PART" --time="$TIME" --ntasks=1 --cpus-per-task="$DCPU" --mem-per-cpu=2G \
        --export="$ENVX,ES_DRL_ITERS=$ITERS,ES_DRL_EPISODES=$EPS" "$B" DRLTRAIN "$REG"
    train_ids+=("$LAST")
  done
fi

# 2. experiments without the DRL-policy runs
all_ids=()
# (do not call this array GROUPS: that is a read-only bash variable holding the user's group IDs)
declare -a EXP_GROUPS=("E1:es-F1-effect-size" "E2,E4,E5:es-F2-period-qoe-headroom" "E6:es-F4-dynamic-load"
                   "E7:es-F5-unbalanced-shifting-sla" "E9,E11:es-F6-ablations-hints" "E10:es-F7-imperfect-telemetry"
                   "E12:es-F9-xr-l4s" "E13:es-F10-theory-checks" "E14:es-F11-convergence")
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

# 3. DRL evaluation runs, after training has ended (afterany, so a failed training cannot leave this job
#    and the report waiting forever; DRL runs then fail fast and show up as errors in the report)
dep_opt=()
if (( ${#train_ids[@]} )); then dep_opt=(--dependency="afterany:$(IFS=:; echo "${train_ids[*]}")"); fi
if [[ "${ES_SKIP_EVAL:-0}" != "1" ]]; then
  sub "es-drl-eval" "${EXP_OPTS[@]}" ${dep_opt[@]+"${dep_opt[@]}"} --export="$ENVX,ES_DRL=only" "$B" "E1,E6,E7,E10,E12,E14"
  all_ids+=("$LAST")
fi

# 4. DeepORAN audit (Tier A) if the data is there
if [[ -d "$ROOT/data/deeporan_v2" ]]; then
  sub "es-audit-deeporan" --partition="$PART" --time=08:00:00 --ntasks=1 --cpus-per-task=16 --mem-per-cpu=4G \
      --export="$ENVX" "$B" AUDIT
  all_ids+=("$LAST")
else
  echo "note: $ROOT/data/deeporan_v2 not found, audit not submitted (upload the data, then: sbatch --job-name=es-audit-deeporan --ntasks=1 --cpus-per-task=16 --mem-per-cpu=4G --time=08:00:00 $B AUDIT)"
fi

# 5. report after everything
dep=$(IFS=:; echo "${all_ids[*]} ${train_ids[*]:-} ${ES_AFTER:-}" | tr ' ' ':' | sed 's/::*/:/g; s/^://; s/:*$//')
if ! sub "es-report" --partition="$PART" --time=04:00:00 --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G \
       --dependency="afterany:$dep" --export="$ENVX" "$B" REPORT; then
  echo "WARNING: report job not accepted; when the jobs above have ended run:"
  echo "  sbatch --job-name=es-report --ntasks=1 --cpus-per-task=4 --mem-per-cpu=8G --time=04:00:00 $B REPORT"
fi
echo "job IDs saved in $REC"
