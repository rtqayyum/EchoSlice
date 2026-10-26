"""Merge, analyse and report the HPC campaign.

Outputs (all under the project root):
  results/<EXP>/merged.jsonl            successful runs, one per job
  results/tables/*.csv                  analysis tables
  figures/*.png                         figures
  results/campaign_summary.json         machine-readable summary
  reports/CAMPAIGN_REPORT.md            human-readable report
Exit code 0 only when every requested experiment is complete with no errors
and every analysis step ran.
"""
import json
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from experiments import campaign as C            # noqa: E402
from experiments import campaign_jobs as CJ      # noqa: E402
from experiments.analyze import load             # noqa: E402

ORDER = ["usage-prop", "forecast+10%", "forecast+20%", "forecast+30%", "forecast+50%", "ol-qoe+10%",
         "ol-qoe+10%-sla0.5", "ol-qoe+10%-sla1", "ol-qoe+10%-sla2", "drl-twin", "drl-twin-l1", "drl-loop", "drl-loop-l1",
         "echoslice-lite", "echoslice", "echoslice3", "echoslice3-l0.5", "echoslice3-l1", "echoslice3-l2",
         "static", "shared"]
LABEL = {"usage-prop": "Usage-proportional", "forecast+20%": "Forecast + 20%", "ol-qoe+10%": "Open-loop QoE",
         "forecast+10%": "Forecast + 10%", "forecast+30%": "Forecast + 30%", "forecast+50%": "Forecast + 50%",
         "ol-qoe+10%-sla0.5": "Open-loop QoE + SLA (0.5)", "ol-qoe+10%-sla1": "Open-loop QoE + SLA (1)",
         "ol-qoe+10%-sla2": "Open-loop QoE + SLA (2)",
         "drl-twin": "DRL, replay-trained", "drl-twin-l1": "DRL, replay-trained, SLA (1)",
         "drl-loop": "DRL, loop-trained", "drl-loop-l1": "DRL, loop-trained, SLA (1)",
         "echoslice-lite": "EchoSlice-lite", "echoslice": "EchoSlice (v2)", "echoslice3": "EchoSlice (v3)",
         "echoslice3-l0.5": "EchoSlice (v3), SLA (0.5)", "echoslice3-l1": "EchoSlice (v3), SLA (1)",
         "echoslice3-l2": "EchoSlice (v3), SLA (2)",
         "static": "Static equal", "shared": "No slicing (PF)", "deploy-static": "Static tuned at deploy"}


def boot_ci(v, B=2000, seed=0):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (float(np.mean(v)) if len(v) else np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    bs = rng.choice(v, (B, len(v)), replace=True).mean(axis=1)
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def merge(root, exp):
    d = C.exp_dir(root, exp)
    jobs = json.load(open(os.path.join(d, "jobs.json")))
    want = {C.key(j) for j in jobs}
    best = {}
    import glob
    for f in sorted(glob.glob(os.path.join(d, "parts", "*.jsonl"))):
        for line in open(f):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = C.key(r["job"])
            if k in want and "error" not in r:
                best[k] = line if line.endswith("\n") else line + "\n"
    out = os.path.join(d, "merged.jsonl")
    with open(out, "w") as f:
        f.writelines(best.values())
    return out, len(best), len(jobs)


def seed_gaps(df, metric="mos_user"):
    """Per cell and slicer: paired per-seed gap to the leave-one-seed-out best
    static share, mean and bootstrap 95% CI over seeds."""
    rows = []
    for cell, g in df.groupby("cell"):
        grid = g[g.is_grid]
        if grid.empty:
            continue
        piv = grid.pivot_table(index="slicer", columns="seed", values=metric)
        seeds = list(piv.columns)
        orc = {}
        for s in seeds:
            others = [o for o in seeds if o != s] or seeds
            orc[s] = piv.loc[piv[others].mean(axis=1).idxmax(), s]
        best_all = piv.mean(axis=1).idxmax()
        slice_cols = [c for c in g.columns if c.startswith("mos_") and c not in ("mos_user", "mos_slice_avg") and g[c].notna().any()]
        for sl, h in g[~g.is_grid].groupby("slicer"):
            gp = [100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h[metric]) if s in orc]
            m, lo, hi = boot_ci(gp)
            rows.append(dict(n_video=cell[0], n_game=cell[1], n_bulk=cell[2], abr=cell[3], strict=cell[4], seg_dur=cell[5],
                             Ts=cell[6], device=cell[7], slicer=sl, seeds=len(gp), gap_pct=m, gap_lo=lo, gap_hi=hi,
                             mos=h[metric].mean(), oracle=float(np.mean(list(orc.values()))), oracle_x=best_all,
                             **{c: h[c].mean() for c in slice_cols},
                             **{c: h[c].mean() for c in h.columns if c.startswith("x_") or c.startswith("xsd_")},
                             game_late=h.game_late.mean(), switches_pm=h.switches_pm.mean(), stall_ratio=h.stall_ratio.mean(),
                             bulk_mbps=h.bulk_mbps.mean(), bitrate=h.bitrate_mbps.mean()))
    return pd.DataFrame(rows)


