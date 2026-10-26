"""Gate analysis: price of ignoring reactions, per scenario cell and overall."""
import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

DYN_ORDER = ["usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "shared", "static"]


def load(path):
    rows = []
    for line in open(path):
        r = json.loads(line)
        if "error" in r:
            print("ERROR in", r["job"], r["error"][-300:])
            continue
        j = r["job"]
        sc = j["scenario"]
        cell = (sc.get("n_video", 24), sc.get("n_game", 0), sc.get("n_bulk", 4), sc.get("abr", "tput"),
                bool(sc.get("strict", False)), sc.get("seg_dur", 4.0), sc.get("Ts", 1.0))
        sl = j["slicer"]
        is_grid = sl["type"] == "static" and sl.get("x") is not None
        row = dict(exp=j.get("exp", ""), device=sc.get("device", "pc"), cell=cell + (sc.get("device", "pc"),), n_video=cell[0], n_game=cell[1], n_bulk=cell[2], abr=cell[3], strict=cell[4],
                   seg_dur=cell[5], Ts=cell[6], seed=j["seed"],
                   slicer=("grid:" + ",".join(f"{v:.2f}" for v in sl["x"])) if is_grid else r["slicer_name"],
                   is_grid=is_grid, mos_user=r["mos_user"], mos_slice_avg=r["mos_slice_avg"])
        for k, v in r["mos_slice"].items():
            row["mos_" + k] = v
        for k in ("stall_ratio", "switches_pm", "bitrate_mbps", "game_rate", "game_late", "game_rtt_ms", "bulk_mbps",
                  "cell_tput_mbps"):
            row[k] = r.get(k, np.nan)
        sm = r["share_mean"]
        ss = r["share_std"]
        for i, nm in enumerate(r["names"]):
            row["x_" + nm] = sm[i]
            row["xsd_" + nm] = ss[i]
        rows.append(row)
    return pd.DataFrame(rows)


def oracle_loso(g, metric):
    """Leave-one-seed-out best static share: choose x on the other seeds,
    score it on the held-out seed. Removes the winner's-curse bias."""
    grid = g[g.is_grid]
    seeds = sorted(grid.seed.unique())
    piv = grid.pivot_table(index="slicer", columns="seed", values=metric)
    if len(seeds) < 2:
        best = piv.mean(axis=1).idxmax()
        return piv.loc[best].mean(), best
    vals = []
    picks = []
    for s in seeds:
        others = [o for o in seeds if o != s]
        b = piv[others].mean(axis=1).idxmax()
        vals.append(piv.loc[b, s])
        picks.append(b)
    best_all = piv.mean(axis=1).idxmax()
    return float(np.mean(vals)), best_all


def cell_table(df, metric="mos_user"):
    out = []
    for cell, g in df.groupby("cell"):
        if not g.is_grid.any():
            continue
        orc, best = oracle_loso(g, metric)
        slice_cols = [c for c in g.columns if c.startswith("mos_") and c not in ("mos_user", "mos_slice_avg")
                      and g[c].notna().any()]
        grid_means = g[g.is_grid].groupby("slicer")[slice_cols].mean()
        for sl, h in g[~g.is_grid].groupby("slicer"):
            m = h[metric].mean()
            d = h[slice_cols].mean()
            # weight-free Pareto check against every static grid point
            margin = (grid_means - d).min(axis=1)       # >0: that static share beats it on every slice
            dom = float(margin.max())
            out.append(dict(n_video=cell[0], n_game=cell[1], n_bulk=cell[2], abr=cell[3], strict=cell[4], device=cell[7],
                            seg_dur=cell[5], Ts=cell[6], slicer=sl, mos=m, oracle=orc, oracle_x=best,
                            gap_pct=100 * (orc - m) / orc, gap_mos=orc - m,
                            gap_pct_above1=100 * (orc - m) / (orc - 1),
                            pareto_margin=dom, n=len(h),
                            **{c: d[c] for c in slice_cols},
                            **{c: h[c].mean() for c in h.columns if c.startswith("x_") or c.startswith("xsd_")},
                            switches_pm=h.switches_pm.mean(), stall_ratio=h.stall_ratio.mean(),
                            game_late=h.game_late.mean(), bulk_mbps=h.bulk_mbps.mean(), bitrate=h.bitrate_mbps.mean()))
    return pd.DataFrame(out)


def summary(ct):
    rows = []
    for sl, g in ct.groupby("slicer"):
        rows.append(dict(slicer=sl, cells=len(g), mean_gap_pct=g.gap_pct.mean(), median_gap_pct=g.gap_pct.median(),
                         worst_gap_pct=g.gap_pct.max(), share_cells_gap_ge5=(g.gap_pct >= 5).mean(),
                         share_pareto_dominated=(g.pareto_margin > 0.05).mean()))
    return pd.DataFrame(rows).sort_values("mean_gap_pct")


if __name__ == "__main__":
    df = load(sys.argv[1])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.max_rows", 500)
    for metric in ("mos_user", "mos_slice_avg"):
        ct = cell_table(df, metric)
        print(f"\n===== metric: {metric} =====")
        print(summary(ct).round(3).to_string(index=False))
        for keys, g in ct.groupby(["strict", "n_game"]):
            print(f"\n-- strict={keys[0]} n_game={keys[1]}")
            print(summary(g).round(3).to_string(index=False))
    ct = cell_table(df, "mos_user")
    cols = ["n_video", "n_game", "n_bulk", "abr", "strict", "slicer", "mos", "oracle", "gap_pct", "pareto_margin"] + \
           [c for c in ct.columns if c.startswith("mos_")] + [c for c in ct.columns if c.startswith("x_")]
    print(ct[cols].round(3).to_string(index=False))
    ct.to_csv(sys.argv[1].replace(".jsonl", "_cells.csv"), index=False)
