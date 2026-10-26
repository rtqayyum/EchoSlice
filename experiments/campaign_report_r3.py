"""Analyses for the final (round-3) experiments: SLA frontier (E7), ablations (E9), imperfect
telemetry (E10), app hints (E11), XR and L4S (E12), theory checks (E13), convergence (E14).

All gaps are on window-averaged user MOS ('wm'), against the leave-one-seed-out best static split of
the same cell (taken from the experiment that holds the static grid for that cell when the experiment
itself has none). Worst-slice SLA = the lowest, over slices, of the share of (user, 300 s window)
pairs meeting the slice target (video and gaming/XR MOS >= 4, bulk MOS >= 3).
"""
import json
import math
import os

import numpy as np
import pandas as pd

from experiments import campaign as C
from experiments import campaign_jobs as CJ

TARGET = {0: 4.0, 2: 4.0, 1: 3.0}       # flow type -> MOS target (video, gaming/XR, bulk)
IMP_KEYS = ("kpm_delay_s", "kpm_drop", "qoe_noise", "qoe_source")
TRACE_EVERY = 1.0


# ------------------------------------------------------------------ loading
def skey(sc, drop=()):
    return json.dumps({k: v for k, v in sc.items() if k not in drop}, sort_keys=True)


def slicer_label(r):
    sl = r["job"]["slicer"]
    if sl["type"] == "static" and sl.get("x") is not None:
        return "grid:" + ",".join(f"{v:.2f}" for v in sl["x"]), True
    return r["slicer_name"], False


def sla_parts(r):
    cm, ft = r.get("chunk_flow_mos"), r.get("flow_type")
    if not cm or ft is None:
        return np.nan, {}
    hit, tot = {}, {}
    for i, row in enumerate(cm):
        for v in row:
            if v is None:
                continue
            tot[ft[i]] = tot.get(ft[i], 0) + 1
            hit[ft[i]] = hit.get(ft[i], 0) + (v >= TARGET[ft[i]])
    per = {k: hit[k] / tot[k] for k in tot}
    return sum(hit.values()) / max(sum(tot.values()), 1), per


def wmean(v):
    v = [x for x in (v or []) if x is not None]
    return float(np.mean(v)) if v else np.nan


def rows_of(path, keep_windows=False, keep_trace=False):
    out = []
    for line in open(path):
        r = json.loads(line)
        j = r["job"]
        name, grid = slicer_label(r)
        sla, per = sla_parts(r)
        sc = j["scenario"]
        d = dict(exp=j.get("exp"), role=j.get("role", ""), cell=j.get("cell", ""), strict=bool(sc.get("strict", False)),
                 slicer=name, grid=grid, seed=j["seed"], wm=wmean(r.get("chunk_mos_user")), mos=r["mos_user"],
                 sla=sla, sla_video=per.get(0, np.nan), sla_game=per.get(2, np.nan), sla_bulk=per.get(1, np.nan),
                 skey=skey(sc), base_key=skey(sc, IMP_KEYS), impairment=j.get("impairment", ""),
                 ref_exp=j.get("ref_exp", ""), ref_key=skey(j["ref_scenario"]) if j.get("ref_scenario") else "",
                 decide_ms=r.get("decide_ms", np.nan), l4s_qdelay_ms=r.get("l4s_qdelay_ms", np.nan),
                 spec=json.dumps(j["slicer"], sort_keys=True), names=",".join(r["names"]),
                 share=r.get("share_mean"))
        d["sla_min"] = np.nanmin([d["sla_video"], d["sla_game"], d["sla_bulk"]]) if per else np.nan
        for k, v in r["mos_slice"].items():
            d["mos_" + k] = v
        if keep_windows:
            d["win"] = r.get("chunk_mos_user")
        if keep_trace:
            d["trace"] = r.get("slice_trace")
            d["share_std"] = r.get("share_std")
        out.append(d)
    return pd.DataFrame(out)


_REF_CACHE = {}


def ref_rows(root, exp):
    """Static-grid runs of an experiment (cached), keyed by scenario."""
    if exp not in _REF_CACHE:
        p = os.path.join(C.exp_dir(root, exp), "merged.jsonl")
        if not os.path.exists(p):
            _REF_CACHE[exp] = pd.DataFrame()
        else:
            df = rows_of(p)
            _REF_CACHE[exp] = df[df.grid].copy()
    return _REF_CACHE[exp]