def family(r):
    return ("3-slice" if r.n_game > 0 else "2-slice") + (" strict" if r.strict else " shareable")


def fam_summary(ct):
    rows = []
    for (fam, sl), g in ct.groupby(["family", "slicer"]):
        rows.append(dict(family=fam, slicer=sl, cells=len(g), mean_gap_pct=g.gap_pct.mean(), worst_gap_pct=g.gap_pct.max(),
                         cells_gap_ge5=int((g.gap_pct >= 5).sum()), cells_ci_above5=int((g.gap_lo >= 5).sum()),
                         mos_video=g.get("mos_video", pd.Series(dtype=float)).mean(),
                         mos_game=g.get("mos_game", pd.Series(dtype=float)).mean(),
                         mos_bulk=g.get("mos_bulk", pd.Series(dtype=float)).mean()))
    t = pd.DataFrame(rows)
    t["o"] = t.slicer.map({s: i for i, s in enumerate(ORDER)})
    return t.sort_values(["family", "o"]).drop(columns="o")


def md_table(df, cols, fmt=None):
    fmt = fmt or {}
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(fmt.get(c, "{:.2f}").format(v) if np.isfinite(v) else "")
            else:
                cells.append(str(LABEL.get(v, v)))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------- per experiment
def an_e1(path, T, S, R):
    df = load(path)
    ct = seed_gaps(df)
    ct["family"] = ct.apply(family, axis=1)
    ct.to_csv(os.path.join(T, "e1_cells.csv"), index=False)
    fs = fam_summary(ct)
    fs.to_csv(os.path.join(T, "e1_family_summary.csv"), index=False)
    S["E1"] = {"family_summary": fs.round(4).to_dict("records")}
    R.append("## E1. Effect size\n")
    R.append("Gap = loss in mean user MOS against the best static share (leave-one-seed-out, paired by seed), slicer period 1 s.\n")
    R.append(md_table(fs, ["family", "slicer", "cells", "mean_gap_pct", "worst_gap_pct", "cells_gap_ge5", "cells_ci_above5",
                           "mos_video", "mos_game", "mos_bulk"]))
    R.append("\n![gap](../figures/fig_gap.png)\n")
    import experiments.figures as F
    F.fig_gap(os.path.join(T, "e1_cells.csv"))
    try:
        F.fig_pareto(path)
        R.append("![pareto](../figures/fig_pareto.png)\n")
    except Exception as e:
        R.append(f"(Pareto figure skipped: {e})\n")


def an_e2(path, T, S, R):
    df = load(path)
    d = df[~df.is_grid]
    cols = ["mos_user", "mos_video", "mos_game", "mos_bulk", "xsd_video", "xsd_game", "switches_pm"]
    t = d.groupby(["abr", "seg_dur", "slicer", "Ts"])[cols].mean().reset_index()
    t.to_csv(os.path.join(T, "e2_period.csv"), index=False)
    piv = t.pivot_table(index=["slicer", "seg_dur"], columns="Ts", values="xsd_video").round(3)
    piv2 = t.pivot_table(index=["slicer", "seg_dur"], columns="Ts", values="mos_user").round(3)
    S["E2"] = {"share_std_video": {str(k): v for k, v in piv.to_dict("index").items()},
               "mos_user": {str(k): v for k, v in piv2.to_dict("index").items()}}
    R.append("## E2. Slicer period\n")
    R.append("Standard deviation of the video-slice share, by slicer period (columns, s), mean over ABR rules:\n")
    R.append(piv.reset_index().to_markdown(index=False))
    R.append("\nMean user MOS:\n")
    R.append(piv2.reset_index().to_markdown(index=False))
    import experiments.figures as F
    F.fig_resonance(path)
    R.append("\n![resonance](../figures/fig_resonance.png)\n")


