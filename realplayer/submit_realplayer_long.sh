#!/bin/bash
# The deployed design with real players: 27 sessions of 1800 s (20 players, 10 downloads), one per array task.
# Rebuilds the test video at 1900 s first if the current one is shorter. Run on the login node:
#
#   bash /home/USER/echoslice/realplayer/submit_realplayer_long.sh
set -euo pipefail
ROOT="${ES_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="$ROOT/.venv/bin/python"
MPD="$ROOT/realplayer/www/video/manifest.mpd"
DUR=$(grep -o 'mediaPresentationDuration="PT[0-9HMS.]*"' "$MPD" 2>/dev/null || true)
echo "current video: ${DUR:-none}"
if ! echo "$DUR" | grep -q "PT0H3[1-9]M\|PT0H[4-9][0-9]M\|PT[1-9]H"; then
  FF=$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
  rm -rf "$ROOT/realplayer/www/video"
  VIDEO_T=1900 FFMPEG="$FF" bash "$ROOT/realplayer/make_video.sh"
  grep -o 'mediaPresentationDuration="[^"]*"' "$MPD"
fi
N=$("$PY" "$ROOT/realplayer/campaign_hpc.py" --set long --list | tail -1 | awk '{print $1}')
mkdir -p "$ROOT/logs"
id=$(sbatch --parsable --job-name=es-realplayer-long --partition="${ES_PARTITION:-longq}" --time=01:15:00 \
     --array=0-$((N - 1))%"${ES_RP_PARALLEL:-14}" --ntasks=1 --cpus-per-task=8 --mem=24G \
     --output="$ROOT/logs/%x_%A_%a.out" --error="$ROOT/logs/%x_%A_%a.err" \
     --wrap="module load anaconda3 2>/dev/null || true; export PLAYWRIGHT_BROWSERS_PATH=$ROOT/.pw-browsers; \
             $PY $ROOT/realplayer/campaign_hpc.py --set long --task \$SLURM_ARRAY_TASK_ID")
echo "submitted es-realplayer-long as array job $id ($N runs)"
echo "$(date '+%F %T') es-realplayer-long $id" >> "$ROOT/logs/submitted_jobs.txt"
