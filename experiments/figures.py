"""Figures for the gate report.

fig_mechanism : time traces of shares, GCC rate and video bitrate (one cell, one seed)
fig_gap       : price of ignoring reactions per scenario cell (E1)
fig_pareto    : static-share frontier vs dynamic slicers (2-slice cell, E1)
fig_resonance : oscillation vs slicer period and segment length (E2)
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Reference categorical palette (light), slots in fixed order.
C = {"echoslice-lite": "#2a78d6", "usage-prop": "#eb6834", "forecast+20%": "#1baf7a", "ol-qoe+10%": "#eda100",
     "echoslice": "#e87ba4", "echoslice3": "#6250d6", "drl-loop": "#008300", "drl-twin": "#e34948"}
# families of swept slicers in the final campaign share their base colour
FAM_COLOR = {"EchoSlice (v3)": "#6250d6", "Forecast + h": "#1baf7a", "Open-loop QoE + SLA": "#eda100",
             "DRL, trained in loop": "#008300", "DRL, trained on replay": "#e34948",
             "Static splits (clairvoyant per cell)": "#8a8985"}
FAM_MARK = {"EchoSlice (v3)": "o", "Forecast + h": "s", "Open-loop QoE + SLA": "^", "DRL, trained in loop": "D",
            "DRL, trained on replay": "v", "Static splits (clairvoyant per cell)": None}
REF = {"oracle": "#52514e", "static": "#8a8985", "shared": "#b5b4ae"}
LABEL = {"echoslice-lite": "EchoSlice-lite", "echoslice": "EchoSlice (v2)", "usage-prop": "Usage-proportional", "forecast+20%": "Forecast + 20%",
         "ol-qoe+10%": "Open-loop QoE", "static": "Static equal", "shared": "No slicing (PF)",
         "echoslice3": "EchoSlice (v3)", "echoslice3-l1": "EchoSlice (v3), SLA 1", "drl-loop": "DRL, loop-trained",
         "drl-twin": "DRL, replay-trained", "ol-qoe+10%-sla1": "Open-loop QoE + SLA 1"}
TEXT2 = "#52514e"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#b5b4ae", "axes.labelcolor": "#0b0b0b", "xtick.color": TEXT2,
                     "ytick.color": TEXT2, "axes.grid": True, "grid.color": "#ecebe7", "grid.linewidth": 0.6,
                     "legend.frameon": False, "figure.dpi": 160, "lines.linewidth": 1.6})
OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)


def fig_mechanism(seed=1, abr="dyn"):
    from sim.engine import Scenario, simulate
    from sim import slicers as SL
    sc = Scenario(n_video=24, n_game=8, n_bulk=6, abr=abr)
    runs = {}
    for sl in (SL.UsageProp(), SL.ForecastHeadroom(0.2), SL.OpenLoopQoE(0.1), SL.EchoSliceLite()):
        runs[sl.name] = simulate(sc, sl, seed, trace=True)
    names = runs["usage-prop"]["names"]
    gi, vi = names.index("game"), names.index("video")
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.6), sharex=True)
    panels = [(ax[0, 0], "trace_x", gi, "game-slice share"),
              (ax[0, 1], "trace_game_rate_mbps", None, "mean GCC rate (Mb/s)"),
              (ax[1, 0], "trace_x", vi, "video-slice share"),
              (ax[1, 1], "trace_video_level_mbps", None, "mean video bitrate (Mb/s)")]
    for a, key, col, lab in panels:
        for nm, r in runs.items():
            t = r["trace_t"]
            y = r[key][:, col] if col is not None else r[key]
            if key != "trace_x":
                k = max(1, int(5 / sc.Ts))
                y = pd.Series(y).rolling(k, center=True, min_periods=1).mean().to_numpy()
            a.plot(t, y, color=C[nm], label=LABEL[nm], lw=1.3)
        a.set_ylabel(lab)
        a.axvspan(sc.t_eval0, sc.T, color="#f4f3ef", zorder=0, lw=0)
    for a in ax[1]:
        a.set_xlabel("time (s)")
    h, l = ax[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, 0.0))
    ax[0, 1].text(sc.t_eval0 + 8, 0.97, "evaluation window", color=TEXT2, fontsize=7.5,
                  transform=ax[0, 1].get_xaxis_transform(), va="top")
    fig.suptitle("One cell, 24 video + 8 cloud-gaming + 6 bulk flows, dash.js DYNAMIC ABR, shareable min-ratio slicing",
                 fontsize=8.5, color=TEXT2, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_mechanism.png"))
    summ = {nm: dict(mos=r["mos_user"], slices=r["mos_slice"], x=r["share_mean"], late=r["game_late"],
                     game_rate=r["game_rate"], bitrate=r["bitrate_mbps"], bulk=r["bulk_mbps"]) for nm, r in runs.items()}
    json.dump(summ, open(os.path.join(OUT, "fig_mechanism_summary.json"), "w"), indent=1, default=float)
    return summ


def _family(r):
    k = "3-slice (video+gaming+bulk)" if r.n_game > 0 else "2-slice (video+bulk)"
    return k + (", strict" if r.strict else ", shareable")


def fig_gap(cells_csv):
    ct = pd.read_csv(cells_csv)
    ct["family"] = ct.apply(_family, axis=1)
    fams = ["2-slice (video+bulk), shareable", "2-slice (video+bulk), strict",
            "3-slice (video+gaming+bulk), shareable", "3-slice (video+gaming+bulk), strict"]
    order = [x for x in ["usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "echoslice"] if x in set(ct.slicer)]
    fig, axs = plt.subplots(1, 4, figsize=(8.4, 3.0), sharey=True)
    rng = np.random.default_rng(0)
    for a, fam in zip(axs, fams):
        g = ct[ct.family == fam]
        for j, sl in enumerate(order):
            h = g[g.slicer == sl]
            if h.empty:
                continue
            xs = j + rng.uniform(-0.18, 0.18, len(h))
            a.scatter(xs, h.gap_pct, s=14, color=C[sl], alpha=0.85, lw=0, zorder=3)
            a.hlines(h.gap_pct.median(), j - 0.3, j + 0.3, color="#0b0b0b", lw=1.2, zorder=4)
        for ref in ("static", "shared"):
            h = g[g.slicer == ref]
            if not h.empty:
                a.axhline(h.gap_pct.median(), color=REF[ref], lw=0.8, ls=":", zorder=1)
        a.axhline(5, color="#e34948", lw=0.8, ls="--", zorder=1)
        a.axhline(0, color="#b5b4ae", lw=0.8, zorder=1)
        a.set_xticks(range(len(order)))
        short = {"usage-prop": "Usage-\nprop.", "forecast+20%": "Forecast\n+20%", "ol-qoe+10%": "Open-loop\nQoE",
                 "echoslice-lite": "Echo-\nSlice-lite", "echoslice": "Echo-\nSlice v2"}
        a.set_xticklabels([short[x] for x in order], fontsize=6.5)
        a.set_title(fam.replace(", ", "\n"), fontsize=8, color=TEXT2)
    axs[0].set_ylabel("QoE gap to best static share (%)")
    axs[0].text(3.4, 5.3, "5% gate", color="#e34948", fontsize=7, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_gap.png"))


def fig_pareto(e1_jsonl, cell=(32, 0, 6, "tput", False)):
    from experiments.analyze import load
    df = load(e1_jsonl)
    g = df[(df.n_video == cell[0]) & (df.n_game == cell[1]) & (df.n_bulk == cell[2]) & (df.abr == cell[3]) & (df.strict == cell[4])]
    grid = g[g.is_grid].groupby("slicer")[["mos_video", "mos_bulk", "x_video"]].mean().sort_values("x_video")
    fig, a = plt.subplots(figsize=(4.4, 3.4))
    a.plot(grid.mos_bulk, grid.mos_video, color=REF["oracle"], lw=1.0, marker="o", ms=3.5, zorder=2)
    for _, r in grid.iterrows():
        if abs(r.x_video * 10 - round(r.x_video * 10)) < 1e-6 and round(r.x_video * 10) % 2 == 1:
            a.annotate(f"{r.x_video:.1f}", (r.mos_bulk, r.mos_video), textcoords="offset points", xytext=(4, -9),
                       fontsize=6.5, color=TEXT2)
    for sl in ("usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite"):
        h = g[g.slicer == sl][["mos_video", "mos_bulk"]].mean()
        a.scatter(h.mos_bulk, h.mos_video, s=46, color=C[sl], edgecolor="white", lw=1.2, zorder=4, label=LABEL[sl])
    for ref in ("shared",):
        h = g[g.slicer == ref][["mos_video", "mos_bulk"]].mean()
        if h.notna().all():
            a.scatter(h.mos_bulk, h.mos_video, s=40, marker="s", color=REF[ref], edgecolor="white", lw=1.0, zorder=3,
                      label=LABEL[ref])
    a.set_xlabel("bulk MOS")
    a.set_ylabel("video MOS (P.1203)")
    a.legend(fontsize=7, loc="lower left")
    a.set_title("Static shares (gray, labelled by video share) vs dynamic slicers", fontsize=8, color=TEXT2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_pareto.png"))


def fig_resonance(e2_jsonl):
    from experiments.analyze import load
    df = load(e2_jsonl)
    df = df[(df.exp == "E2") & (~df.is_grid)]
    fig, axs = plt.subplots(1, 3, figsize=(8.4, 3.4))
    for a, (metric, lab) in zip(axs, [("xsd_video", "std of video-slice share"), ("switches_pm", "video bitrate switches / min"),
                                      ("mos_user", "mean user MOS")]):
        for sl in [x for x in ("usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "echoslice") if x in set(df.slicer)]:
            for L, ls in ((2.0, ":"), (4.0, "-"), (6.0, "--")):
                h = df[(df.slicer == sl) & (df.seg_dur == L)].groupby("Ts")[metric].mean()
                a.plot(h.index, h.values, color=C[sl], ls=ls, marker="o", ms=2.5, lw=1.1,
                       label=f"{LABEL[sl]}, {L:.0f} s seg" if a is axs[0] else None)
        a.set_xscale("log")
        a.set_xlabel("slicer period T_s (s)")
        a.set_ylabel(lab)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=6.5, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_resonance.png"))


def fig_headroom(jsonl):
    """E5: outcome of forecast-then-allocate vs headroom h, one dot per seed."""
    from experiments.analyze import load
    df = load(jsonl)
    df = df[(df.exp == "E5") & df.slicer.str.startswith("forecast+")].copy()
    df["h"] = df.slicer.str.extract(r"forecast\+(\d+(?:\.\d+)?)%").astype(float)[0] / 100
    fams = [("2-slice, shareable", (df.n_game == 0) & (~df.strict)), ("2-slice, strict", (df.n_game == 0) & (df.strict)),
            ("3-slice, shareable", (df.n_game > 0) & (~df.strict))]
    fig, axs = plt.subplots(1, 3, figsize=(8.4, 2.8))
    for a, (title, m) in zip(axs, fams):
        g = df[m]
        for col, lab, colr in (("x_video", "video share", C["echoslice-lite"]), ("x_game", "game share", C["usage-prop"])):
            if col not in g or g[col].isna().all():
                continue
            a.scatter(g.h + np.random.default_rng(0).uniform(-0.01, 0.01, len(g)), g[col], s=12, color=colr, label=lab, zorder=3)
            mm = g.groupby("h")[col].median()
            a.plot(mm.index, mm.values, color=colr, lw=1.0)
        a.axvline(1 / 0.9 - 1, color="#8a8985", ls=":", lw=0.9)
        a.set_xscale("symlog", linthresh=0.1)
        a.set_xlabel("forecast headroom h")
        a.set_title(title, fontsize=8, color=TEXT2)
        a.set_ylim(0, 1)
    axs[0].set_ylabel("mean share in evaluation window")
    axs[0].text(1 / 0.9 - 1, 0.95, " h* = 1/0.9 - 1", fontsize=6.5, color=TEXT2, va="top")
    axs[-1].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_headroom.png"))


def fig_dynload(t, w):
    """E6: gap to the best static share under changing load, and the gaming
    slice's MOS per scoring window in the gaming-surge pattern."""
    pats = ["game_surge", "bulk_wave", "video_peak", "churn"]
    sls = [x for x in ["usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "echoslice", "static", "deploy-static",
                       "shared"] if x in set(t.slicer)]
    col = dict(C, static=REF["static"], shared=REF["shared"])
    col["deploy-static"] = REF["oracle"]
    lab = dict(LABEL, **{"deploy-static": "Static tuned at deploy"})
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.3), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    for a, strict in zip(axs[:2], (False, True)):
        g = t[t.strict == strict]
        for j, sl in enumerate(sls):
            h = g[g.slicer == sl].set_index("pattern").reindex(pats)
            if h.gap_pct.isna().all():
                continue
            xs = np.arange(len(pats)) + (j - len(sls) / 2) * 0.1
            yerr = np.vstack([h.gap_pct - h.gap_lo, h.gap_hi - h.gap_pct])
            mk = "o" if sl in C else ("s" if sl == "deploy-static" else "D")
            a.errorbar(xs, h.gap_pct, yerr=np.nan_to_num(yerr), fmt=mk, ms=4, color=col[sl], elinewidth=0.8, capsize=0,
                       label=lab[sl] if a is axs[0] else None)
        a.axhline(5, color="#e34948", lw=0.8, ls="--")
        a.axhline(0, color="#b5b4ae", lw=0.8)
        a.set_xticks(range(len(pats)))
        a.set_xticklabels([p.replace("_", "\n") for p in pats], fontsize=7)
        a.set_title("strict" if strict else "shareable", fontsize=8, color=TEXT2)
    axs[0].set_ylabel("QoE gap to best static share (%)")
    a = axs[2]
    if w is not None and len(w):
        g = w[(w.pattern == "game_surge") & (~w.strict) & (w.slice == "game")]
        for sl in sls:
            h = g[g.slicer == sl].sort_values("window")
            if len(h):
                a.plot(h.window, h.mos, marker="o", ms=3, color=col[sl], lw=1.3, ls="-" if sl in C else "--")
        a.set_xticks([0, 1, 2, 3])
        a.set_xticklabels(["200-500 s\nbefore", "500-800 s\nsurge", "800-1100 s\nafter", "1100-1200 s"], fontsize=6.5)
        a.set_ylabel("gaming-slice MOS")
        a.set_title("gaming surge, shareable", fontsize=8, color=TEXT2)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_dynload.png"))


