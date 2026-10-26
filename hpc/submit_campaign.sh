#!/bin/bash
# Submit the campaign as parallel jobs: one job per experiment (each with its own
# CPUs), plus a report job that starts when all of them have ended.
#
#   bash /home/USER/echoslice/hpc/submit_campaign.sh
#
# Options (environment):
#   ES_EXPS="E1 E2 E4 E5 E6 E7"   experiments to submit
#   ES_NTASKS=40               CPUs (tasks) per experiment job
#   ES_PARTITION=longq         queue for experiment jobs
#   ES_TIME=23:00:00           time limit for experiment jobs
#   ES_REPORT_PARTITION=longq  queue for the report job (shortq is enough if its limit is >= 1 h)
#   ES_SEEDS=30                seeds per configuration
#   ES_SMOKE=1                 submit a quick smoke test instead (one cell per experiment)
set -euo pipefail
ROOT="${ES_ROOT:-/home/USER/echoslice}"
B="$ROOT/Batch"
EXPS="${ES_EXPS:-E1 E2 E4 E5 E6 E7}"
NT="${ES_NTASKS:-40}"
PART="${ES_PARTITION:-longq}"
TIME="${ES_TIME:-23:00:00}"
RPART="${ES_REPORT_PARTITION:-longq}"
SEEDS="${ES_SEEDS:-30}"
SMOKE="${ES_SMOKE:-0}"
mkdir -p "$ROOT/logs"

declare -A NAME=( [E1]=es-E1-effect [E2]=es-E2-slicer-period [E4]=es-E4-qoe-sensitivity
                  [E5]=es-E5-headroom [E6]=es-E6-dynamic-load [E7]=es-E7-unbalanced-shifting )
pre=""; [[ "$SMOKE" == "1" ]] && pre="smoke-"
ids=()
for E in $EXPS; do
  id=$(sbatch --parsable --job-name="${pre}${NAME[$E]}" --partition="$PART" --time="$TIME" --ntasks="$NT" \
       --export=ALL,ES_SEEDS="$SEEDS",ES_SMOKE="$SMOKE" "$B" "$E")
  id=${id%%;*}
  echo "submitted $E as job $id (${pre}${NAME[$E]}, $NT CPUs, $PART, $TIME)"
  ids+=("$id")
done
dep=$(IFS=:; echo "${ids[*]}")
rexps=$(echo "$EXPS" | tr ' ' ',')
echo "$(date '+%F %T') experiments=[$EXPS] jobs=${ids[*]}" >> "$ROOT/logs/submitted_jobs.txt"
if rid=$(sbatch --parsable --job-name="${pre}es-report" --partition="$RPART" --time=02:00:00 --ntasks=1 \
         --cpus-per-task=4 --mem-per-cpu=4G --dependency="afterany:$dep" \
         --export=ALL,ES_SEEDS="$SEEDS",ES_SMOKE="$SMOKE" "$B" REPORT "$rexps"); then
  rid=${rid%%;*}
  echo "submitted report as job $rid (${pre}es-report), starts after jobs $dep"
  echo "$(date '+%F %T') report=$rid after $dep" >> "$ROOT/logs/submitted_jobs.txt"
else
  echo "WARNING: the report job was not accepted. When the jobs above have ended, run:"
  echo "  sbatch --job-name=es-report --ntasks=1 --cpus-per-task=4 --mem-per-cpu=4G $B REPORT $rexps"
fi
echo "job IDs saved in $ROOT/logs/submitted_jobs.txt"