def loso(piv):
    seeds = list(piv.columns)
    out = {}
    for s in seeds:
        others = [o for o in seeds if o != s] or seeds
        out[s] = float(piv.loc[piv[others].mean(axis=1).idxmax(), s])
    return out


def oracle_for(root, exp, key, metric="wm"):
    g = ref_rows(root, exp)
    if g.empty:
        return {}, None
    g = g[g.skey == key]
    if g.empty:
        return {}, None
    piv = g.pivot_table(index="slicer", columns="seed", values=metric)
    return loso(piv), piv.mean(axis=1).idxmax()


def boot(v, B=2000, seed=0):
    v = np.asarray([x for x in v if np.isfinite(x)], dtype=float)
    if len(v) < 2:
        return (float(v.mean()) if len(v) else np.nan, np.nan, np.nan)
    bs = np.random.default_rng(seed).choice(v, (B, len(v)), replace=True).mean(axis=1)
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def gap_rows(h, orc, metric="wm"):
    gp = [100 * (orc[s] - v) / orc[s] for s, v in zip(h.seed, h[metric]) if s in orc and np.isfinite(v)]
    return boot(gp)


def summarise(h, orc, extra=None):
    m, lo, hi = gap_rows(h, orc)
    rec = dict(seeds=int(len(h)), gap_pct=m, gap_lo=lo, gap_hi=hi, wm=h.wm.mean(), sla=h.sla.mean(),
               sla_min=h.sla_min.mean(), sla_video=h.sla_video.mean(), sla_game=h.sla_game.mean(),
               sla_bulk=h.sla_bulk.mean(), decide_ms=h.decide_ms.mean())
    for c in ("mos_video", "mos_game", "mos_bulk"):
        if c in h:
            rec[c] = h[c].mean()
    if extra:
        rec.update(extra)
    return rec


# ------------------------------------------------------------------ E7 frontier
FAMILIES = {
    "EchoSlice (v3)": ["echoslice3", "echoslice3-l0.5", "echoslice3-l1", "echoslice3-l2"],
    "Forecast + h": ["forecast+10%", "forecast+20%", "forecast+30%", "forecast+50%"],
    "Open-loop QoE + SLA": ["ol-qoe+10%", "ol-qoe+10%-sla0.5", "ol-qoe+10%-sla1", "ol-qoe+10%-sla2"],
    "DRL, trained in loop": ["drl-loop", "drl-loop-l1"],
    "DRL, trained on replay": ["drl-twin", "drl-twin-l1"],
}


def pareto_front(pts):
    """pts: list of (mean wm, worst-slice SLA); returns the non-dominated subset (both maximised)."""
    pts = sorted(set(pts), key=lambda p: (-p[0], -p[1]))
    out, best_s = [], -1
    for m, s in pts:
        if s > best_s:
            out.append((m, s))
            best_s = s
    return out


def hypervolume(pts, ref):
    """2-D hypervolume (wm, sla_min) above the reference point ref = (wm_ref, sla_ref)."""
    f = [p for p in pareto_front(pts) if p[0] > ref[0] and p[1] > ref[1]]
    f = sorted(f, key=lambda p: p[0])            # increasing wm, decreasing sla
    hv, prev_m = 0.0, ref[0]
    for i, (m, s) in enumerate(f):
        # area contributed between prev_m and m at height = max sla of points with wm >= m
        hs = max(p[1] for p in f[i:])
        hv += (m - prev_m) * (hs - ref[1])
        prev_m = m
    return hv


