"""Pick the count-proportional bulk floor from the tuning runs (E34, seeds 101-104 only).
Criterion: mean user QoE averaged over the scoring windows, over the six ablation cells and the four
departure cells (the same cells and criterion as the absolute floor of round 6).

  python diagnostics/round7/select_tuned7.py <root>     writes diagnostics/round7/tuned.json and tuning.csv
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
for f in glob.glob(os.path.join(root, "results", "E34", "parts", "*.jsonl")):
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
best = t[t.tag.str.startswith("bfrac")].sort_values("wm", ascending=False).iloc[0].tag
out = dict(bulk_frac=float(best[5:]), tag=best, n_runs=int(len(df)))
json.dump(out, open(os.path.join(HERE, "tuned.json"), "w"), indent=1)
print("chosen:", out)