def fig_e7(t, w):
    """E7: gap to the best whole-run static split per cell, with the clairvoyant per-window
    split as reference, and the day cycle window by window."""
    cells = [c for c in ["M1-video-heavy", "M2-gaming-heavy", "M3-bulk-heavy", "day_cycle", "flash_crowd"] if c in set(t.cell)]
    sls = [x for x in ["usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "echoslice", "static", "deploy-static",
                       "shared"] if x in set(t.slicer)]
    col = dict(C, static=REF["static"], shared=REF["shared"])
    col["deploy-static"] = REF["oracle"]
    lab = dict(LABEL, **{"deploy-static": "Static tuned at deploy"})
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.5), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    for a, strict in zip(axs[:2], (False, True)):
        g = t[t.strict == strict]
        for j, sl in enumerate(sls):
            h = g[g.slicer == sl].set_index("cell").reindex(cells)
            if h.gap_pct.isna().all():
                continue
            xs = np.arange(len(cells)) + (j - len(sls) / 2) * 0.09
            yerr = np.vstack([h.gap_pct - h.gap_lo, h.gap_hi - h.gap_pct])
            mk = "o" if sl in C else ("s" if sl == "deploy-static" else "D")
            a.errorbar(xs, h.gap_pct, yerr=np.nan_to_num(yerr), fmt=mk, ms=4, color=col[sl], elinewidth=0.8, capsize=0,
                       label=lab[sl])
        hd = g.drop_duplicates("cell").set_index("cell").reindex(cells).headroom_pct
        a.hlines(-hd, np.arange(len(cells)) - 0.4, np.arange(len(cells)) + 0.4, color="#0b0b0b", lw=1.0, ls="--",
                 label="Clairvoyant best split per window")
        a.axhline(0, color="#b5b4ae", lw=0.8)
        a.set_xticks(range(len(cells)))
        short = {"M1-video-heavy": "M1\nvideo-\nheavy", "M2-gaming-heavy": "M2\ngaming-\nheavy",
                 "M3-bulk-heavy": "M3\nbulk-\nheavy", "day_cycle": "day\ncycle", "flash_crowd": "flash\ncrowd"}
        a.set_xticklabels([short.get(c, c) for c in cells], fontsize=6.5)
        a.set_title("strict" if strict else "shareable", fontsize=8, color=TEXT2)
    axs[0].set_ylabel("QoE gap to best static split (%)")
    a = axs[2]
    if w is not None and len(w):
        g = w[(w.cell == "day_cycle") & (w.strict)]
        for sl in sls:
            h = g[g.slicer == sl].sort_values("window")
            if len(h):
                a.plot(h.window, h.mos, marker="o" if sl in C else ("s" if sl == "deploy-static" else "D"), ms=3,
                       color=col[sl], lw=1.3, ls="-" if sl in C else "--")
        a.set_xticks(range(6))
        a.set_xticklabels(["video-\nheavy", "", "gaming-\nheavy", "", "bulk-\nheavy", ""], fontsize=6.5)
        a.set_ylabel("mean user MOS in window")
        a.set_title("day cycle, strict (300 s windows)", fontsize=8, color=TEXT2)
    seen = {}
    for ax in axs[:2]:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=5, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_e7.png"))


