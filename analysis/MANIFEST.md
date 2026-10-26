# Reproducibility manifest

Every table and figure of the paper, the experiments it reads, and the file that `analysis/reproduce.sh` writes for it.
All experiments run 30 seeds (seeds 1–30). Seeds 101–104 were used only for tuning (`diagnostics/round3/`).
Job definitions: `experiments/campaign_jobs.py`. Released runs: `results/final/runs/<EXP>.jsonl.gz` (E21 in two parts).
Software versions used on the cluster: `results/final/env_freeze.txt`. PPO policies: `results/final/policies/`.

| Paper item | Content | Experiments | Output file |
|---|---|---|---|
| Table I | Main parameters | configuration in `experiments/campaign_jobs.py`, `sim/slicers.py` | (in the paper) |
| Table II | 18 changing scenarios, all slicers | E6, E7, E15, E25, E26 | `analysis/tables/tab_main.tex` |
| Table III | 36 balanced cells | E1, E15 | `analysis/tables/tab_e1.tex` |
| Table IV | Wrong templates, with and without trials | E9, E16 | `analysis/tables/tab_templates.tex` |
| Table V | All 72 scenarios | E1, E6, E7, E12, E15, E17, E25, E26 | `analysis/tables/tab_overall.tex` |
| Table VI | Held-out operating conditions | E17 | `analysis/tables/tab_heldout.tex` |
| Table VII | Ablations, holds, trial order, count source | E9, E16, E20 | `analysis/tables/tab_ablation.tex` |
| Table VIII | Session-count estimators in light cells | E22 | `analysis/tables/tab_counts.tex` |
| Table IX | The cell changes mid-run | E21 | `analysis/tables/tab_mismatch.tex` |
| Table X | Share-dependent departures | E23 | `analysis/tables/tab_depart.tex` |
| Table XI | XR and L4S cells | E12, E15 | `analysis/tables/tab_xr.tex` |
| Table XII | Convergence | E14, E18 | `analysis/tables/tab_conv.tex` |
| Table XIII | Real players | `results/final/realplayer/short_240s.jsonl` (`realplayer/analyze.py`) | `analysis/tables/tab_realplayer.tex` |
| Table XIV | Politeness by capacity per session | E13 | `analysis/tables/tab_politeness.tex` |
| Table XV | Application response and knife-edge | E13 | `analysis/tables/tab_theory.tex` |
| Fig. 2 | Gap per scenario | E6, E7 | `analysis/figures/fig_cells.pdf` |
| Fig. 3 | Mean QoE against weakest-slice SLA | E7 | `analysis/figures/fig_frontier.pdf` |
| Fig. 4 | Template error sweep | E24 | `analysis/figures/fig_tfactor.pdf` |
| Fig. 5 | Ablations | E9 | `analysis/figures/fig_ablation.pdf` |
| Fig. 6 | Imperfect telemetry | E10, E19 | `analysis/figures/fig_telemetry.pdf` |
| Fig. 7 | Convergence curves | E14 | `analysis/figures/fig_convergence.pdf` |
| Fig. 8 | PPO training curves | `results/final/policies/drl_*_log.jsonl` | `analysis/figures/fig_drl.pdf` |
| Fig. 9 | Knife-edge and filter gain | E13, E2 | `analysis/figures/fig_theory.pdf` |

Per-cell summaries that the tables are built from:
`diagnostics/round3/final_cells.csv` (E1, E6, E7, E12) and `diagnostics/round4/r4_*.csv` (E15–E20) and `diagnostics/round5/r6_*.csv` (E21–E26).
The long real-player runs (`results/final/realplayer/long_600s_hostloaded.jsonl`) had CPU-caused stalls on the host; the paper uses only their search trajectories, not their QoE.
Paired statistics (bootstrap intervals and Holm counts) are written to `analysis/assets_summary.json`.