def an_e7_frontier(path, T, S, R):
    df = rows_of(path)
    df = df[df.role != "phaseA"]
    out, curves = [], []
    for (cell, strict), g in df.groupby(["cell", "strict"]):
        gr = g[g.grid]
        if gr.empty:
            continue
        piv = gr.pivot_table(index="slicer", columns="seed", values="wm")
        orc = loso(piv)
        o_m = float(np.mean(list(orc.values())))
        pts = {"Static splits (clairvoyant per cell)": [(float(h.wm.mean()), float(h.sla_min.mean()))
                                                          for _, h in gr.groupby("slicer")]}
        for fam, names in FAMILIES.items():
            pts[fam] = [(float(g[g.slicer == n].wm.mean()), float(g[g.slicer == n].sla_min.mean()))
                        for n in names if (g.slicer == n).any()]
            for n in names:
                h = g[g.slicer == n]
                if len(h):
                    curves.append(dict(cell=cell, strict=strict, family=fam, slicer=n,
                                       gap_pct=100 * (o_m - h.wm.mean()) / o_m, sla_min=h.sla_min.mean(), sla=h.sla.mean()))
        ref = (o_m * 0.90, 0.0)
        for fam, p in pts.items():
            if not p:
                continue
            rec = dict(cell=cell, strict=strict, family=fam, points=len(p), hypervolume=hypervolume(p, ref))
            for tau in (0.5, 0.6, 0.7, 0.8):
                ok = [m for m, s in p if s >= tau]
                rec[f"gap_at_sla{tau:g}"] = 100 * (o_m - max(ok)) / o_m if ok else np.nan
            best = max(p, key=lambda q: q[1])
            rec["best_sla_min"] = best[1]
            out.append(rec)
        for m, s in pareto_front(pts["Static splits (clairvoyant per cell)"]):
            curves.append(dict(cell=cell, strict=strict, family="Static splits (clairvoyant per cell)", slicer="front",
                               gap_pct=100 * (o_m - m) / o_m, sla_min=s, sla=np.nan))
    t = pd.DataFrame(out)
    c = pd.DataFrame(curves)
    t.to_csv(os.path.join(T, "e7_frontier.csv"), index=False)
    c.to_csv(os.path.join(T, "e7_frontier_points.csv"), index=False)
    if t.empty:
        return
    hv = t.pivot_table(index=["cell", "strict"], columns="family", values="hypervolume")
    hv_rel = hv.div(hv["Static splits (clairvoyant per cell)"], axis=0).round(3)
    S["E7_frontier"] = {"hypervolume_relative_to_static_front": {str(k): v for k, v in hv_rel.to_dict("index").items()},
                        "table": t.round(4).to_dict("records")}
    R.append("### E7 (final). Mean QoE against the worst slice's SLA\n")
    R.append("Hypervolume of each slicer family's (mean user MOS, worst-slice SLA) points, relative to the front of "
             "all static splits of the same cell (1.0 = as good as the best static splits chosen per cell with hindsight). "
             "Reference point: 10% below the best static split, SLA 0.\n")
    R.append(hv_rel.reset_index().to_markdown(index=False))
    R.append("\nMean-QoE gap (%) of the best point of each family whose worst-slice SLA is at least 0.7 "
             "(blank: no point reaches it):\n")
    g7 = t.pivot_table(index=["cell", "strict"], columns="family", values="gap_at_sla0.7").round(2)
    R.append(g7.reset_index().to_markdown(index=False))
    import experiments.figures as F
    if hasattr(F, "fig_frontier"):
        F.fig_frontier(c)
        R.append("\n![frontier](../figures/fig_frontier.png)\n")


# ------------------------------------------------------------------ E9 ablations, E11 hints, E10 telemetry
def _vs_ref(root, df, ref_col="ref_exp", key_col="skey"):
    out = []
    for (cell, ref, key), g in df.groupby(["cell", ref_col, key_col]):
        orc, ox = oracle_for(root, ref, key)
        if not orc:
            continue
        for sl, h in g.groupby("slicer"):
            out.append(dict(cell=cell, ref_exp=ref, slicer=sl, oracle_x=ox, **summarise(h, orc)))
    return pd.DataFrame(out)


def an_e9(path, T, S, R, root=None):
    df = rows_of(path)
    t = _vs_ref(root, df)
    t.to_csv(os.path.join(T, "e9_ablations.csv"), index=False)
    if t.empty:
        R.append("## E9. Ablations\n\n(no reference static grid found)\n")
        return
    S["E9"] = {"table": t.round(4).to_dict("records")}
    piv = t.pivot_table(index="slicer", columns="cell", values="gap_pct").round(2)
    piv["mean"] = piv.mean(axis=1).round(2)
    piv["worst"] = piv.drop(columns="mean").max(axis=1).round(2)
    R.append("## E9. Ablations of EchoSlice (v3)\n")
    R.append("Gap (%) to the best static split of each cell, 30 seeds; 'abl-freeze-at-eval' stops probing when scoring "
             "starts, so its difference to the full method is the QoE cost of probing in stationary cells.\n")
    R.append(piv.reset_index().to_markdown(index=False))
    sp = t.pivot_table(index="slicer", columns="cell", values="sla_min").round(2)
    R.append("\nWorst-slice SLA:\n")
    R.append(sp.reset_index().to_markdown(index=False))
    import experiments.figures as F
    if hasattr(F, "fig_ablation"):
        F.fig_ablation(t)
        R.append("\n![ablations](../figures/fig_ablation.png)\n")


