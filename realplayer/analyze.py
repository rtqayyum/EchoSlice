"""Summarise the real-player runs: gap to the best static video share (chosen leave-one-seed-out on the grid),
video share, served rates, video MOS, stalls and bulk MOS. Writes results/summary.csv and a figure."""
import glob
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
SUB = sys.argv[1] if len(sys.argv) > 1 else "results"
R = []
for f in glob.glob(os.path.join(HERE, SUB, "*.jsonl")):
    for l in open(f):
        R.append(json.loads(l))
df = pd.DataFrame([dict(tag=r["tag"], seed=r["seed"], mos=r["mos_user"], mos_v=np.mean(r["mos_video"]),
                        mos_b=np.mean(r["mos_bulk"]), share=r["share_video_mean"], v_mbps=r["served_video_mbps"],
                        b_mbps=r["served_bulk_mbps"],
                        stall_s=np.mean([d.get("stall_s", 0) for d in r["video_detail"]]),
                        vbr=np.mean([d.get("mean_mbps", np.nan) for d in r["video_detail"]]),
                        min_v=np.min(r["mos_video"])) for r in R]).drop_duplicates(["tag", "seed"], keep="last")
grid = df[df.tag.str.startswith("static-")]
piv = grid.pivot_table(index="tag", columns="seed", values="mos")
ref = {}
for s in piv.columns:
    others = [o for o in piv.columns if o != s] or list(piv.columns)
    ref[s] = float(piv.loc[piv[others].mean(axis=1).idxmax(), s])
best = piv.mean(axis=1).idxmax()
df["gap"] = [100 * (ref[s] - m) / ref[s] if s in ref else np.nan for s, m in zip(df.seed, df.mos)]
order = [f"static-0.{i}" for i in range(3, 10)] + ["usage", "forecast+10%", "forecast+30%", "prior", "echoslice",
                                                    "echoslice-h36", "prior-rho0.5", "echoslice-rho0.5", "echoslice-h36-rho0.5"]
t = df.groupby("tag").agg(n=("mos", "size"), gap=("gap", "mean"), gap_max=("gap", "max"), mos=("mos", "mean"),
                          mos_v=("mos_v", "mean"), min_v=("min_v", "mean"), mos_b=("mos_b", "mean"),
                          share=("share", "mean"), v_mbps=("v_mbps", "mean"), b_mbps=("b_mbps", "mean"),
                          vbr=("vbr", "mean"), stall_s=("stall_s", "mean"))
t = t.reindex([o for o in order if o in t.index])
t.to_csv(os.path.join(HERE, SUB, "summary.csv"))
print("best static:", best)
print(t.round(3).to_string())
