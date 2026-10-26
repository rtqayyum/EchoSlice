"""Real-player runs on the cluster: 20 dash.js players and 10 TCP downloads over an 80 Mb/s paced bottleneck,
600 s per run, one run per Slurm array task.

  python realplayer/campaign_hpc.py --list            print the run list
  python realplayer/campaign_hpc.py --task N          run task N (0-based) into results/realplayer_hpc/
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = [(f"static-0.{i}", ["--slicer", "static", "--x", f"0.{i}"]) for i in range(5, 10)]
CFG += [("usage", ["--slicer", "usage"]), ("forecast+10%", ["--slicer", "forecast", "--h", "0.1"]),
        ("prior", ["--slicer", "prior"]),
        ("echoslice", ["--slicer", "echoslice"]),
        ("echoslice-h36", ["--slicer", "echoslice", "--hold", "36", "--settle", "12"]),
        ("prior-rho0.5", ["--slicer", "prior", "--rho", "1.5e6"]),
        ("echoslice-rho0.5", ["--slicer", "echoslice", "--rho", "1.5e6"]),
        ("echoslice-h36-rho0.5", ["--slicer", "echoslice", "--hold", "36", "--settle", "12", "--rho", "1.5e6"])]
SEEDS = [1, 2, 3]
RUNS = [(t, a, s) for s in SEEDS for t, a in CFG]
COMMON = ["--players", "20", "--bulk", "10", "--C", "80e6", "--T", "600", "--t_eval0", "60"]
# --set long: 1800 s sessions for the deployed design, gated trials held 90 s and scored on the last 30 s
RAPP = ["--slicer", "echoslice", "--hold", "90", "--settle", "60", "--gate"]
CFG_LONG = [(f"static-0.{i}", ["--slicer", "static", "--x", f"0.{i}"]) for i in range(5, 10)]
CFG_LONG += [("prior", ["--slicer", "prior"]), ("prior-rho0.5", ["--slicer", "prior", "--rho", "1.5e6"]),
             ("echoslice-rapp", RAPP), ("echoslice-rapp-rho0.5", RAPP + ["--rho", "1.5e6"])]
RUNS_LONG = [(t, a, s) for s in SEEDS for t, a in CFG_LONG]
COMMON_LONG = ["--players", "20", "--bulk", "10", "--C", "80e6", "--T", "1800", "--t_eval0", "120"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=int)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--set", default="short", choices=["short", "long"])
    a = ap.parse_args()
    if a.set == "long":
        RUNS, COMMON = RUNS_LONG, COMMON_LONG
    if a.list:
        for i, (t, _, s) in enumerate(RUNS):
            print(i, t, s)
        print(len(RUNS), "runs")
        sys.exit(0)
    t, args, s = RUNS[a.task]
    out = os.path.join(ROOT, "results", "realplayer_hpc" + ("_long" if a.set == "long" else ""))
    os.makedirs(out, exist_ok=True)
    f = os.path.join(out, f"run_{a.task:03d}.jsonl")
    if os.path.exists(f) and os.path.getsize(f) > 0:
        print("done already:", f)
        sys.exit(0)
    port = (9500 if a.set == "long" else 9000) + a.task
    cmd = [sys.executable, os.path.join(HERE, "testbed.py"), *args, *COMMON, "--tag", t, "--seed", str(s),
           "--port", str(port), "--out", f]
    print(" ".join(cmd), flush=True)
    sys.exit(subprocess.call(cmd))
