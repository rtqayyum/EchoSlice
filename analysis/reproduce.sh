#!/bin/bash
# Rebuild the campaign report and the paper's tables and figures from the released runs.
#
#   bash analysis/reproduce.sh [work dir]      (default: ./work)
#
# Steps: unpack the runs -> campaign report (results/tables/*.csv, figures/, reports/CAMPAIGN_REPORT.md)
#        -> per-cell gaps (diagnostics/round3/final_cells.csv) -> paper tables and figures (analysis/tables, analysis/figures).
# Takes a few minutes and about 2 GB of disk. No simulation is run.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mkdir -p "${1:-$REPO/work}" && cd "${1:-$REPO/work}" && pwd)"
cd "$REPO"
PY="${PYTHON:-python3}"
"$PY" analysis/unpack_runs.py "$WORK"
"$PY" -m experiments.campaign report --root "$WORK" --exps E1,E2,E4,E5,E6,E7,E9,E10,E11,E12,E13,E14,E15,E16,E17,E18,E19,E20,E21,E22,E23,E24,E25,E26,E27 --tag released
"$PY" diagnostics/round3/final_analysis.py "$WORK"
"$PY" diagnostics/round4/final_analysis_r4.py "$WORK"
"$PY" diagnostics/round5/final_analysis_r6.py "$WORK"
"$PY" analysis/make_paper_assets.py "$WORK" "$WORK/results/tables" "$WORK/figures"
echo "done: report $WORK/reports/CAMPAIGN_REPORT.md, paper tables analysis/tables/, paper figures analysis/figures/"