def an_e11(path, T, S, R, root=None):
    df = rows_of(path)
    t = _vs_ref(root, df)
    # the non-cooperative EchoSlice (v3) in the same cells, from the reference experiments
    base = []
    for (cell, ref, key), g in df.groupby(["cell", "ref_exp", "skey"]):
        p = os.path.join(C.exp_dir(root, ref), "merged.jsonl")
        if not os.path.exists(p):
            continue
        if ref not in _ALL_CACHE:
            _ALL_CACHE[ref] = rows_of(p)
        rr = _ALL_CACHE[ref]
        h = rr[(rr.skey == key) & rr.slicer.isin(["echoslice3", "echoslice3-l1"])]
        orc, ox = oracle_for(root, ref, key)
        for sl, hh in h.groupby("slicer"):
            base.append(dict(cell=cell, ref_exp=ref, slicer=sl, oracle_x=ox, **summarise(hh, orc)))
    t = pd.concat([t, pd.DataFrame(base)], ignore_index=True) if base else t
    t.to_csv(os.path.join(T, "e11_hints.csv"), index=False)
    if t.empty:
        return
    S["E11"] = {"table": t.round(4).to_dict("records")}
    R.append("## E11. App hints (cooperative mode) and a lying app\n")
    R.append("Gap (%) to the best static split; 'hint-liar' = the gaming app reports 3x its true saturation rate.\n")
    R.append(t.pivot_table(index="cell", columns="slicer", values="gap_pct").round(2).reset_index().to_markdown(index=False))
    R.append("\nWorst-slice SLA:\n")
    R.append(t.pivot_table(index="cell", columns="slicer", values="sla_min").round(2).reset_index().to_markdown(index=False))


_ALL_CACHE = {}


def an_e10(path, T, S, R, root=None):
    df = rows_of(path)
    out = []
    for (cell, ref, key), g in df.groupby(["cell", "ref_exp", "base_key"]):
        orc, ox = oracle_for(root, ref, key)
        if not orc:
            continue
        # unimpaired runs of the same slicers, from the reference experiment
        p = os.path.join(C.exp_dir(root, ref), "merged.jsonl")
        if ref not in _ALL_CACHE and os.path.exists(p):
            _ALL_CACHE[ref] = rows_of(p)
        rr = _ALL_CACHE.get(ref, pd.DataFrame())
        for sl, h0 in (rr[rr.skey == key].groupby("slicer") if not rr.empty else []):
            if sl in set(g.slicer):
                out.append(dict(cell=cell, impairment="none", slicer=sl, **summarise(h0, orc)))
        for (imp, sl), h in g.groupby(["impairment", "slicer"]):
            out.append(dict(cell=cell, impairment=imp, slicer=sl, **summarise(h, orc)))
    t = pd.DataFrame(out)
    t.to_csv(os.path.join(T, "e10_telemetry.csv"), index=False)
    if t.empty:
        return
    S["E10"] = {"table": t.round(4).to_dict("records")}
    R.append("## E10. Imperfect telemetry\n")
    R.append("Gap (%) to the best static split (static splits do not read telemetry), mean over the four cells:\n")
    m = t.groupby(["slicer", "impairment"]).gap_pct.mean().unstack().round(2)
    R.append(m.reset_index().to_markdown(index=False))
    R.append("\nWorst cell:\n")
    R.append(t.groupby(["slicer", "impairment"]).gap_pct.max().unstack().round(2).reset_index().to_markdown(index=False))
    import experiments.figures as F
    if hasattr(F, "fig_telemetry"):
        F.fig_telemetry(t)
        R.append("\n![telemetry](../figures/fig_telemetry.png)\n")


