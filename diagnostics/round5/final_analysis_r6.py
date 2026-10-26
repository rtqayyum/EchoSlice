"""Final review round (E21-E26): per-cell summaries in the same metric as the rest of the paper.

  python diagnostics/round5/final_analysis_r6.py <root with results/E1..E26/merged.jsonl>

Writes, next to this script:
  r6_mismatch.csv   E21: whole-run, pre-event and post-event gaps, transient harm, recovery time, QoE lost
  r6_curves.csv     E21: per-minute gap after the event (mean over seeds)
  r6_counts.csv     E22: gaps of the count estimators and their count error against the true session count
  r6_depart.csv     E23: gaps with share-dependent departures (abandonment, finite files)
  r6_tfactor.csv    E24: gaps against the template error factor
  r6_cells.csv      E25 and E26: gated variant, QoE feedback and extra PPO seeds in the scenarios of Table V
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
EVENT_T, T0, CH = 900.0, 300.0, 60.0


def path(e):
    return os.path.join(ROOT, "results", e, "merged.jsonl")


def have(e):
    return os.path.exists(path(e))


def per_slicer(g, orc):
    out = []
    for sl, h in g.groupby("slicer"):
        gd = {int(s): 100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h.wm) if s in orc and np.isfinite(v)}
        m, lo, hi = R3.boot(list(gd.values()))
        out.append(dict(slicer=sl, seeds=len(gd), gap=m, lo=lo, hi=hi, sla_min=h.sla_min.mean(), sla=h.sla.mean(),
                        gaps=json.dumps({str(k): round(v, 4) for k, v in sorted(gd.items())})))
    return out


def own_grid(exp, extra_cols=()):
    if not have(exp):
        return pd.DataFrame()
    df = R3.rows_of(path(exp))
    rows = []
    for key, g in df.groupby("skey"):
        orc, best = R3.oracle_for(ROOT, exp, key)
        if not orc:
            continue
        cell = g.cell.iloc[0]
        for r in per_slicer(g[~g.grid], orc):
            rows.append(dict(exp=exp, cell=cell, skey=key, best_static=best, **r))
    return pd.DataFrame(rows)


def ref_rows(exp):
    if not have(exp):
        return pd.DataFrame()
    df = R3.rows_of(path(exp))
    rows = []
    for (cell, ref, key), g in df.groupby(["cell", "ref_exp", "skey"]):
        orc, best = R3.oracle_for(ROOT, ref, key)
        if not orc:
            continue
        sc = json.loads(key)
        for r in per_slicer(g, orc):
            rows.append(dict(exp=ref, src=exp, cell=cell, strict=bool(sc.get("strict", False)), skey=key, **r))
    return pd.DataFrame(rows)


def diag_of(exp):
    """slicer_diag per run (count errors, frozen fraction), plus abandonment and finished files."""
    out = []
    for line in open(path(exp)):
        r = json.loads(line)
        if r.get("error"):
            continue
        d = r.get("slicer_diag") or {}
        out.append(dict(cell=r["job"]["cell"], slicer=r["slicer_name"], seed=r["job"]["seed"],
                        err_mean=(d.get("count_rel_err_mean") or [np.nan])[0],
                        err_abs=(d.get("count_rel_err_abs") or [np.nan])[0],
                        err_p10=(d.get("count_rel_err_p10") or [np.nan])[0],
                        frozen=d.get("frozen_frac", np.nan), reopen=d.get("n_reopen", np.nan),
                        moves=d.get("n_moves", np.nan), abandoned=r.get("n_abandoned", np.nan),
                        files=r.get("files_done", np.nan)))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- E21: the prior turns wrong during a run
def mismatch():
    if not have("E21"):
        return pd.DataFrame(), pd.DataFrame()
    df = R3.rows_of(path("E21"), keep_windows=True)
    ke = int(round((EVENT_T - T0) / CH))
    df["pre"] = [np.nanmean([w if w is not None else np.nan for w in v[:ke]]) for v in df.win]
    df["post"] = [np.nanmean([w if w is not None else np.nan for w in v[ke:]]) for v in df.win]
    rows, curves = [], []
    for key, g in df.groupby("skey"):
        cell = g.cell.iloc[0]
        G = g[g.grid]
        orc = {}
        refwin = {}
        for part in ("wm", "pre", "post"):
            piv = G.pivot_table(index="slicer", columns="seed", values=part)
            orc[part] = R3.loso(piv)
            if part == "post":
                seeds = list(piv.columns)
                for s in seeds:
                    others = [o for o in seeds if o != s] or seeds
                    best = piv[others].mean(axis=1).idxmax()
                    w = G[(G.slicer == best) & (G.seed == s)].win.iloc[0]
                    refwin[s] = np.array([x if x is not None else np.nan for x in w], float)
        for sl, h in g[~g.grid].groupby("slicer"):
            rec = dict(cell=cell, base=cell.split(":")[0], event=cell.split(":")[1], slicer=sl, seeds=len(h))
            for part in ("wm", "pre", "post"):
                gp = [100 * (orc[part][s] - v) / orc[part][s] for s, v in zip(h.seed, h[part]) if s in orc[part]]
                rec[part + "_gap"], rec[part + "_lo"], rec[part + "_hi"] = R3.boot(gp)
            gm = []
            lost = []
            for s, w in zip(h.seed, h.win):
                if s not in refwin:
                    continue
                w = np.array([x if x is not None else np.nan for x in w], float)
                r = refwin[s]
                gm.append(100 * (r[ke:] - w[ke:]) / r[ke:])
                lost.append(np.nansum(r[ke:] - w[ke:]))           # MOS-minutes lost per user after the event
            gm = np.nanmean(np.array(gm), axis=0)
            roll = pd.Series(gm).rolling(3, min_periods=1).mean().values
            rec["transient"] = float(np.nanmax(roll[:5]))
            ok = np.where(roll <= 1.0)[0]
            rec["recover_min"] = next((int(i) + 1 for i in range(len(roll)) if (roll[i:] <= 1.0).all()), np.nan)
            rec["mos_min_lost"] = float(np.mean(lost))
            rows.append(rec)
            for i, v in enumerate(gm):
                curves.append(dict(cell=cell, slicer=sl, minute=i + 1, gap=float(v)))
    return pd.DataFrame(rows), pd.DataFrame(curves)


def main():
    t, c = mismatch()
    t.to_csv(os.path.join(HERE, "r6_mismatch.csv"), index=False)
    c.to_csv(os.path.join(HERE, "r6_curves.csv"), index=False)
    for exp, name in (("E22", "r6_counts"), ("E23", "r6_depart")):
        g = own_grid(exp)
        if not g.empty:
            d = diag_of(exp).groupby(["cell", "slicer"]).mean(numeric_only=True).reset_index().drop(columns="seed")
            g = g.merge(d, on=["cell", "slicer"], how="left")
        g.to_csv(os.path.join(HERE, name + ".csv"), index=False)
    tf = ref_rows("E24")
    if not tf.empty:
        d = diag_of("E24").groupby(["cell", "slicer"]).mean(numeric_only=True).reset_index().drop(columns="seed")
        tf = tf.merge(d, on=["cell", "slicer"], how="left")
        tf["factor"] = tf.slicer.str.extract(r"tf([0-9.]+)-")[0].astype(float)
        tf["variant"] = tf.slicer.str.extract(r"tf[0-9.]+-(.*)")[0]
    tf.to_csv(os.path.join(HERE, "r6_tfactor.csv"), index=False)
    cells = pd.concat([ref_rows("E25"), ref_rows("E26")], ignore_index=True)
    if not cells.empty:
        d = pd.concat([diag_of(e) for e in ("E25",) if have(e)], ignore_index=True)
        if not d.empty:
            fz = d.groupby("slicer").frozen.mean().to_dict()
            cells["frozen_mean"] = cells.slicer.map(fz)
    cells.to_csv(os.path.join(HERE, "r6_cells.csv"), index=False)
    for n in ("r6_mismatch", "r6_counts", "r6_depart", "r6_tfactor", "r6_cells"):
        p = os.path.join(HERE, n + ".csv")
        print(n, len(pd.read_csv(p)) if os.path.getsize(p) > 2 else 0)


if __name__ == "__main__":
    main()
