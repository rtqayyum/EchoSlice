"""Fourth review round (E26, E29-E33): per-cell summaries in the same metric as the rest of the paper.

  python diagnostics/round7/final_analysis_r7.py <root with results/E1..E33/merged.jsonl>

Writes, next to this script:
  r7_cells.csv     E29, E32, E33 and E26 rows in the 72 scenarios of the overall table (reference: the source exp)
  r7_tfactor.csv   E31 and E33: gaps against the template error factor
  r7_mismatch.csv  E30 and E33: the cell changes of E21, against E21's static grid (whole run, before, after, peak)
  r7_depart.csv    E30 and E33: share-dependent departures, against E23's static grid
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "round5"))
from experiments import campaign_report_r3 as R3   # noqa: E402
import final_analysis_r6 as R6                       # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/r7root"
R6.ROOT = ROOT
EVENT_T, T0, CH = R6.EVENT_T, R6.T0, R6.CH


def diag(exp):
    return R6.diag_of(exp).groupby(["cell", "slicer"]).mean(numeric_only=True).reset_index().drop(columns="seed")


def cells():
    out = []
    for e in ("E26", "E29", "E32", "E33", "E35"):
        if not R6.have(e):
            continue
        r = R6.ref_rows(e)
        r = r[r.exp.isin(["E1", "E6", "E7", "E12", "E15", "E17"])]
        r = r[~r.slicer.str.startswith("tf")]
        if e in ("E29", "E33", "E35"):
            r = r.merge(diag(e), on=["cell", "slicer"], how="left")
        out.append(r)
    return pd.concat(out, ignore_index=True)


def tfactor():
    out = []
    for e in ("E31", "E33", "E35"):
        if not R6.have(e):
            continue
        r = R6.ref_rows(e)
        r = r[r.slicer.str.startswith("tf")]
        out.append(r)
    tf = pd.concat(out, ignore_index=True)
    tf["factor"] = tf.slicer.str.extract(r"tf([0-9.]+)-")[0].astype(float)
    tf["variant"] = tf.slicer.str.extract(r"tf[0-9.]+-(.*)")[0]
    return tf


def mismatch():
    """Rows of E30/E33 in the E21 cells, scored against the E21 static grid, as R6.mismatch does for E21."""
    base = R3.rows_of(R6.path("E21"), keep_windows=True)
    G = base[base.grid]
    new = []
    for e in ("E30", "E33", "E35"):
        if R6.have(e):
            d = R3.rows_of(R6.path(e), keep_windows=True)
            new.append(d[d.cell.str.contains(":")])
    df = pd.concat([G] + new, ignore_index=True)
    ke = int(round((EVENT_T - T0) / CH))
    df["pre"] = [np.nanmean([w if w is not None else np.nan for w in v[:ke]]) for v in df.win]
    df["post"] = [np.nanmean([w if w is not None else np.nan for w in v[ke:]]) for v in df.win]
    rows = []
    for key, g in df.groupby("skey"):
        cell = g.cell.iloc[0]
        Gk = g[g.grid]
        if Gk.empty:
            continue
        orc, refwin = {}, {}
        for part in ("wm", "pre", "post"):
            piv = Gk.pivot_table(index="slicer", columns="seed", values=part)
            orc[part] = R3.loso(piv)
            if part == "post":
                seeds = list(piv.columns)
                for s in seeds:
                    others = [o for o in seeds if o != s] or seeds
                    best = piv[others].mean(axis=1).idxmax()
                    w = Gk[(Gk.slicer == best) & (Gk.seed == s)].win.iloc[0]
                    refwin[s] = np.array([x if x is not None else np.nan for x in w], float)
        for sl, h in g[~g.grid].groupby("slicer"):
            rec = dict(cell=cell, base=cell.split(":")[0], event=cell.split(":")[1], slicer=sl, seeds=len(h))
            for part in ("wm", "pre", "post"):
                gp = [100 * (orc[part][s] - v) / orc[part][s] for s, v in zip(h.seed, h[part]) if s in orc[part]]
                rec[part + "_gap"], rec[part + "_lo"], rec[part + "_hi"] = R3.boot(gp)
            gm = []
            for s, w in zip(h.seed, h.win):
                if s in refwin:
                    w = np.array([x if x is not None else np.nan for x in w], float)
                    gm.append(100 * (refwin[s][ke:] - w[ke:]) / refwin[s][ke:])
            gm = np.nanmean(np.array(gm), axis=0)
            roll = pd.Series(gm).rolling(3, min_periods=1).mean().values
            rec["transient"] = float(np.nanmax(roll[:5]))
            rows.append(rec)
    return pd.DataFrame(rows)


def depart():
    out = []
    for e in ("E30", "E33", "E35"):
        if not R6.have(e):
            continue
        r = R6.ref_rows(e)
        r = r[r.exp == "E23"]
        r = r.merge(diag(e), on=["cell", "slicer"], how="left")
        out.append(r)
    return pd.concat(out, ignore_index=True)


def main():
    for name, fn in (("r7_cells", cells), ("r7_tfactor", tfactor), ("r7_mismatch", mismatch), ("r7_depart", depart)):
        d = fn()
        d.to_csv(os.path.join(HERE, name + ".csv"), index=False)
        print(name, len(d))


if __name__ == "__main__":
    main()