def fig_e7_sla(t):
    """E7 trade-off: mean-QoE gap to the best static split against the SLA of the worst-served slice.
    Faint points are single cells; solid points are the mean over the five cells of each mode."""
    t = t[t.slicer != "deploy-static"].copy()
    t["sla_min"] = t[["sla_video", "sla_game", "sla_bulk"]].min(axis=1)
    sls = [x for x in ["usage-prop", "forecast+20%", "ol-qoe+10%", "echoslice-lite", "echoslice", "static", "shared"]
           if x in set(t.slicer)]
    col = dict(C, static=REF["static"], shared=REF["shared"])
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
    for a, strict in zip(axs, (False, True)):
        g = t[t.strict == strict]
        for sl in sls:
            h = g[g.slicer == sl]
            if not len(h):
                continue
            mk = "o" if sl in C else "D"
            a.scatter(h.gap_pct, h.sla_min, s=12, color=col[sl], alpha=0.25, lw=0, marker=mk)
            a.scatter(h.gap_pct.mean(), h.sla_min.mean(), s=46, color=col[sl], marker=mk, edgecolor="white",
                      lw=1.2, zorder=3, label=LABEL[sl])
        a.axvline(0, color="#b5b4ae", lw=0.8)
        a.set_xlabel("mean-QoE gap to best static split (%)")
        a.set_title("strict" if strict else "shareable", fontsize=8, color=TEXT2)
        a.annotate("better", xy=(0.04, 0.95), xycoords="axes fraction", fontsize=7, color=TEXT2, va="top")
    axs[0].set_ylabel("SLA met by the worst-served slice")
    axs[0].set_ylim(-0.02, 1.0)
    seen = {}
    for ax in axs:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_e7_sla.png"))


