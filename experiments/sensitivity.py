"""E4: does the gate verdict depend on QoE-model choices?

Re-scores bulk flows offline from stored per-flow throughput with different
MOS saturation points (T_hi = 50, 100, 200 Mb/s), and compares P.1203 'pc'
with 'mobile' (separate runs). Reports each slicer's gap to the leave-one-
seed-out best static share under every variant.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import qoe  # noqa: E402

BULK = 1


def rows(path):
    out = []
    for line in open(path):
        r = json.loads(line)
        if r["job"].get("exp") != "E4" or "error" in r:
            continue
        j = r["job"]
        sc = j["scenario"]
        sl = j["slicer"]
        grid = sl["type"] == "static" and sl.get("x") is not None
        name = ("grid:" + ",".join(f"{v:.2f}" for v in sl["x"])) if grid else r["slicer_name"]
        ft = np.array(r["flow_type"])
        tp = np.array(r["flow_tput_mbps"]) * 1e6
        fm = np.array([np.nan if v is None else v for v in r["flow_mos"]], dtype=float)
        for thi in (50e6, 100e6, 200e6):
            m = fm.copy()
            m[ft == BULK] = qoe.bulk_mos(tp[ft == BULK], t_hi=thi)
            out.append(dict(cell=f"{sc['n_video']}v/{sc['n_game']}g/{sc['n_bulk']}b {sc['abr']}", device=sc.get("device", "pc"),
                            thi=int(thi / 1e6), slicer=name, grid=grid, seed=j["seed"], mos=np.nanmean(m)))
    return pd.DataFrame(out)


def gaps(df):
    res = []
    for (cell, dev, thi), g in df.groupby(["cell", "device", "thi"]):
        piv = g[g.grid].pivot_table(index="slicer", columns="seed", values="mos")
        seeds = list(piv.columns)
        orc = np.mean([piv.loc[piv[[o for o in seeds if o != s]].mean(axis=1).idxmax(), s] for s in seeds])
        for sl, h in g[~g.grid].groupby("slicer"):
            res.append(dict(cell=cell, device=dev, bulk_T_hi=thi, slicer=sl, gap_pct=100 * (orc - h.mos.mean()) / orc))
    return pd.DataFrame(res)


if __name__ == "__main__":
    df = rows(sys.argv[1])
    g = gaps(df)
    pd.set_option("display.width", 200)
    t = g.pivot_table(index=["cell", "slicer"], columns=["device", "bulk_T_hi"], values="gap_pct").round(2)
    print(t.to_string())
    t.to_csv(sys.argv[1].replace(".jsonl", "_sensitivity.csv"))