def an_e4(path, T, S, R):
    from experiments import sensitivity as SE
    g = SE.gaps(SE.rows(path))
    t = g.pivot_table(index=["cell", "slicer"], columns=["device", "bulk_T_hi"], values="gap_pct").round(2)
    t.columns = [f"{d} / {h} Mb/s" for d, h in t.columns]
    t.to_csv(os.path.join(T, "e4_sensitivity.csv"))
    S["E4"] = {"gap_pct": {str(k): {str(c): v for c, v in row.items()} for k, row in t.to_dict("index").items()}}
    R.append("## E4. QoE-model sensitivity\n")
    R.append("Gap (%) by P.1203 device / bulk-MOS saturation point:\n")
    R.append(t.reset_index().to_markdown(index=False))


def an_e5(path, T, S, R):
    df = load(path)
    df = df[df.slicer.str.startswith("forecast+")].copy()
    df["h"] = df.slicer.str.extract(r"forecast\+(\d+(?:\.\d+)?)%").astype(float)[0] / 100
    df["fam"] = np.where(df.n_game > 0, "3-slice", "2-slice") + np.where(df.strict, " strict", " shareable")
    cols = [c for c in ("mos_user", "mos_video", "mos_game", "mos_bulk", "x_video", "x_game", "bulk_mbps") if c in df]
    t = df.groupby(["fam", "h"])[cols].mean().reset_index()
    t.to_csv(os.path.join(T, "e5_headroom.csv"), index=False)
    S["E5"] = {"table": t.round(4).to_dict("records")}
    R.append("## E5. Forecast headroom\n")
    R.append(t.round(3).to_markdown(index=False))
    import experiments.figures as F
    F.fig_headroom(path)
    R.append("\n![headroom](../figures/fig_headroom.png)\n")