def _cell_title(cell, strict):
    short = {"M1-video-heavy": "M1 video-heavy", "M2-gaming-heavy": "M2 gaming-heavy", "M3-bulk-heavy": "M3 bulk-heavy",
             "day_cycle": "day cycle", "flash_crowd": "flash crowd"}
    return f"{short.get(cell, cell)}, {'strict' if strict else 'shareable'}"


def fig_frontier(c):
    """Final E7 figure: each family's (mean-QoE gap, worst-slice SLA) points per cell, against the front
    of all static splits of that cell (chosen with hindsight)."""
    cells = [x for x in ["M1-video-heavy", "M2-gaming-heavy", "M3-bulk-heavy", "day_cycle", "flash_crowd"] if x in set(c.cell)]
    fig, axs = plt.subplots(2, len(cells), figsize=(2.3 * len(cells) + 0.6, 5.2), squeeze=False)
    for ri, strict in enumerate((False, True)):
        for ci, cell in enumerate(cells):
            a = axs[ri, ci]
            g = c[(c.cell == cell) & (c.strict == strict)]
            fr = g[g.family == "Static splits (clairvoyant per cell)"].sort_values("gap_pct")
            if len(fr):
                a.step(fr.gap_pct, fr.sla_min, where="post", color=FAM_COLOR["Static splits (clairvoyant per cell)"],
                       lw=1.0, ls="--", label="Static splits (clairvoyant per cell)")
            for fam, col in FAM_COLOR.items():
                if fam.startswith("Static"):
                    continue
                h = g[g.family == fam]
                if not len(h):
                    continue
                h = h.sort_values("slicer")
                a.plot(h.gap_pct, h.sla_min, color=col, lw=1.0, marker=FAM_MARK[fam], ms=4.5, mec="white", mew=0.8,
                       label=fam, alpha=0.95)
            a.set_title(_cell_title(cell, strict), fontsize=7.5, color=TEXT2)
            a.set_ylim(-0.03, 1.0)
            a.axvline(0, color="#b5b4ae", lw=0.7)
            if ci == 0:
                a.set_ylabel("worst-slice SLA")
            if ri == 1:
                a.set_xlabel("mean-QoE gap (%)", fontsize=8)
            a.tick_params(labelsize=7)
    seen = {}
    for a in axs.ravel():
        for hh, ll in zip(*a.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.985, "better: up and to the left", fontsize=7, color=TEXT2, va="top")
    fig.tight_layout(rect=(0, 0.1, 1, 0.98))
    fig.savefig(os.path.join(OUT, "fig_frontier.png"))


