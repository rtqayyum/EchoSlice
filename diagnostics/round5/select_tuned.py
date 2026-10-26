"""Pick the QoE feedback step/band and the gated variant's settle rule from the tuning runs (E27, seeds
101-104 only). The criterion is mean user QoE averaged over the scoring windows, over the six ablation cells.

  python diagnostics/round5/select_tuned.py <root>      writes diagnostics/round5/tuned.json and tuning.csv
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
root = sys.argv[1]
rows = []
for f in glob.glob(os.path.join(root, "results", "E27", "parts", "*.jsonl")):
    for line in open(f):
        r = json.loads(line)
        if r.get("error"):
            continue
        w = [x for x in (r.get("chunk_mos_user") or []) if x is not None]
        rows.append(dict(cell=r["job"]["cell"], tag=r["slicer_name"], seed=r["job"]["seed"],
                         wm=float(np.mean(w)) if w else np.nan, frozen=(r.get("slicer_diag") or {}).get("frozen_frac")))
df = pd.DataFrame(rows).drop_duplicates(["cell", "tag", "seed"])
t = df.groupby("tag").agg(n=("wm", "size"), wm=("wm", "mean"), frozen=("frozen", "mean")).reset_index()
t.to_csv(os.path.join(HERE, "tuning.csv"), index=False)
print(t.sort_values("wm", ascending=False).to_string(index=False))
fb = t[t.tag.str.startswith("fb-")].sort_values("wm", ascending=False).iloc[0].tag
gt = t[t.tag.str.startswith("gated-")].sort_values("wm", ascending=False).iloc[0].tag
s, b = fb[len("fb-s"):].split("-b")
m, tol = gt[len("gated-m"):].split("-t")
out = dict(fb_step=float(s), fb_band=float(b), gate_m=int(m), gate_tol=float(tol), fb_tag=fb, gate_tag=gt,
           n_runs=int(len(df)))
json.dump(out, open(os.path.join(HERE, "tuned.json"), "w"), indent=1)
print("chosen:", out)