def an_e6(path, T, S, R):
    raw = [json.loads(l) for l in open(path)]
    rows = []
    for r in raw:
        j = r["job"]
        sl = j["slicer"]
        grid = sl["type"] == "static" and sl.get("x") is not None
        name = ("grid:" + ",".join(f"{v:.2f}" for v in sl["x"])) if grid else r["slicer_name"]
        pat = j["scenario"].get("pattern") or j.get("pattern_of")
        rows.append(dict(role=j.get("role", "dynamic"), pattern=pat, strict=bool(j["scenario"].get("strict", False)),
                         slicer=name, grid=grid, seed=j["seed"], mos=r["mos_user"],
                         **{f"mos_{k}": v for k, v in r["mos_slice"].items()},
                         chunk_slice=r.get("chunk_slice_mos"), chunk_x=r.get("chunk_share_mean")))
    df = pd.DataFrame(rows)
    out = []
    surge = []
    for (pat, strict), g in df.groupby(["pattern", "strict"]):
        dyn = g[g.role == "dynamic"]
        pa = g[g.role == "phaseA"]
        piv = dyn[dyn.grid].pivot_table(index="slicer", columns="seed", values="mos")
        if piv.empty:
            continue
        seeds = list(piv.columns)
        orc = {}
        for s in seeds:
            others = [o for o in seeds if o != s] or seeds
            orc[s] = piv.loc[piv[others].mean(axis=1).idxmax(), s]
        entries = {sl: h for sl, h in dyn[~dyn.grid].groupby("slicer")}
        if not pa.empty:
            dep = pa.groupby("slicer").mos.mean().idxmax()          # what an operator would tune before the change
            if dep in piv.index:
                entries["deploy-static"] = dyn[dyn.slicer == dep]
        for sl, h in entries.items():
            gp = [100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h.mos) if s in orc]
            m, lo, hi = boot_ci(gp)
            rec = dict(pattern=pat, strict=strict, slicer=sl, seeds=len(gp), gap_pct=m, gap_lo=lo, gap_hi=hi, mos=h.mos.mean(),
                       oracle=float(np.mean(list(orc.values()))), oracle_x=piv.mean(axis=1).idxmax(),
                       deploy_x=(dep if not pa.empty else None))
            for c in ("mos_video", "mos_game", "mos_bulk"):
                if c in h:
                    rec[c] = h[c].mean()
            out.append(rec)
            # per-window MOS of each slice (e.g. the gaming surge window)
            cs = [x for x in h.chunk_slice if x]
            if cs:
                for ci in range(len(cs[0])):
                    for nm in cs[0][ci]:
                        vals = [x[ci][nm] for x in cs if x[ci][nm] is not None]
                        if vals:
                            surge.append(dict(pattern=pat, strict=strict, slicer=sl, window=ci, slice=nm, mos=float(np.mean(vals))))
    t = pd.DataFrame(out)
    t.to_csv(os.path.join(T, "e6_dynamic_gaps.csv"), index=False)
    w = pd.DataFrame(surge)
    w.to_csv(os.path.join(T, "e6_window_slice_mos.csv"), index=False)
    S["E6"] = {"gaps": t.round(4).to_dict("records")}
    R.append("## E6. Dynamic load\n")
    R.append("Gap (%) against the best static share over the whole 1200 s run (leave-one-seed-out). "
             "'Static tuned at deploy' is the best static share for the load before the change, kept through it.\n")
    t2 = t.copy()
    t2["o"] = t2.slicer.map({s: i for i, s in enumerate(ORDER + ["deploy-static"])})
    t2 = t2.sort_values(["pattern", "strict", "o"])
    R.append(md_table(t2, ["pattern", "strict", "slicer", "seeds", "gap_pct", "gap_lo", "gap_hi", "mos_video", "mos_game", "mos_bulk"]))
    import experiments.figures as F
    if hasattr(F, "fig_dynload"):
        F.fig_dynload(t, w)
        R.append("\n![dynamic load](../figures/fig_dynload.png)\n")


SLA_TARGET = {0: 4.0, 2: 4.0, 1: 3.0}          # video MOS >= 4, gaming MOS >= 4, bulk MOS >= 3 (about 10 Mb/s)


def _wmean(v):
    v = [x for x in (v or []) if x is not None]
    return float(np.mean(v)) if v else np.nan


def _sla(r):
    """Share of (user, window) pairs meeting the slice target, overall and per slice type."""
    cm, ft = r.get("chunk_flow_mos"), r.get("flow_type")
    if not cm or ft is None:
        return np.nan, {}
    hit, tot = {0: 0, 1: 0, 2: 0}, {0: 0, 1: 0, 2: 0}
    for i, row in enumerate(cm):
        for v in row:
            if v is None:
                continue
            tot[ft[i]] += 1
            hit[ft[i]] += v >= SLA_TARGET[ft[i]]
    per = {k: hit[k] / tot[k] for k in tot if tot[k]}
    return (sum(hit.values()) / max(sum(tot.values()), 1)), per


def _loso(piv):
    seeds = list(piv.columns)
    out = {}
    for s in seeds:
        others = [o for o in seeds if o != s] or seeds
        out[s] = piv.loc[piv[others].mean(axis=1).idxmax(), s]
    return out