def fig_ablation(t):
    piv = t.pivot_table(index="slicer", columns="cell", values="gap_pct")
    order = piv.mean(axis=1).sort_values().index.tolist()
    fig, a = plt.subplots(figsize=(6.4, 0.28 * len(order) + 1.2))
    y = np.arange(len(order))
    a.barh(y, piv.loc[order].mean(axis=1), color="#c9c8f0", height=0.6, label="mean over cells")
    for j, cell in enumerate(piv.columns):
        a.scatter(piv.loc[order, cell], y, s=10, color=REF["oracle"], zorder=3, label="single cell" if j == 0 else None)
    if "echoslice3" in order:
        a.axvline(piv.loc["echoslice3"].mean(), color="#6250d6", lw=1.0, ls="--", label="EchoSlice (v3)")
    a.set_yticks(y)
    a.set_yticklabels([LABEL.get(o, o) for o in order], fontsize=7)
    a.axvline(0, color="#b5b4ae", lw=0.8)
    a.set_xlabel("QoE gap to best static split (%)")
    a.invert_yaxis()
    a.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_ablation.png"))


IMP_ORDER = ["none", "delay2s", "delay5s", "drop20", "qnoise0.1", "qnoise0.3", "qoe-from-kpm"]


def fig_telemetry(t):
    m = t.groupby(["slicer", "impairment"]).gap_pct.mean().unstack()
    cols = [c for c in IMP_ORDER if c in m.columns]
    fig, a = plt.subplots(figsize=(6.4, 3.0))
    colors = dict(C, **{"echoslice3-l1": "#9085e9"})
    for sl in m.index:
        a.plot(range(len(cols)), m.loc[sl, cols], marker="o", ms=4, lw=1.4, color=colors.get(sl, REF["static"]),
               label=LABEL.get(sl, sl))
    a.set_xticks(range(len(cols)))
    a.set_xticklabels(cols, fontsize=7)
    a.axhline(0, color="#b5b4ae", lw=0.8)
    a.set_ylabel("QoE gap to best static split (%)")
    a.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_telemetry.png"))


