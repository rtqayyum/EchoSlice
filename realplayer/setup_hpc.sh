#!/bin/bash
# One-time set-up of the real-player check on the cluster (run on the login node, it needs the internet):
# Playwright and its headless Chromium inside the project, a static ffmpeg from imageio-ffmpeg, the test
# video, and a 40 s smoke run with 2 players.
#
#   bash /home/USER/echoslice/realplayer/setup_hpc.sh
set -euo pipefail
ROOT="${ES_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
module load anaconda3 2>/dev/null || true
PY="$ROOT/.venv/bin/python"
export PLAYWRIGHT_BROWSERS_PATH="$ROOT/.pw-browsers"
"$PY" -m pip install --quiet "playwright==${RP_PW_VERSION:-1.63.0}" imageio-ffmpeg
"$PY" -m playwright install chromium
FF=$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
echo "ffmpeg: $FF"
if [[ ! -s "$ROOT/realplayer/www/video/manifest.mpd" ]]; then
  FFMPEG="$FF" bash "$ROOT/realplayer/make_video.sh"
fi
echo "=== smoke run (40 s, 2 players)"
"$PY" "$ROOT/realplayer/testbed.py" --slicer static --x 0.5 --T 40 --t_eval0 10 --players 2 --bulk 1 --C 8e6 \
      --port 9799 --out "$ROOT/logs/realplayer_smoke.jsonl" | tee "$ROOT/logs/realplayer_smoke_last.txt"
if ! "$PY" -c "import json,sys; d=json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]); sys.exit(0 if d['served_video_mbps'] > 0.5 else 1)" "$ROOT/logs/realplayer_smoke_last.txt"; then
  echo "set-up FAILED: the players fetched no video. Run: PLAYWRIGHT_BROWSERS_PATH=$ROOT/.pw-browsers $PY $ROOT/realplayer/diag_hpc.py" >&2
  exit 1
fi
echo "set-up OK"
