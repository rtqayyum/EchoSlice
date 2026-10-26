# Results

## `final/` — the campaign reported in the paper

All 110,610 runs completed with 0 errors. The runs were made in October 2026 with the code in this repository.

| Path | Contents |
|---|---|
| `runs/<EXP>.jsonl.gz` | Every run of experiment `<EXP>`, one JSON record per line (gzip). |
| `tables/*.csv` | Result tables written by the campaign report. |
| `CAMPAIGN_REPORT.md` | The report, with all tables in readable form. |
| `campaign_summary.json` | The same numbers in machine-readable form. |
| `report_figures/` | Figures written by the campaign report. |
| `paper_figures/` | The figures used in the paper (built by `analysis/make_paper_assets.py`). |
| `policies/` | Trained PPO policies (`drl_loop.json`, `drl_twin.json` = best validation; `*_last.json` = last iteration) and their training logs. |
| `job_summaries/` | One summary per Slurm job (exit code, failures, elapsed time). |
| `env_freeze.txt` | Python package versions on the cluster. |

### Run record fields

| Field | Meaning |
|---|---|
| `job` | The full job specification: experiment, cell, scenario parameters, slicer and its parameters, seed. This is enough to rerun the run with `experiments/runner.py`. |
| `slicer_name` | Name of the slicer as configured. |
| `mos_user` | Mean user MOS over the scoring period. |
| `mos_slice` | Mean MOS per slice. |
| `chunk_bounds`, `chunk_mos_user`, `chunk_slice_mos`, `chunk_flow_mos` | The same, per 300 s scoring window (per minute in E14). |
| `flow_mos`, `flow_slice`, `flow_type`, `flow_tput_mbps` | Per-flow results. |
| `share_mean`, `share_std`, `chunk_share_mean` | Slice shares chosen by the slicer. |
| `stall_ratio`, `switches_pm`, `bitrate_mbps` | Video statistics. |
| `game_rate`, `game_late`, `game_rtt_ms` | Gaming and XR statistics. |
| `bulk_mbps`, `cell_tput_mbps` | Bulk and cell throughput. |
| `l4s_qdelay_ms`, `l4s_mark_frac` | L4S queue delay and marking (E12). |
| `decide_ms` | Mean time per slicer decision. |
| `slice_trace` | Per-second trace `[t, shares.., offered Mb/s.., served Mb/s.., PRBs.., sessions..]` (E13 step runs). |
| `wall_s`, `host` | Run time and compute node. |

Runs whose `job.slicer.type` is `static` with a share vector `x` form the static grid. The "best static split" of each cell is chosen from it, leave one seed out.

The runs of one cancelled job (599815), started by mistake before PPO training had finished, were set aside and are not included. The PPO runs were all repeated with the final policies (job 599799).

## `pilot/` — the earlier local pilot

The first gate runs (E1, E2, E4, E5 at a smaller scale), made on a workstation before the HPC campaign. They are kept for completeness. The paper does not use them.