def fig_theory(ke, cmp_, rz):
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.2))
    a = axs[0]
    apps = sorted(set(ke.cell))
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
    for i, app in enumerate(apps):
        g = ke[(ke.cell == app) & (ke.strict)].sort_values("h")
        if len(g):
            a.plot(g.h, g.x_app, marker="o", ms=3, color=pal[i % len(pal)], lw=1.2, label=app)
            r = cmp_[(cmp_.app == app) & (cmp_.strict)] if "strict" in cmp_ else cmp_[cmp_.app == app]
            if len(r) and np.isfinite(r.h_star_pred.iloc[0]):
                a.axvline(r.h_star_pred.iloc[0], color=pal[i % len(pal)], lw=0.8, ls=":")
    a.set_xlabel("forecast headroom h")
    a.set_ylabel("share of the app's slice (strict)")
    a.set_title("knife-edge (dotted: predicted h*)", fontsize=8, color=TEXT2)
    a.legend(fontsize=6)
    a = axs[1]
    if "h_star_pred" in cmp_:
        for strict, mk in ((True, "o"), (False, "s")):
            g = cmp_[cmp_.strict == strict]
            a.scatter(g.h_star_pred, g.h_star_meas, marker=mk, s=22, color="#6250d6" if strict else "#8a8985",
                      label="strict" if strict else "shareable")
            for _, r in g.iterrows():
                if np.isfinite(r.h_star_pred) and np.isfinite(r.h_star_meas):
                    a.annotate(r.app, (r.h_star_pred, r.h_star_meas), fontsize=6, color=TEXT2,
                               xytext=(3, 2), textcoords="offset points")
        lim = [0, max(0.3, float(np.nanmax([cmp_.h_star_pred.max(), cmp_.h_star_meas.max()])) + 0.02)]
        a.plot(lim, lim, color="#b5b4ae", lw=0.8)
    a.set_xlabel("predicted h* = 1/ratio - 1")
    a.set_ylabel("measured h*")
    a.set_title("predicted vs measured knife-edge", fontsize=8, color=TEXT2)
    a.legend(fontsize=7)
    a = axs[2]
    if rz is not None:
        agg = rz.groupby(["slicer", "Ts", "L"]).agg(xsd=("xsd", "mean"), H=("H", "first")).reset_index()
        for i, (sl, g) in enumerate(agg.groupby("slicer")):
            a.scatter(g.H, g.xsd, s=14, color=pal[i % len(pal)], label=sl)
    a.set_xlabel("predicted gain G at 1/segment")
    a.set_ylabel("std of the video share")
    a.set_title("resonance", fontsize=8, color=TEXT2)
    a.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_theory.png"))