# ------------------------------------------------------------------ E12 XR / L4S (own static grid)
def an_e12(path, T, S, R, root=None):
    df = rows_of(path)
    out = []
    for (cell, strict), g in df.groupby(["cell", "strict"]):
        gr = g[g.grid]
        if gr.empty:
            continue
        orc = loso(gr.pivot_table(index="slicer", columns="seed", values="wm"))
        ox = gr.groupby("slicer").wm.mean().idxmax()
        for sl, h in g[~g.grid].groupby("slicer"):
            out.append(dict(cell=cell, strict=strict, slicer=sl, oracle_x=ox,
                            **summarise(h, orc, dict(l4s_qdelay_ms=h.l4s_qdelay_ms.mean()))))
    t = pd.DataFrame(out)
    t.to_csv(os.path.join(T, "e12_xr_l4s.csv"), index=False)
    if t.empty:
        return
    S["E12"] = {"table": t.round(4).to_dict("records")}
    R.append("## E12. XR and L4S cells\n")
    R.append("X1: 24 video, 6 XR (5-60 Mb/s, 20 ms frame budget), 6 bulk. X2: X1 with TCP Prague + L4S marking for video "
             "and bulk. X3: 24 video, 8 cloud gaming, 6 bulk, all TCP over L4S. Gap (%) to the best static split:\n")
    t["cell_mode"] = t.cell + np.where(t.strict, " strict", " shareable")
    R.append(t.pivot_table(index="slicer", columns="cell_mode", values="gap_pct").round(2).reset_index().to_markdown(index=False))
    R.append("\nWorst-slice SLA:\n")
    R.append(t.pivot_table(index="slicer", columns="cell_mode", values="sla_min").round(2).reset_index().to_markdown(index=False))
    q = t.dropna(subset=["l4s_qdelay_ms"])
    if not q.empty:
        R.append("\nMean per-UE queue delay of L4S flows (ms):\n")
        R.append(q.pivot_table(index="slicer", columns="cell_mode", values="l4s_qdelay_ms").round(2).reset_index().to_markdown(index=False))


