#!/bin/bash
# Submit the real-player runs as one Slurm array (39 runs, 600 s each, 8 CPUs per run).
#
#   bash /home/USER/echoslice/realplayer/submit_realplayer.sh
set -euo pipefail
ROOT="${ES_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
N=$("$ROOT/.venv/bin/python" "$ROOT/realplayer/campaign_hpc.py" --list | tail -1 | awk '{print $1}')
mkdir -p "$ROOT/logs"
id=$(sbatch --parsable --job-name=es-realplayer --partition="${ES_PARTITION:-longq}" --time=01:00:00 \
     --array=0-$((N - 1))%"${ES_RP_PARALLEL:-13}" --ntasks=1 --cpus-per-task=8 --mem=24G \
     --output="$ROOT/logs/%x_%A_%a.out" --error="$ROOT/logs/%x_%A_%a.err" \
     --wrap="module load anaconda3 2>/dev/null || true; export PLAYWRIGHT_BROWSERS_PATH=$ROOT/.pw-browsers; \
             $ROOT/.venv/bin/python $ROOT/realplayer/campaign_hpc.py --task \$SLURM_ARRAY_TASK_ID")
echo "submitted es-realplayer as array job $id ($N runs)"
echo "$(date '+%F %T') es-realplayer $id" >> "$ROOT/logs/submitted_jobs.txt"