def fig_convergence(c):
    cells = sorted(set(c.cell))
    fig, axs = plt.subplots(2, (len(cells) + 1) // 2, figsize=(9.6, 4.8), squeeze=False, sharey=True)
    colors = dict(C, **{"echoslice3-l1": "#9085e9", "forecast+20%": "#1baf7a"})
    for i, cell in enumerate(cells):
        a = axs.ravel()[i]
        g = c[c.cell == cell]
        for sl, h in g.groupby("slicer"):
            h = h.sort_values("minute")
            a.plot(h.minute, pd.Series(h.gap_pct.values).rolling(3, min_periods=1).mean(), lw=1.3,
                   color=colors.get(sl, REF["static"]), label=LABEL.get(sl, sl))
        a.axhline(0, color="#b5b4ae", lw=0.8)
        a.axhline(1, color="#b5b4ae", lw=0.6, ls=":")
        a.set_title(cell, fontsize=8, color=TEXT2)
        a.set_ylim(-3, 12)
        a.set_xlabel("minute", fontsize=8)
    axs[0, 0].set_ylabel("gap to best static (%)")
    axs[1, 0].set_ylabel("gap to best static (%)")
    seen = {}
    for a in axs.ravel():
        for hh, ll in zip(*a.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=6, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_convergence.png"))


def fig_drl(d):
    fig, a = plt.subplots(figsize=(5.6, 3.0))
    for reg, col in (("loop", "#008300"), ("twin", "#e34948")):
        g = d[d.regime == reg].sort_values("iter")
        if not len(g):
            continue
        a.plot(g["iter"], g.mean_utility, color=col, lw=1.2, label=f"{reg}: training episodes")
        if "val_utility" in g:
            v = g.dropna(subset=["val_utility"])
            a.plot(v["iter"], v.val_utility, color=col, lw=0, marker="o", ms=4, label=f"{reg}: validation")
    a.set_xlabel("PPO iteration")
    a.set_ylabel("mean step utility")
    a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_drl.png"))


if __name__ == "__main__":
    what = sys.argv[1:] or ["mechanism"]
    if "mechanism" in what:
        print(json.dumps(fig_mechanism(), indent=1, default=float))
    if "gap" in what:
        fig_gap(os.path.join(ROOT, "results", "e1_cells.csv"))
    if "pareto" in what:
        fig_pareto(os.path.join(ROOT, "results", "e1.jsonl"))
    if "headroom" in what:
        fig_headroom(os.path.join(ROOT, "results", "e245.jsonl"))
    if "resonance" in what:
        fig_resonance(os.path.join(ROOT, "results", "e245.jsonl"))