def an_e7(path, T, S, R):
    rows = []
    for line in open(path):
        r = json.loads(line)
        j = r["job"]
        sl = j["slicer"]
        grid = sl["type"] == "static" and sl.get("x") is not None
        name = ("grid:" + ",".join(f"{v:.2f}" for v in sl["x"])) if grid else r["slicer_name"]
        sla, per = _sla(r)
        rows.append(dict(role=j["role"], cell=j["cell"], strict=bool(j["scenario"].get("strict", False)), slicer=name,
                         grid=grid, seed=j["seed"], wm=_wmean(r.get("chunk_mos_user")), win=r.get("chunk_mos_user"),
                         sla=sla, sla_video=per.get(0, np.nan), sla_game=per.get(2, np.nan), sla_bulk=per.get(1, np.nan),
                         **{f"mos_{k}": v for k, v in r["mos_slice"].items()}))
    df = pd.DataFrame(rows)
    out, wins = [], []
    for (cell, strict), g in df[df.role != "phaseA"].groupby(["cell", "strict"]):
        gr = g[g.grid]
        piv = gr.pivot_table(index="slicer", columns="seed", values="wm")
        if piv.empty:
            continue
        orc = _loso(piv)
        # clairvoyant best split per scoring window (upper bound for any dynamic slicer)
        nwin = max(len(w) for w in gr.win if w)
        piece = {s: [] for s in orc}
        for c in range(nwin):
            pc = gr.assign(v=[(w[c] if w and c < len(w) else None) for w in gr.win]).dropna(subset=["v"])
            if pc.empty:
                continue
            pv = pc.pivot_table(index="slicer", columns="seed", values="v")
            for s, v in _loso(pv).items():
                piece.setdefault(s, []).append(v)
        piece = {s: float(np.mean(v)) for s, v in piece.items() if v}
        entries = {sl: h for sl, h in g[~g.grid].groupby("slicer")}
        dep = None
        if g.role.iloc[0] == "dynamic":
            if cell == "flash_crowd":
                pa = df[(df.role == "phaseA") & (df.cell == "flash_crowd") & (df.strict == strict)]
            else:   # the day starts video-heavy: an operator tunes for that mix
                pa = df[(df.role == "stationary") & (df.cell == "M1-video-heavy") & (df.strict == strict) & df.grid]
            if not pa.empty:
                dep = pa.groupby("slicer").wm.mean().idxmax()
                if dep in piv.index:
                    entries["deploy-static"] = gr[gr.slicer == dep]
        orc_m = float(np.mean(list(orc.values())))
        pce_m = float(np.mean([piece[s] for s in orc if s in piece])) if piece else np.nan
        head = 100 * (pce_m - orc_m) / orc_m
        for sl, h in entries.items():
            gp = [100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h.wm) if s in orc]
            m, lo, hi = boot_ci(gp)
            v = h.wm.mean()
            rec = dict(cell=cell, strict=strict, slicer=sl, seeds=len(gp), gap_pct=m, gap_lo=lo, gap_hi=hi, mos=v,
                       oracle=orc_m, piecewise_oracle=pce_m, headroom_pct=head,
                       captured=(v - orc_m) / (pce_m - orc_m) if pce_m - orc_m > 1e-3 else np.nan,
                       sla=h.sla.mean(), sla_video=h.sla_video.mean(), sla_game=h.sla_game.mean(), sla_bulk=h.sla_bulk.mean(),
                       oracle_x=piv.mean(axis=1).idxmax(), deploy_x=dep)
            for c in ("mos_video", "mos_game", "mos_bulk"):
                if c in h:
                    rec[c] = h[c].mean()
            out.append(rec)
            if g.role.iloc[0] == "dynamic":
                for c in range(nwin):
                    vals = [w[c] for w in h.win if w and c < len(w) and w[c] is not None]
                    if vals:
                        wins.append(dict(cell=cell, strict=strict, slicer=sl, window=c, mos=float(np.mean(vals))))
    t = pd.DataFrame(out)
    t.to_csv(os.path.join(T, "e7_gaps.csv"), index=False)
    w = pd.DataFrame(wins)
    w.to_csv(os.path.join(T, "e7_windows.csv"), index=False)
    S["E7"] = {"gaps": t.round(4).to_dict("records")}
    R.append("## E7. Unbalanced and shifting load\n")
    R.append("Gap (%) of window-averaged user MOS against the best single static split for the whole run "
             "(leave-one-seed-out). Headroom = how much a clairvoyant best split per 300 s window would gain over it; "
             "captured = share of that headroom a slicer actually gains (negative: it loses to the best static split; above 1 is possible "
             "because the per-window oracle only picks from the grid). "
             "SLA = share of (user, window) pairs meeting the slice target (video and gaming MOS >= 4, bulk MOS >= 3).\n")
    t2 = t.copy()
    t2["o"] = t2.slicer.map({s: i for i, s in enumerate(ORDER + ["deploy-static"])})
    t2 = t2.sort_values(["cell", "strict", "o"])
    R.append(md_table(t2, ["cell", "strict", "slicer", "gap_pct", "gap_lo", "gap_hi", "headroom_pct", "captured",
                           "sla", "sla_video", "sla_game", "sla_bulk"]))
    import experiments.figures as F
    if hasattr(F, "fig_e7"):
        F.fig_e7(t, w)
        R.append("\n![E7](../figures/fig_e7.png)\n")
    if hasattr(F, "fig_e7_sla"):
        F.fig_e7_sla(t)
        R.append("\n![E7 SLA trade-off](../figures/fig_e7_sla.png)\n")
    from experiments import campaign_report_r3 as R3
    R3.an_e7_frontier(path, T, S, R)


