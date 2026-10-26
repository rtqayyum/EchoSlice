# EchoSlice: reaction-aware RAN slicing

Code and results for the paper *EchoSlice: Reaction-Aware RAN Slicing in O-RAN* (T. Qayyum). The manuscript itself is not part of this repository.

Most traffic adapts to the capacity it gets. Video players lower their bitrate, cloud-gaming senders back off, and TCP fills what it is given. So the demand a RAN slicer measures is partly the echo of its own earlier decisions. This repository holds:
- a simulator of that loop;
- the slicers we compare, including **EchoSlice**, our method;
- the full evaluation campaign (215,794 simulation runs, 30 seeds each), including the revision runs E15–E35;
- a real-player testbed (`realplayer/`): 20 real dash.js players and 10 TCP downloads over a paced bottleneck, run on a Slurm cluster;
- every result the paper reports.

EchoSlice has two parts. An xApp sets each slice's share from the number of active sessions, which the slicer does not cause, and a reference rate per session, and keeps best effort at least its fair share by session count. An rApp corrects the per-session rates with SPSA. It holds each trial for 90 s so that the applications can react, and it stops once the search settles.

## Names used in the paper and in the code

| Paper | Code |
|---|---|
| EchoSlice (final design) | `EchoSlice3(gate=True, bulk_frac=1.0, hold=90, settle=60)`, slicer name `echoslice-ff` |
| xApp only | `EchoSlice3(bulk_frac=1.0, freeze_after=0)`, slicer name `prior-ff` |
| EchoSlice, 12 s trials (first design) | `sim/slicers.py: EchoSlice3`, slicer names `echoslice3`, `echoslice3-l<λ>` |
| Zipper-like | `EchoSlice3(eta_mode="harmonic", freeze_after=0)`, slicer name `zipper-like` |
| BO instead of SPSA | `BOSlicer`, slicer name `bo-gpucb` |
| PPO-Stack | `experiments/drl.py --regime loopstack`, slicer names `drl-loopstack-s<seed>` |
| Online probing (baseline) | `EchoSlice` class (`echoslice`), built on `EchoSliceLite`, which the paper does not use |
| PPO-Loop / PPO-Replay | `experiments/drl.py`, slicer names `drl-loop` / `drl-twin` |
| Prior only | `EchoSlice3(freeze_after=0)`, slicer name `prior-only` |
| Probing from the prior | `EchoSlice3(space="share", ...)`, slicer name `probe-prior` |
| PPO-Prior | `experiments/drl.py --regime prior`, slicer name `drl-prior` |
| Held-out families (40 MHz, SINR 6 dB, 2 s segments) | experiment E17 |
| Balanced cells, load changes, shifting mixes, XR and L4S cells | experiments E1, E6, E7, E12 in `experiments/campaign_jobs.py` |

## What is in here

