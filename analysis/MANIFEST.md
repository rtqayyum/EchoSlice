# Reproducibility manifest

Every table and figure of the paper and its supplement, the experiments it reads, and the file that `analysis/reproduce.sh` writes for it.
All experiments run 30 seeds (seeds 1–30). Seeds 101–104 were used only for tuning (E27, E28, E34 and `diagnostics/round3/`).
Job definitions: `experiments/campaign_jobs.py`. Released runs: `results/final/runs/<EXP>.jsonl.gz` (E21 in two parts).
Software versions used on the cluster: `results/final/env_freeze.txt`. PPO policies: `results/final/policies/`.

## Main paper

| Item | Content | Experiments | Output file |
|---|---|---|---|
| Table I | Main parameters | `experiments/campaign_jobs.py` (RAPP_FF, PRIOR_FF), `diagnostics/round7/tuned.json` | (in the paper) |
| Table II | All 72 scenarios by family | E1, E6, E7, E12, E15, E17, E25, E26, E29, E32, E35 | `analysis/tables/tab_overall7.tex` |
| Table III | Mid-run cell changes and share-dependent departures | E21, E23, E30, E35 | `analysis/tables/tab_robust7.tex` |
| Table IV | Real players, 600 s and 1800 s sessions | `results/final/realplayer/hpc_600s`, `hpc_1800s` | `analysis/tables/tab_realplayer7.tex` |
| Fig. 2 | CDF of per-scenario gaps | as Table II | `analysis/figures/fig_cdf.pdf` |
| Fig. 3 | Template error sweep | E24, E31, E35 | `analysis/figures/fig_tfactor.pdf` |
| Fig. 4 | Knife-edge and filter gain | E13, E2 | `analysis/figures/fig_theory.pdf` |

## Supplement

| Item | Content | Experiments | Output file |
|---|---|---|---|
| Table SI | Template sweep, numbers | E24, E31, E35 | `analysis/tables/tab_tfactor7.tex` |
| Table SII | Main parameters of the first design | configuration | (in the supplement) |
| Table SIII | 18 changing scenarios, all slicers | E6, E7, E15, E25, E26 | `analysis/tables/tab_main.tex` |
| Table SIV | 36 balanced cells | E1, E15 | `analysis/tables/tab_e1.tex` |
| Table SV | Wrong templates per class | E9, E16 | `analysis/tables/tab_templates.tex` |
| Table SVI | All 72 scenarios, first design | E1, E6, E7, E12, E15, E17, E25, E26 | `analysis/tables/tab_overall.tex` |
| Table SVII | Held-out operating conditions | E17 | `analysis/tables/tab_heldout.tex` |
| Table SVIII | Ablations, holds, trial order, count source | E9, E16, E20 | `analysis/tables/tab_ablation.tex` |
| Table SIX | Session-count estimators in light cells | E22 | `analysis/tables/tab_counts.tex` |
| Tables SX–SXVI | Mid-run changes, departures, XR and L4S, convergence, real players (4 players), politeness, application response | E21, E23, E12, E14, E18, E13 | `tab_mismatch`, `tab_depart`, `tab_xr`, `tab_conv`, `tab_realplayer`, `tab_politeness`, `tab_theory` |
| Figs. S1–S8 | Gap per scenario, SLA frontier, template sweep, ablations, telemetry, convergence, PPO training, knife-edge | E6, E7, E9, E10, E14, E19, policies | `fig_cells`, `fig_frontier`, `fig_ablation`, `fig_telemetry`, `fig_convergence`, `fig_drl` |

Per-cell summaries that the tables are built from:
`diagnostics/round3/final_cells.csv` (E1, E6, E7, E12), `diagnostics/round4/r4_*.csv` (E15–E20), `diagnostics/round5/r6_*.csv` (E21–E26) and `diagnostics/round7/r7_*.csv` (E26, E29–E35).
The first real-player runs on a two-core host (`results/final/realplayer/short_240s.jsonl`, `long_600s_hostloaded.jsonl`) are kept for the supplement; the long ones had CPU-caused stalls, so only their search trajectories are used.
Paired statistics (bootstrap intervals and Holm counts) are written to `analysis/assets_summary.json`.
