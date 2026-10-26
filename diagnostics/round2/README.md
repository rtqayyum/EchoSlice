# Round-2 diagnostics (held-out seeds 101–104)

Local checks behind section 5 and parts of sections 3–4 of `HPC_ROUND2_ANALYSIS.md`. Run from the repo root, each takes the output path as its only argument, for example `python diagnostics/round2/diag_cold.py out.jsonl`. Results from 26 October 2026 are in `results/`.

| Script | Question |
|---|---|
| `diag_cold.py` | Is the E7 stationary gap a convergence problem? (v2 from the equal split, scored later, started at the best split) |
| `diag_prior.py` | Warm start from a forecast snapshot at 40 s |
| `diag_resid.py` | EchoSlice as a live correction on top of the forecast (unstable under shifts) |
| `diag_v3.py` | Sketch of v3: exogenous session-count prior, no count moves for bulk |
| `diag_jumps.py` | Why v2 loses to v1 in E6 bulk wave and churn |
| `diag_forecast.py` | How Forecast + 20% splits the video-heavy cell |
| `diag_slices.py` | Per-slice MOS in the video-heavy cell |

None of these variants is in the campaign code; they are diagnostics, not tuned slicers.