# ------------------------------------------------------------------ E13 theory checks
def fit_response(tr, k, K):
    """Fit y_t = a*y_{t-1} + b*c_{t-d} + e on the stepped slice (0.5 s samples).
    c = capacity given to the slice (share x served-rate-per-PRB x PRBs), y = offered load.
    Returns politeness beta = b/(1-a) (offered per unit of capacity), time constant tau (s), delay (s)."""
    A = np.array(tr, dtype=float)
    t = A[:, 0]
    x = A[:, 1 + k]
    off = A[:, 1 + K + k]
    srv = A[:, 1 + 2 * K + k]
    prb = A[:, 1 + 3 * K + k]
    B = 273.0
    rp = np.where(prb > 1.0, srv / np.maximum(prb, 1e-9), np.nan)          # Mb/s per PRB actually achieved
    rp = pd.Series(rp).ffill().bfill().rolling(20, min_periods=1).median().to_numpy()
    cap = x * B * rp
    ok = t > 60.0
    best = None
    for d in range(0, 21):                                    # delay 0-10 s
        y = off[ok][d + 1:]
        y1 = off[ok][d:-1]
        c = cap[ok][:len(cap[ok]) - d - 1]
        if len(y) < 50:
            continue
        X = np.column_stack([y1, c, np.ones(len(y))])
        coef, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(((X @ coef - y) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, d, coef)
    if best is None:
        return dict(beta=np.nan, tau_s=np.nan, delay_s=np.nan, ratio=np.nan)
    _, d, (a, b, e) = best
    a = min(max(a, 1e-3), 0.999)
    ratio = float(np.nanmedian(off[ok] / np.maximum(cap[ok], 1e-6)))      # steady offered / capacity
    return dict(beta=float(b / (1 - a)), tau_s=float(-TRACE_EVERY / math.log(a)), delay_s=d * TRACE_EVERY, ratio=ratio)


def ewma_gain(Ts, alpha, L):
    """Gain with which a demand-following slicer passes the apps' on-off cycle (period L, the segment
    duration) into its shares: per-period averaging (|sinc(Ts/L)|) times the EWMA filter
    |alpha / (1 - (1 - alpha) e^{-j 2 pi Ts / L})|."""
    w = 2 * math.pi * Ts / L
    u = Ts / L
    sinc = 1.0 if u == 0 else abs(math.sin(math.pi * u) / (math.pi * u))
    return sinc * abs(alpha / (1 - (1 - alpha) * complex(math.cos(w), -math.sin(w))))


def an_e13(path, T, S, R, root=None):
    df = rows_of(path, keep_trace=True)
    R.append("## E13. Theory checks\n")
    # (a) app response: politeness beta and adaptation time per class
    st = df[df.role == "steps"]
    resp = []
    for (cls), g in st.groupby("cell"):
        K = len(g.names.iloc[0].split(","))
        k = json.loads(g.spec.iloc[0])["k"]
        fits = [fit_response(tr, k, K) for tr in g.trace if tr]
        if fits:
            f = pd.DataFrame(fits)
            resp.append(dict(app=cls, runs=len(f), beta=f.beta.median(), ratio=f.ratio.median(),
                             tau_s=f.tau_s.median(), delay_s=f.delay_s.median(),
                             h_star_pred=(1.0 / f.ratio.median() - 1.0) if f.ratio.median() > 0 else np.nan))
    rp = pd.DataFrame(resp)
    rp.to_csv(os.path.join(T, "e13_app_response.csv"), index=False)
    # (b) knife-edge: smallest headroom at which the app's slice escapes the floor
    kn = df[df.role == "knife"].copy()
    kn["h"] = kn.slicer.str.extract(r"forecast\+(\d+(?:\.\d+)?)%").astype(float)[0] / 100
    kn["x_app"] = [s[0] if isinstance(s, list) and s else np.nan for s in kn.share]
    ke = kn.groupby(["cell", "strict", "h"]).agg(x_app=("x_app", "mean"), wm=("wm", "mean")).reset_index()
    ke.to_csv(os.path.join(T, "e13_knife_edge.csv"), index=False)
    meas = []
    for (cell, strict), g in ke.groupby(["cell", "strict"]):
        g = g.sort_values("h")
        lo, hi = g.x_app.min(), g.x_app.max()
        thr = lo + 0.5 * (hi - lo)
        above = g[g.x_app >= thr]
        meas.append(dict(app=cell, strict=strict, h_star_meas=float(above.h.min()) if len(above) else np.nan,
                         x_floor=lo, x_top=hi))
    ms = pd.DataFrame(meas)
    if not rp.empty and not ms.empty:
        cmp_ = ms.merge(rp[["app", "ratio", "beta", "tau_s", "delay_s", "h_star_pred"]], on="app", how="left")
    else:
        cmp_ = ms
    cmp_.to_csv(os.path.join(T, "e13_knife_pred_vs_meas.csv"), index=False)
    if not rp.empty:
        R.append("App response from randomised share steps (median over runs):\n")
        R.append(rp.round(3).to_markdown(index=False))
        R.append("")
    R.append("Knife-edge: ratio = steady offered load / capacity given "
             "(politeness when < 1), tau = adaptation time, and the headroom knife-edge it predicts, h* = 1/ratio - 1, "
             "against the measured knife-edge of forecast + h (strict and shareable):\n")
    R.append(cmp_.round(3).to_markdown(index=False))
    # (c) resonance: share swing vs the EWMA filter gain at the segment on-off frequency
    rs = []
    for rr, src in ((df[df.role == "resonance"], "E13"),):
        for _, r in rr.iterrows():
            sc = json.loads(r.skey)
            alpha = json.loads(r.spec).get("alpha", 0.5)
            rs.append(dict(src=src, slicer=f"usage a={alpha:g}", Ts=sc.get("Ts", 1.0), L=sc.get("seg_dur", 4.0),
                           alpha=alpha, xsd=(r.share_std or [np.nan])[0]))
    e2p = os.path.join(C.exp_dir(root, "E2"), "merged.jsonl") if root else ""
    if e2p and os.path.exists(e2p):
        for line in open(e2p):
            r = json.loads(line)
            j = r["job"]
            sl = j["slicer"]
            if sl["type"] not in ("usage", "forecast"):
                continue
            alpha = sl.get("alpha", 0.5 if sl["type"] == "usage" else 0.3)
            sc = j["scenario"]
            if sc.get("abr", "tput") != "tput":
                continue
            rs.append(dict(src="E2", slicer=f"{sl['type']} a={alpha:g}", Ts=sc.get("Ts", 1.0), L=sc.get("seg_dur", 4.0),
                           alpha=alpha, xsd=r["share_std"][0]))
    rz = pd.DataFrame(rs)
    if not rz.empty:
        rz["H"] = [ewma_gain(a.Ts, a.alpha, a.L) for a in rz.itertuples()]
        agg = rz.groupby(["slicer", "Ts", "L"]).agg(xsd=("xsd", "mean"), H=("H", "first")).reset_index()
        agg.to_csv(os.path.join(T, "e13_resonance.csv"), index=False)
        from scipy.stats import spearmanr
        rho = {sl: float(spearmanr(g.H, g.xsd).correlation) for sl, g in agg.groupby("slicer") if len(g) > 3}
        rho_all = float(spearmanr(agg.H, agg.xsd).correlation)
        S["E13"] = {"app_response": rp.round(4).to_dict("records"), "knife": cmp_.round(4).to_dict("records"),
                    "resonance_spearman": rho, "resonance_spearman_all": rho_all}
        R.append(f"\nResonance: Spearman correlation between the video-share swing and the predicted gain G "
                 f"(per-period averaging times the EWMA filter, at the segment on-off frequency): all {rho_all:.2f}; per slicer "
                 + ", ".join(f"{k} {v:.2f}" for k, v in rho.items()) + ".\n")
    import experiments.figures as F
    if hasattr(F, "fig_theory"):
        F.fig_theory(ke, cmp_, rz if not rz.empty else None)
        R.append("\n![theory](../figures/fig_theory.png)\n")


# ------------------------------------------------------------------ E14 convergence
def an_e14(path, T, S, R, root=None):
    df = rows_of(path, keep_windows=True)
    out, curves = [], []
    for (cell, ref, key), g in df.groupby(["cell", "ref_exp", "ref_key"]):
        orc, ox = oracle_for(root, ref, key)
        if not orc:
            continue
        for sl, h in g.groupby("slicer"):
            gaps = []
            for s, w in zip(h.seed, h.win):
                if s not in orc or not w:
                    continue
                gaps.append([100 * (orc[s] - v) / orc[s] if v is not None else np.nan for v in w])
            if not gaps:
                continue
            G = np.array(gaps, dtype=float)                   # seeds x minutes
            mean = np.nanmean(G, axis=0)
            for i, v in enumerate(mean):
                curves.append(dict(cell=cell, slicer=sl, minute=i + 1, gap_pct=float(v)))
            sm = pd.Series(mean).rolling(3, min_periods=1).mean().to_numpy()
            within = [i for i in range(len(sm)) if np.all(sm[i:] < 1.0)]
            out.append(dict(cell=cell, slicer=sl, minutes_to_1pct=(within[0] + 1) if within else np.nan,
                            gap_first5=float(np.nanmean(mean[:5])), gap_last10=float(np.nanmean(mean[-10:]))))
    t = pd.DataFrame(out)
    c = pd.DataFrame(curves)
    t.to_csv(os.path.join(T, "e14_convergence.csv"), index=False)
    c.to_csv(os.path.join(T, "e14_curves.csv"), index=False)
    if t.empty:
        return
    S["E14"] = {"table": t.round(4).to_dict("records")}
    R.append("## E14. Convergence (1,800 s runs, QoE per minute)\n")
    R.append("Minutes until the 3-minute rolling gap to the best static split stays below 1% (blank: never), "
             "and the mean gap over the first 5 and last 10 minutes:\n")
    R.append(t.pivot_table(index="slicer", columns="cell", values="minutes_to_1pct", dropna=False).reset_index().to_markdown(index=False))
    R.append("\nGap over the last 10 minutes (%):\n")
    R.append(t.pivot_table(index="slicer", columns="cell", values="gap_last10").round(2).reset_index().to_markdown(index=False))
    import experiments.figures as F
    if hasattr(F, "fig_convergence"):
        F.fig_convergence(c)
        R.append("\n![convergence](../figures/fig_convergence.png)\n")


# ------------------------------------------------------------------ DRL learning curves
def drl_curves(root, T, S, R):
    rows = []
    for reg in ("loop", "twin"):
        p = os.path.join(root, "policies", f"drl_{reg}_log.jsonl")
        if os.path.exists(p):
            for line in open(p):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d["regime"] = reg
                rows.append(d)
    if not rows:
        return
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(T, "drl_learning.csv"), index=False)
    eps = {}
    for reg in ("loop", "twin"):
        p = os.path.join(root, "policies", f"drl_{reg}.json")
        if os.path.exists(p):
            eps[reg] = json.load(open(p)).get("meta", {})
    S["DRL"] = {"selected": eps}
    R.append("## DRL training (PPO)\n")
    for reg, m in eps.items():
        R.append(f"- {reg}: selected iteration {m.get('iter')} (validation utility {m.get('val_utility', float('nan')):.3f}, "
                 f"{m.get('episodes_seen')} training episodes)")
    import experiments.figures as F
    if hasattr(F, "fig_drl"):
        F.fig_drl(d)
        R.append("\n![DRL learning](../figures/fig_drl.png)\n")
