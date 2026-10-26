"""Pick the bulk floor and the BO exploration weight from the tuning runs (E28, seeds 101-104 only).
Criterion: mean user QoE averaged over the scoring windows. Bulk floor: over the six ablation cells and the
four departure cells. BO weight: over the six ablation cells.

  python diagnostics/round6/select_tuned6.py <root>     writes diagnostics/round6/tuned.json and tuning.csv
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
for f in glob.glob(os.path.join(root, "results", "E28", "parts", "*.jsonl")):
    for line in open(f):
        r = json.loads(line)
        if r.get("error"):
            continue
        w = [x for x in (r.get("chunk_mos_user") or []) if x is not None]
        rows.append(dict(cell=r["job"]["cell"], tag=r["slicer_name"], seed=r["job"]["seed"],
                         wm=float(np.mean(w)) if w else np.nan))
df = pd.DataFrame(rows).drop_duplicates(["cell", "tag", "seed"])
t = df.groupby("tag").agg(n=("wm", "size"), wm=("wm", "mean")).reset_index()
t.to_csv(os.path.join(HERE, "tuning.csv"), index=False)
print(t.sort_values("wm", ascending=False).to_string(index=False))
bf = t[t.tag.str.startswith("bf")].sort_values("wm", ascending=False).iloc[0].tag
bo = t[t.tag.str.startswith("bo-b")].sort_values("wm", ascending=False).iloc[0].tag
out = dict(bulk_rate=float(bf[2:]) * 1e6, bo_beta=float(bo[4:]), bf_tag=bf, bo_tag=bo, n_runs=int(len(df)))
json.dump(out, open(os.path.join(HERE, "tuned.json"), "w"), indent=1)
print("chosen:", out)