| Folder | Contents |
|---|---|
| `sim/` | Time-stepped fluid simulator of one NR cell (numba). `kernel.py` has the application logic: dash.js throughput rule, BOLA and DYNAMIC; libwebrtc-style GCC; TCP Cubic and TCP Prague with L4S marking. `qoe.py` has the QoE models: ITU-T P.1203 through its reference implementation, a G.1072-style gaming and XR model, and a log-throughput bulk MOS. `slicers.py` has all slicers, including `EchoSlice3`. `engine.py` runs a scenario. |
| `experiments/` | Campaign definition (`campaign_jobs.py`, experiments E1–E35), runner, Slurm-parallel driver (`campaign.py`), PPO baselines in plain numpy (`drl.py`), analysis and report (`campaign_report*.py`), figures. |
| `hpc/`, `Batch` | Slurm scripts used to run the campaign: environment set-up, submission, monitoring and a local smoke test. |
| `diagnostics/` | Round-2 diagnostics. Round-3 tuning of EchoSlice on held-out seeds 101–104 (`round3/TUNING.md`, `tune.py`, raw runs in `cache.jsonl`). The per-cell summary used by the paper (`round3/final_analysis.py`, `final_cells.csv`). Revision summaries for E15–E20 (`round4/final_analysis_r4.py`, `r4_*.csv`), E21–E27 (`round5/final_analysis_r6.py`, `r6_*.csv`), and E26 and E28–E35 (`round7/final_analysis_r7.py`, `r7_*.csv`). Tuned settings of each round: `round*/tuned.json`. |
| `analysis/` | Scripts that rebuild every table and figure of the paper from the released runs (`reproduce.sh`), and `MANIFEST.md`, which maps each table and figure to its experiments and output file. |
| `results/final/` | The final campaign: all runs, report, tables, figures, trained PPO policies (see `results/README.md`). |
| `results/pilot/` | The earlier local pilot (gate) runs. |
| `tier_a/` | Audit script for the DeepORAN real-stack dataset (not used in the paper's results). |
| `vendor/` | The ITU-T P.1203 reference implementation wheel (`itu-p1203` 1.11.0, MIT licence), so no network access is needed on the cluster. |

## Quick start

Python 3.10 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install vendor/itu_p1203-1.11.0-py3-none-any.whl
```

**Rebuild the paper's tables and figures from the released runs** (about 2 minutes, no simulation):

```bash
bash analysis/reproduce.sh work
```

This writes the following:
- the campaign report to `work/reports/CAMPAIGN_REPORT.md`;
- the result tables (CSV) to `work/results/tables/`;
- the paper's tables and figures to `analysis/tables/` and `analysis/figures/`.

The output matches the numbers in the paper exactly.

**Run one simulation:**

```python
from sim.engine import Scenario, simulate
from sim import slicers as SL

sc = Scenario(n_video=24, n_game=8, n_bulk=6, abr="dyn", strict=True)   # 24 viewers, 8 gamers, 6 bulk users
r = simulate(sc, SL.EchoSlice3(), seed=1)
print(r["mos_user"], r["mos_slice"])
```

One 600 s run takes about 20 s on one CPU core.

**Run the campaign** on a Slurm cluster. First edit the paths at the top of `Batch` and in `hpc/*.sh`; they point to `/home/USER/echoslice`. Then:

```bash
bash hpc/setup_env.sh                   # project-local venv
bash hpc/local_smoke.sh                 # quick end-to-end check
bash hpc/submit_final.sh                # PPO training, all experiments, PPO evaluation, report
bash hpc/monitor.sh                     # progress
```

Jobs are resumable: a rerun skips finished runs. The full campaign took under one hour on 9 × 40 cores plus 2 × 32 cores for PPO training.

## Experiments

| Exp | Question |
|---|---|
| E1 | Effect size in 36 balanced cells |
| E2 | Slicer period × video segment length (resonance) |
| E4 | Sensitivity to the QoE models |
| E5 | Forecast headroom in balanced cells |
| E6 | Load changes: gaming surge, bulk wave, video peak, churn |
| E7 | Unbalanced mixes, a compressed day cycle and a flash crowd (main result) |
| E9 | Ablations of EchoSlice |
| E10 | Imperfect telemetry: KPM delay and loss, QoE noise, QoE from KPMs only |
| E11 | Application hints and a lying application |
| E12 | XR and L4S (TCP Prague) cells |
| E13 | Theory checks: application step response, headroom knife-edge, resonance gain |
| E14 | Convergence over 30-minute runs |
| E15 | Equally informed baselines (prior only, probing from the prior, PPO-Prior) in the main scenarios |
| E16 | Longer holds (24–60 s), random trial order, wrong templates per slice |
| E17 | Held-out families: 40 MHz cell, mean SINR 6 dB, 2 s video segments |
| E18 | Convergence of the equally informed baselines |
| E19 | Imperfect telemetry for prior only and PPO-Prior |
| E20 | Session counts from radio activity, or kept 10 s after the last data |
| E21 | The cell changes mid-run (video rate x2 or x0.5, SINR -6 dB) with the same session counts |
| E22 | Session-count estimators in light cells with long segments |
| E23 | Share-dependent departures: users who leave after a long stall, finite bulk files |
| E24 | Template error sweep, x0.25 to x4 |
| E25 | Gated EchoSlice and a QoE feedback controller in all 72 scenarios |
| E26 | Extra PPO training seeds |
| E27 | Tuning runs (seeds 101-104) for E21-E26 (`diagnostics/round5/tuned.json`) |
| E28 | Tuning runs for a bulk floor in Mb/s and the BO exploration weight (`diagnostics/round6/tuned.json`) |
| E29 | Zipper-like provisioning, the Mb/s bulk floor and BO in all 72 scenarios |
| E30 | The same controllers with share-dependent departures and mid-run cell changes |
| E31 | BO and Zipper-like provisioning against the template error factor |
| E32 | PPO with frame stacking (PPO-Stack), two training seeds |
| E33 | Gated 90 s trials with the Mb/s bulk floor |
| E34 | Tuning runs for the fair-share bulk floor (`diagnostics/round7/tuned.json`) |
| E35 | The final design (`echoslice-ff`), the xApp alone (`prior-ff`) and no floor (`echoslice-nf`) in all sets |

Each configuration runs seeds 1–30. Seeds 101–104 were used only for tuning.

## What is real and what is synthetic

- **Real logic.** The application control logic is reimplemented from the real algorithms: dash.js rules, GCC's trendline detector and AIMD, and TCP Cubic. P.1203 is the ITU reference implementation.
- **Synthetic.** These parts are modelled, not taken from a real system:
  - the radio, a fluid model of one cell;
  - the gaming and XR QoE models (G.1072-style, with assumed XR parameters);
  - TCP Prague and L4S marking, as a fluid approximation;
  - the per-flow QoE estimate given to QoE-aware slicers.
- **Real players.** `realplayer/` runs real dash.js 4.7.4 players in headless Chromium and real TCP downloads over loopback, through a paced two-slice bottleneck. Results: `results/final/realplayer/hpc_600s` and `hpc_1800s` (20 players, 10 downloads, 80 Mb/s).
- **Not covered.** No radio stack (e.g. OAI) and no multi-cell effects.

## Citation

If you use this code or data, please cite the paper (details in `CITATION.cff`; to be updated with the publication).

## Licence

GNU General Public License v3.0, see `LICENSE`. The vendored P.1203 wheel keeps its own MIT licence.