ANALYSES = {"E1": an_e1, "E2": an_e2, "E4": an_e4, "E5": an_e5, "E6": an_e6, "E7": an_e7}
NEEDS_ROOT = {"E9": "an_e9", "E10": "an_e10", "E11": "an_e11", "E12": "an_e12", "E13": "an_e13", "E14": "an_e14"}


def report(root, exps, tag):
    t0 = time.time()
    T = os.path.join(root, "results", "tables")
    os.makedirs(T, exist_ok=True)
    os.makedirs(os.path.join(root, "reports"), exist_ok=True)
    os.makedirs(os.path.join(root, "figures"), exist_ok=True)
    import experiments.figures as F
    F.OUT = os.path.join(root, "figures")
    S = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag, "root": root, "experiments": {}, "analysis_errors": {}}
    R = ["# EchoSlice HPC campaign report", "", f"Generated {S['generated']} (job tag {tag}).", ""]
    status_rows = []
    ok_all = True
    for e in exps:
        st = C.exp_status(root, e)
        if st is None:
            S["experiments"][e] = {"status": "not prepared"}
            ok_all = False
            continue
        path, n_ok, n_jobs = merge(root, e)
        st["complete"] = st["done_ok"] == st["jobs"]
        S["experiments"][e] = st
        status_rows.append(f"| {e} | {CJ.TITLES[e]} | {st['jobs']} | {st['done_ok']} | {st['errors']} | {st['missing']} | "
                           f"{'yes' if st['complete'] else 'NO'} |")
        ok_all &= st["complete"] and st["errors"] == 0
    R += ["## Completion", "", "| exp | title | jobs | done | errors | missing | complete |", "|---|---|---|---|---|---|---|"] + status_rows + [""]
    if not ok_all:
        R.append("**The campaign is incomplete. Tables below use the runs that finished.** Re-submit the same command to resume.\n")
    from experiments import campaign_report_r3 as R3
    R3._REF_CACHE.clear()
    R3._ALL_CACHE.clear()
    for e in exps:
        if (e not in ANALYSES and e not in NEEDS_ROOT) or S["experiments"].get(e, {}).get("done_ok", 0) == 0:
            continue
        try:
            p = os.path.join(C.exp_dir(root, e), "merged.jsonl")
            if e in NEEDS_ROOT:
                getattr(R3, NEEDS_ROOT[e])(p, T, S, R, root=root)
            else:
                ANALYSES[e](p, T, S, R)
            R.append("")
        except Exception:
            ok_all = False
            S["analysis_errors"][e] = traceback.format_exc()
            R.append(f"## {e}: analysis failed\n\n```\n{traceback.format_exc()[-1500:]}\n```\n")
    try:
        R3.drl_curves(root, T, S, R)
    except Exception:
        S["analysis_errors"]["DRL"] = traceback.format_exc()
    S["ok"] = bool(ok_all)
    S["report_seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(root, "results", "campaign_summary.json"), "w") as f:
        json.dump(S, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(root, "reports", "CAMPAIGN_REPORT.md"), "w") as f:
        f.write("\n".join(R) + "\n")
    print(f"[report] ok={ok_all} -> {os.path.join(root, 'reports', 'CAMPAIGN_REPORT.md')}", flush=True)
    return 0 if ok_all else 4
