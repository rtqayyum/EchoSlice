#!/bin/bash
# Progress, CPU, memory and failures for the EchoSlice campaign.
#
#   bash /home/USER/echoslice/hpc/monitor.sh            all jobs of this project in the queue
#   bash /home/USER/echoslice/hpc/monitor.sh 123456     one job
#   watch -n 60 bash /home/USER/echoslice/hpc/monitor.sh
set -uo pipefail
ROOT="${ES_ROOT:-/home/USER/echoslice}"
PY="$ROOT/.venv/bin/python"
ME="${USER:-USER}"
cd "$ROOT" || exit 1

if [[ $# -ge 1 ]]; then
  JOBS="$1"
else
  # only jobs whose name belongs to this project
  JOBS=$(squeue -h -u "$ME" -o "%i %j" 2>/dev/null | awk '$2 ~ /^(echoslice|es-|smoke-es-)/ {print $1}' | paste -sd, -)
fi

echo "=== queue (this project)"
if [[ -n "${JOBS:-}" ]]; then
  squeue -j "$JOBS" -o "%.10i %.26j %.8T %.10M %.10l %.6D %.5C %R" 2>/dev/null
else
  echo "no running or pending jobs of this project"
fi

echo; echo "=== experiments (all runs so far, any job)"
"$PY" -m experiments.campaign status --root "$ROOT" 2>/dev/null || echo "(environment not built yet)"

for J in ${JOBS//,/ }; do
  d=$(ls -d "$ROOT"/logs/*_"$J" 2>/dev/null | head -n 1)      # works for running and finished jobs
  [[ -n "$d" && -d "$d" ]] || { echo; echo "=== job $J: no log folder yet"; continue; }
  name=$(basename "$d"); name=${name%_"$J"}
  echo; echo "=== job $J ($name): per-task logs in $d"
  nf=$(grep -l "finished in" "$d"/*_task*.out 2>/dev/null | wc -l)
  nt=$(ls "$d"/*_task*.out 2>/dev/null | wc -l)
  echo "tasks finished: $nf of $nt task logs"
  echo "latest progress per task (last 8 tasks):"
  for f in $(ls "$d"/*_task*.out 2>/dev/null | tail -n 8); do
    printf "  %-22s %s\n" "$(basename "$f" .out)" "$(grep -E 'done,|finished' "$f" | tail -n 1)"
  done
  echo "CPU and memory (running steps):"
  sstat -a -j "$J" --format=JobID%18,NTasks,AveCPU,AveRSS,MaxRSS,MaxVMSize 2>/dev/null | head -n 8
  sstat -j "$J.batch" --format=JobID,AveCPU,MaxRSS,MaxVMSize 2>/dev/null | tail -n +3
done

echo; echo "=== DRL training (PPO)"
for REG in loop twin prior; do
  f="$ROOT/policies/drl_${REG}_log.jsonl"
  if [[ -s "$f" ]]; then
    "$PY" -c "import json,sys; L=[json.loads(x) for x in open(sys.argv[1]) if x.strip()]; d=L[-1]; v=[x['val_utility'] for x in L if 'val_utility' in x]; print(f'  {sys.argv[2]}: iteration {d[\"iter\"]+1}, {d[\"elapsed_min\"]:.0f} min, train utility {d[\"mean_utility\"]:.3f}, best validation {max(v) if v else float(\"nan\"):.3f}')" "$f" "$REG" 2>/dev/null
  else
    echo "  $REG: not started"
  fi
done

echo; echo "=== failures (logs of this project)"
hits=$(grep -RlniE "error|fatal|failed|traceback|oom|killed|timeout" "$ROOT/logs/" --include='*.err' 2>/dev/null | head -n 20)
if [[ -n "$hits" ]]; then echo "$hits"; else echo "no error lines in *.err files"; fi
grep -Rh "ERROR job" "$ROOT/logs/" --include='*.out' 2>/dev/null | tail -n 5

echo; echo "=== results"
echo "partial runs:  $ROOT/results/<EXP>/parts/*.jsonl"
echo "merged runs:   $ROOT/results/<EXP>/merged.jsonl (after the report)"
echo "tables:        $ROOT/results/tables/"
echo "figures:       $ROOT/figures/"
echo "summary:       $ROOT/results/campaign_summary.json"
echo "report:        $ROOT/reports/CAMPAIGN_REPORT.md"
