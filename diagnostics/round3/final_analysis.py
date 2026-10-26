"""Round-3 cross-experiment summary for the paper.

Reads results/<EXP>/merged.jsonl under ROOT (argv[1]) and writes
diagnostics/round3/final_cells.csv (one row per cell x mode x slicer) and prints the
cross-cell summaries quoted in the results section.

Gap = 100 (oracle - slicer) / oracle on window-averaged user MOS, paired by seed; the oracle
is the best static split of the same cell, chosen leave-one-seed-out (same as the report).
"""
import os
import sys
import json

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from experiments import campaign_report_r3 as R3   # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/r3root"
OUT = os.path.join(HERE, "final_cells.csv")

MAIN = ["echoslice3", "echoslice3-l1", "drl-loop", "drl-twin", "forecast+10%", "forecast+20%", "forecast+30%",
        "forecast+50%", "ol-qoe+10%", "ol-qoe+10%-sla1", "usage-prop", "echoslice-lite", "echoslice", "shared",
        "static-equal", "static"]


def cell_rows(exp):
    p = os.path.join(ROOT, "results", exp, "merged.jsonl")
    df = R3.rows_of(p)
    out = []
    for key, g in df[~df.grid].groupby("skey"):
        orc, best = R3.oracle_for(ROOT, exp, key)
        orcm, _ = R3.oracle_for(ROOT, exp, key, metric="mos")
        if not orc:
            continue
        sc = json.loads(key)
        cell = g.cell.iloc[0] if isinstance(g.cell.iloc[0], str) and g.cell.iloc[0] else ""
        if not cell:
            cell = sc.get("pattern") or f"{sc.get('n_video', 0)}v/{sc.get('n_game', 0)}g/{sc.get('n_bulk', 0)}b-{sc.get('abr', '')}"
        for sl, h in g.groupby("slicer"):
            gd = {int(s): 100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h.wm) if s in orc and np.isfinite(v)}
            gp = list(gd.values())
            m, lo, hi = R3.boot(gp)
            gq = [100 * (orcm[s] - v) / orcm[s] for s, v in zip(h.seed, h.mos) if s in orcm and np.isfinite(v)]
            out.append(dict(exp=exp, cell=cell, strict=bool(sc.get("strict", False)), slicer=sl, seeds=len(gp),
                            gap=m, lo=lo, hi=hi, gap_mos=float(np.mean(gq)) if gq else np.nan, sla_min=h.sla_min.mean(), sla=h.sla.mean(),
                            gaps=json.dumps({str(k): round(v, 4) for k, v in sorted(gd.items())}), best_static=best, skey=key))
    return pd.DataFrame(out)


def main():
    frames = []
    for e in ("E1", "E6", "E7", "E12"):
        print("loading", e, flush=True)
        frames.append(cell_rows(e))
    D = pd.concat(frames, ignore_index=True)
    D.to_csv(OUT, index=False)
    print("wrote", OUT, len(D))


if __name__ == "__main__":
    main()
