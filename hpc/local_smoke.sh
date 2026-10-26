#!/bin/bash
# End-to-end smoke test of the final campaign on a workstation (no Slurm): tiny DRL training,
# one cell per experiment with 2 seeds, every analysis and figure.
#   bash hpc/local_smoke.sh <scratch-root> [workers]
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${1:?scratch root}"
W="${2:-2}"
mkdir -p "$ROOT"
for d in sim experiments tier_a hpc vendor; do rm -rf "$ROOT/$d"; cp -r "$SRC/$d" "$ROOT/$d"; done
cp "$SRC/Batch" "$SRC/requirements.txt" "$ROOT/"
cd "$ROOT"
export ES_ROOT="$ROOT" PYTHONUNBUFFERED=1 MPLBACKEND=Agg
mkdir -p policies
for REG in loop twin; do
  python3 -m experiments.drl train --regime "$REG" --out "policies/drl_${REG}.json" --workers "$W" \
          --iters 2 --episodes 2 --n-val 2 --val-every 1 > "policies/train_${REG}.log" 2>&1
  test -s "policies/drl_${REG}.json"
done
EXPS="E1 E2 E4 E5 E6 E7 E9 E10 E11 E12 E13 E14"
for E in $EXPS; do
  python3 -m experiments.campaign prepare --root "$ROOT" --exps "$E" --seeds 2 --ntasks "$W" --tag smoke --smoke
done
for E in $EXPS; do
  for ((t=0; t<W; t++)); do
    python3 -m experiments.campaign run --root "$ROOT" --exp "$E" --tag smoke --task "$t" > "$ROOT/run_${E}_${t}.log" 2>&1 &
  done
  wait
done
python3 -m experiments.campaign status --root "$ROOT"
python3 -m experiments.campaign report --root "$ROOT" --exps "$(echo $EXPS | tr ' ' ',')" --tag smoke || true
grep -n "analysis failed" "$ROOT/reports/CAMPAIGN_REPORT.md" || echo "no analysis failures"
