#!/bin/bash
# Build the test video for the real-player check: 680 s of synthetic H.264 content, six rungs
# (0.3-4.5 Mb/s), 4 s segments, DASH with a template MPD. Needs ffmpeg with libx264.
set -euo pipefail
OUT="${1:-$(dirname "$0")/www/video}"
mkdir -p "$OUT" && cd "$OUT"
ffmpeg -hide_banner -loglevel error -f lavfi -i "testsrc2=size=854x480:rate=25,noise=alls=30:allf=t" -t 680 \
 -filter_complex "[0:v]split=6[a][b][c][d][e][f];[a]scale=320:180[v0];[b]scale=480:270[v1];[c]scale=640:360[v2];[d]scale=640:360[v3];[e]scale=854:480[v4];[f]scale=854:480[v5]" \
 -map "[v0]" -map "[v1]" -map "[v2]" -map "[v3]" -map "[v4]" -map "[v5]" -c:v libx264 -preset ultrafast -tune zerolatency -profile:v baseline -g 100 -keyint_min 100 -sc_threshold 0 \
 -b:v:0 300k -maxrate:v:0 300k -bufsize:v:0 300k -b:v:1 750k -maxrate:v:1 750k -bufsize:v:1 750k -b:v:2 1200k -maxrate:v:2 1200k -bufsize:v:2 1200k \
 -b:v:3 2000k -maxrate:v:3 2000k -bufsize:v:3 2000k -b:v:4 3000k -maxrate:v:4 3000k -bufsize:v:4 3000k -b:v:5 4500k -maxrate:v:5 4500k -bufsize:v:5 4500k \
 -x264-params nal-hrd=cbr -f dash -seg_duration 4 -use_template 1 -use_timeline 0 -adaptation_sets "id=0,streams=v" manifest.mpd
echo "video written to $OUT"
