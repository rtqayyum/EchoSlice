"""Round-4 (review) per-cell summaries, in the same metric as diagnostics/round3/final_analysis.py.

  python diagnostics/round4/final_analysis_r4.py <root with results/E1..E19/merged.jsonl>

Writes, next to this script:
  r4_cells.csv     E15 rows (equally informed baselines in the main scenarios, gap against the reference
                   experiment's static grid) and E17 rows (held-out families, own static grid)
  r4_variants.csv  E16 rows (holds, random trial order, per-slice template errors) and E20 rows (session counts
                   from radio activity) in the ablation cells
  r4_conv.csv      E18 convergence table, r4_curves.csv per-minute curves
  r4_telemetry.csv E19 telemetry rows, plus the unimpaired E15 runs of the same slicers ('none')
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from experiments import campaign_report_r3 as R3   # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/r3root"


def path(e):
    return os.path.join(ROOT, "results", e, "merged.jsonl")


def per_slicer(g, orc):
    out = []
    for sl, h in g.groupby("slicer"):
        gd = {int(s): 100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h.wm) if s in orc and np.isfinite(v)}
        m, lo, hi = R3.boot(list(gd.values()))
        out.append(dict(slicer=sl, seeds=len(gd), gap=m, lo=lo, hi=hi, sla_min=h.sla_min.mean(), sla=h.sla.mean(),
                        gaps=json.dumps({str(k): round(v, 4) for k, v in sorted(gd.items())})))
    return out


def ref_rows(exp, key_col="skey"):
    if not os.path.exists(path(exp)):
        return pd.DataFrame()
    df = R3.rows_of(path(exp))
    rows = []
    for (cell, ref, key), g in df.groupby(["cell", "ref_exp", key_col]):
        orc, best = R3.oracle_for(ROOT, ref, key)
        if not orc:
            continue
        sc = json.loads(key)
        for imp, gi in g.groupby("impairment"):
            for r in per_slicer(gi, orc):
                rows.append(dict(exp=ref, src=exp, cell=cell, strict=bool(sc.get("strict", False)), skey=key,
                                 impairment=imp, **r))
    return pd.DataFrame(rows)


def own_grid(exp):
    if not os.path.exists(path(exp)):
        return pd.DataFrame()
    df = R3.rows_of(path(exp))
    rows = []
    for key, g in df[~df.grid].groupby("skey"):
        orc, best = R3.oracle_for(ROOT, exp, key)
        if not orc:
            continue
        sc = json.loads(key)
        for r in per_slicer(g, orc):
            rows.append(dict(exp=exp, src=exp, cell=g.cell.iloc[0], strict=bool(sc.get("strict", False)), skey=key,
                             best_static=best, **r))
    return pd.DataFrame(rows)


def convergence(exp):
    if not os.path.exists(path(exp)):
        return pd.DataFrame(), pd.DataFrame()
    T = os.path.join(HERE, "_tmp_tables")
    os.makedirs(T, exist_ok=True)
    S, R = {}, []
    import experiments.figures as F
    F.OUT = T
    R3.an_e14(path(exp), T, S, R, root=ROOT)
    t = pd.read_csv(os.path.join(T, "e14_convergence.csv"))
    c = pd.read_csv(os.path.join(T, "e14_curves.csv"))
    return t, c


def main():
    e15 = ref_rows("E15")
    e17 = own_grid("E17")
    pd.concat([e15, e17], ignore_index=True).to_csv(os.path.join(HERE, "r4_cells.csv"), index=False)
    pd.concat([ref_rows("E16"), ref_rows("E20")], ignore_index=True).to_csv(os.path.join(HERE, "r4_variants.csv"), index=False)
    t, c = convergence("E18")
    t.to_csv(os.path.join(HERE, "r4_conv.csv"), index=False)
    c.to_csv(os.path.join(HERE, "r4_curves.csv"), index=False)
    tel = ref_rows("E19", key_col="base_key")
    if not e15.empty and not tel.empty:
        cells = {"M1T": ("E7", "M1-video-heavy", True), "dayT": ("E7", "day_cycle", True),
                 "flashT": ("E7", "flash_crowd", True), "B3T": ("E1", "24v/8g/6b-dyn", True)}
        none = []
        for name, (ref, cell, strict) in cells.items():
            g = e15[(e15.exp == ref) & (e15.cell == cell) & (e15.strict == strict) & e15.slicer.isin(set(tel.slicer))]
            for _, r in g.iterrows():
                d = r.to_dict()
                d.update(cell=name, impairment="none")
                none.append(d)
        tel = pd.concat([tel, pd.DataFrame(none)], ignore_index=True)
    tel.to_csv(os.path.join(HERE, "r4_telemetry.csv"), index=False)
    for n in ("r4_cells", "r4_variants", "r4_conv", "r4_telemetry"):
        f = pd.read_csv(os.path.join(HERE, n + ".csv")) if os.path.getsize(os.path.join(HERE, n + ".csv")) > 1 else pd.DataFrame()
        print(n, len(f))


if __name__ == "__main__":
    main()
