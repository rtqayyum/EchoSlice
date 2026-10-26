"""Build every table and the new figures of the paper from the final campaign.

  python analysis/make_paper_assets.py <campaign root> <results/tables dir> <report figures dir>

(analysis/reproduce.sh runs it for you.) Tables go to analysis/tables/, figures to analysis/figures/.

<campaign root>      folder holding results/<EXP>/merged.jsonl (E13 is read for the app-response table)
<results/tables dir> the CSVs written by the campaign report
<hpc figures dir>    the figures written by the campaign report (copied for the panels kept as they are)

Per-cell gaps of E1, E6, E7 and E12 come from diagnostics/round3/final_cells.csv, written by
diagnostics/round3/final_analysis.py, so that every experiment uses the same metric: window-averaged
user MOS against the best static split chosen leave-one-seed-out. Nothing in the paper's tables is typed by hand.
"""
import json
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

ROOT, TAB, HFIG = sys.argv[1], sys.argv[2], sys.argv[3]
CELLS = os.path.join(REPO, "diagnostics", "round3", "final_cells.csv")
OT = os.path.join(HERE, "tables")
OF = os.path.join(HERE, "figures")
os.makedirs(OT, exist_ok=True)
os.makedirs(OF, exist_ok=True)

NAME = {"usage-prop": "Usage-proportional", "forecast+10%": "Forecast + 10\\%", "forecast+20%": "Forecast + 20\\%",
        "forecast+30%": "Forecast + 30\\%", "forecast+50%": "Forecast + 50\\%", "forecast-best": "Forecast, best $h$ per cell$^\\dagger$",
        "ol-qoe+10%": "Open-loop QoE", "ol-qoe+10%-sla1": "Open-loop QoE, $\\lambda{=}1$",
        "drl-twin": "PPO-Replay", "drl-loop": "PPO-Loop", "echoslice": "Online probing",
        "static": "Static equal", "shared": "No slicing (PF)",
        "echoslice3-l1": "EchoSlice, $\\lambda{=}1$", "echoslice3": "\\textbf{EchoSlice}",
        "prior-only": "Prior only", "probe-prior": "Probing from prior", "drl-prior": "PPO-Prior",
        "gated": "EchoSlice, gated trials", "qoe-feedback": "QoE feedback",
        "drl-loop-s1": "PPO-Loop, seed 1", "drl-loop-s2": "PPO-Loop, seed 2",
        "drl-prior-s1": "PPO-Prior, seed 1", "drl-prior-s2": "PPO-Prior, seed 2"}
PLAIN = {k: v.replace("\\%", "%").replace("\\textbf{", "").replace("}", "").replace("$\\lambda{=", "λ=").replace("$", "")
         .replace("^\\dagger", "") for k, v in NAME.items()}
PLAIN.update({"echoslice3-l1": "EchoSlice, λ=1", "ol-qoe+10%-sla1": "Open-loop QoE, λ=1"})
CELL = {"M1-video-heavy": "video-heavy", "M2-gaming-heavy": "gaming-heavy", "M3-bulk-heavy": "bulk-heavy",
        "day_cycle": "day cycle", "flash_crowd": "flash crowd", "game_surge": "gaming surge", "bulk_wave": "bulk wave",
        "video_peak": "video peak", "churn": "churn"}
E7C = ["M1-video-heavy", "M2-gaming-heavy", "M3-bulk-heavy", "day_cycle", "flash_crowd"]
E6C = ["game_surge", "bulk_wave", "video_peak", "churn"]

TEXT1, TEXT2, GRID, AX = "#0b0b0b", "#52514e", "#ecebe7", "#b5b4ae"
C = {"echoslice-lite": "#2a78d6", "usage-prop": "#eb6834", "forecast+20%": "#1baf7a", "ol-qoe+10%": "#eda100",
     "echoslice": "#e87ba4", "echoslice3": "#6250d6", "drl-loop": "#008300", "drl-twin": "#e34948", "static": "#8a8985",
     "prior-only": "#2a78d6", "drl-prior": "#52514e", "gated": "#b03ec4", "qoe-feedback": "#c98a0b",
     "probe-prior": "#7fb8e8"}
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": AX,
                     "axes.labelcolor": TEXT1, "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False, "figure.dpi": 200,
                     "lines.linewidth": 1.4, "font.family": "DejaVu Sans"})


def fmt(v, d=2):
    return "--" if v is None or not np.isfinite(v) else f"{v:.{d}f}"


def save(fig, name):
    fig.savefig(os.path.join(OF, name + ".png"), bbox_inches="tight", dpi=300)
    fig.savefig(os.path.join(OF, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)


def write(name, lines):
    open(os.path.join(OT, name + ".tex"), "w").write("\n".join(lines) + "\n")


D = pd.read_csv(CELLS)
R4DIR = os.path.join(REPO, "diagnostics", "round4")
R4 = os.path.join(R4DIR, "r4_cells.csv")
if os.path.exists(R4) and os.path.getsize(R4) > 5:
    _r4 = pd.read_csv(R4)
    D = pd.concat([D, _r4[_r4.src == "E15"].drop(columns=["src", "impairment"], errors="ignore")], ignore_index=True)
    H17 = _r4[_r4.src == "E17"].copy()
else:
    H17 = pd.DataFrame()
R6DIR = os.path.join(REPO, "diagnostics", "round5")
R6 = os.path.join(R6DIR, "r6_cells.csv")
if os.path.exists(R6) and os.path.getsize(R6) > 5:
    _r6 = pd.read_csv(R6)
    _keep = [c for c in D.columns if c in _r6.columns]
    D = pd.concat([D, _r6[_r6.exp != "E17"][_keep]], ignore_index=True)
    H17 = pd.concat([H17, _r6[_r6.exp == "E17"]], ignore_index=True)
D["cm"] = D.cell + "|" + D.strict.map({True: "T", False: "F"})
ADAPT = ["usage-prop", "forecast+10%", "forecast+20%", "forecast+30%", "forecast+50%", "ol-qoe+10%", "ol-qoe+10%-sla1",
         "drl-twin", "drl-loop", "echoslice", "static", "shared", "echoslice3-l1", "echoslice3",
         "prior-only", "probe-prior", "drl-prior"]
EQ = [s for s in ("prior-only", "probe-prior", "drl-prior") if s in set(D.slicer)]
NEW6 = [s for s in ("qoe-feedback", "gated") if s in set(D.slicer)]
PPOS = [s for s in ("drl-loop-s1", "drl-loop-s2", "drl-prior-s1", "drl-prior-s2") if s in set(D.slicer)]
ADAPT += NEW6 + PPOS
SUMMARY = {}


# ---------------------------------------------------------------- Table: main summary over E6 + E7
def with_best_forecast(sub):
    f = sub[sub.slicer.str.startswith("forecast")]
    fb = f.loc[f.groupby("cm").gap.idxmin()].copy()
    fb["slicer"] = "forecast-best"
    return pd.concat([sub, fb], ignore_index=True)


def tab_main():
    A = with_best_forecast(D[D.exp.isin(["E6", "E7"])])
    real = A[A.slicer.isin(ADAPT)]
    lowest = real.loc[real.groupby("cm").gap.idxmin()].slicer.value_counts()
    order = ["usage-prop", "forecast+10%", "forecast+20%", "forecast+30%", "forecast-best", "ol-qoe+10%", "ol-qoe+10%-sla1",
             "static", "echoslice", "drl-twin", "drl-loop"] + PPOS + EQ + NEW6 + ["echoslice3-l1", "echoslice3"]
    lines = ["\\begin{tabular}{lrrrrrrrr}", "\\toprule",
             " & \\multicolumn{2}{c}{Shifting mixes (10)} & \\multicolumn{2}{c}{Load changes (8)} & \\multicolumn{4}{c}{All 18} \\\\",
             "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-9}",
             "Slicer & mean & worst & mean & worst & mean & worst & SLA & best \\\\", "\\midrule"]
    rec = {}
    for sl in order:
        g = A[A.slicer == sl]
        e7, e6 = g[g.exp == "E7"], g[g.exp == "E6"]
        r = dict(e7m=e7.gap.mean(), e7w=e7.gap.max(), e6m=e6.gap.mean(), e6w=e6.gap.max(), m=g.gap.mean(), w=g.gap.max(),
                 sla=g.sla_min.mean(), best=int(lowest.get(sl, 0)))
        rec[sl] = r
        b = "--" if sl == "forecast-best" else str(r["best"])
        lines.append(f"{NAME[sl]} & {fmt(r['e7m'])} & {fmt(r['e7w'])} & {fmt(r['e6m'])} & {fmt(r['e6w'])} & "
                     f"{fmt(r['m'])} & {fmt(r['w'])} & {fmt(r['sla'])} & {b} \\\\")
        if sl in ("forecast-best", "ol-qoe+10%-sla1", "echoslice") or sl == (PPOS or ["drl-loop"])[-1] or \
                (EQ and sl == EQ[-1]) or (NEW6 and sl == NEW6[-1]):
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_main", lines)
    SUMMARY["main"] = rec
    sh = A[A.slicer == "shared"]
    SUMMARY["shared_shareable_only"] = dict(m=sh.gap.mean(), w=sh.gap.max(), sla=sh.sla_min.mean(), n=len(sh))


# ---------------------------------------------------------------- Table: every scenario family at once
def tab_overall():
    fams = [("Balanced", D[D.exp == "E1"]), ("Changing", D[D.exp.isin(["E6", "E7"])]), ("XR, L4S", D[D.exp == "E12"]),
            ("Held-out", H17)]
    order = ["forecast+20%", "static", "echoslice", "drl-twin", "drl-loop"] + PPOS + EQ + NEW6 + ["echoslice3"]
    lines = ["\\begin{tabular}{l" + "rr" * len(fams) + "rrr}", "\\toprule",
             "Slicer & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{f} ({len(set(zip(g.cell, g.strict)))})}}" for f, g in fams)
             + " & \\multicolumn{3}{c}{All} \\\\",
             "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(fams)))
             + f"\\cmidrule(lr){{{2 + 2 * len(fams)}-{4 + 2 * len(fams)}}}",
             " & " + " & ".join(["mean & worst"] * len(fams)) + " & mean & worst & $>2\\%$ \\\\", "\\midrule"]
    rec = {}
    for sl in order:
        row, allg = [NAME[sl]], []
        for f, g in fams:
            h = g[g.slicer == sl].gap if not g.empty else pd.Series(dtype=float)
            allg += list(h)
            row += [fmt(h.mean()) if len(h) else "--", fmt(h.max()) if len(h) else "--"]
        a = np.array(allg)
        rec[sl] = dict(n=len(a), m=float(a.mean()), w=float(a.max()), over2=int((a > 2).sum()))
        row += [fmt(a.mean()), fmt(a.max()), f"{int((a > 2).sum())}/{len(a)}"]
        lines.append(" & ".join(row) + " \\\\")
        if sl in ("static",) or sl == (PPOS or ["drl-loop"])[-1] or (EQ and sl == EQ[-1]) or (NEW6 and sl == NEW6[-1]):
            lines.append("\\midrule")
    lines[-1] = lines[-1].replace(NAME["echoslice3"], NAME["echoslice3"]) 
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_overall", lines)
    SUMMARY["overall"] = rec


# ---------------------------------------------------------------- Table: balanced cells (E1)
def tab_e1():
    E = D[D.exp == "E1"].copy()
    E["fam"] = [("3-slice" if "/0g/" not in c else "2-slice") + (" strict" if s else " shareable")
                for c, s in zip(E.cell, E.strict)]
    fams = ["2-slice shareable", "2-slice strict", "3-slice shareable", "3-slice strict"]
    order = ["usage-prop", "forecast+20%", "ol-qoe+10%", "static", "shared", "echoslice", "drl-twin", "drl-loop"] + EQ + ["echoslice3"]
    lines = ["\\begin{tabular}{l" + "rr" * len(fams) + "}", "\\toprule",
             "Slicer & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{x}}}" for x in fams) + " \\\\",
             "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(fams))),
             " & " + " & ".join(["mean & worst"] * len(fams)) + " \\\\", "\\midrule"]
    rec = {}
    for sl in order:
        row = [NAME[sl]]
        for fm in fams:
            g = E[(E.fam == fm) & (E.slicer == sl)]
            row += [fmt(g.gap.mean()) if len(g) else "--", fmt(g.gap.max()) if len(g) else "--"]
        lines.append(" & ".join(row) + " \\\\")
        g = E[E.slicer == sl]
        rec[sl] = dict(m=g.gap.mean(), w=g.gap.max(), n=len(g))
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_e1", lines)
    SUMMARY["E1"] = rec


# ---------------------------------------------------------------- Figure: per-cell gaps (E7 + E6)
def fig_cells():
    sls = ["echoslice3", "drl-loop", "drl-twin", "echoslice", "forecast+20%", "static", "ol-qoe+10%", "usage-prop"]
    cols = [(c, s) for c in E7C for s in (False, True)] + [(c, s) for c in E6C for s in (False, True)]
    M = np.full((len(sls), len(cols)), np.nan)
    for i, sl in enumerate(sls):
        for j, (c, s) in enumerate(cols):
            g = D[(D.cell == c) & (D.strict == s) & (D.slicer == sl)]
            if len(g):
                M[i, j] = g.gap.iloc[0]
    cmap = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#86b6ef", "#f0efec", "#f2a3a2", "#c62f2f"])
    norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6)
    fig, ax = plt.subplots(figsize=(7.16, 2.9))
    ax.imshow(np.clip(M, -6, 6), cmap=cmap, norm=norm, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if not np.isfinite(v):
                continue
            dark = abs(v) > 3.6
            txt = f"{v:.1f}" if abs(v) < 9.95 else f"{v:.0f}"
            txt = "0.0" if txt == "-0.0" else txt
            ax.text(j, i, txt, ha="center", va="center", fontsize=6.2,
                    color="white" if dark else TEXT1)
    ax.set_yticks(range(len(sls)), [PLAIN[s] for s in sls], fontsize=7)
    ax.set_xticks(range(len(cols)), ["sh." if not s else "str." for c, s in cols], fontsize=6.2)
    for k, c in enumerate(E7C + E6C):
        short = {"M1-video-heavy": "video-\nheavy", "M2-gaming-heavy": "gaming-\nheavy", "M3-bulk-heavy": "bulk-\nheavy",
                 "day_cycle": "day\ncycle", "flash_crowd": "flash\ncrowd", "game_surge": "gaming\nsurge",
                 "bulk_wave": "bulk\nwave", "video_peak": "video\npeak", "churn": "\nchurn"}[c]
        ax.text(2 * k + 0.5, -0.75, short, ha="center", va="bottom", fontsize=6.6, color=TEXT1, linespacing=1.1)
    ax.axvline(9.5, color="white", lw=3)
    ax.text(4.5, -2.25, "unbalanced and shifting mixes", ha="center", fontsize=7.2, color=TEXT2)
    ax.text(13.5, -2.25, "load changes in a 32/12/8 cell", ha="center", fontsize=7.2, color=TEXT2)
    ax.set_xticks(np.arange(-0.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sls), 1), minor=True)
    ax.grid(which="minor", color="white", lw=1.2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_ylim(len(sls) - 0.5, -2.6)
    save(fig, "fig_cells")


# ---------------------------------------------------------------- Table + figure: ablations (E9)
ABL = [("full", "Full method"), ("abl-prior-only", "Prior only, no trials"),
       ("abl-freeze-at-eval", "Trials stop when scoring starts"), ("abl-no-prior", "No prior (start from equal split)"),
       ("abl-no-moves", "No move on count changes"), ("abl-no-hold", "No hold (score at once)"),
       ("abl-hold6", "Hold 6 s"), ("abl-hold24", "Hold 24 s"), ("abl-pair-sign", "Sign search instead of SPSA"),
       ("abl-fixed-gain", "Fixed SPSA gains"), ("abl-share-space", "Learn shares, not rates"),
       ("abl-rate0.5", "Template rates $\\times 0.5$"), ("abl-rate0.5-noprobe", "Template $\\times 0.5$, no trials"),
       ("abl-rate2", "Template rates $\\times 2$"), ("abl-rate2-noprobe", "Template $\\times 2$, no trials")]
ABL_CELLS = [("M1T", "E7", "M1-video-heavy", True), ("M2F", "E7", "M2-gaming-heavy", False),
             ("M3T", "E7", "M3-bulk-heavy", True), ("dayT", "E7", "day_cycle", True), ("flashT", "E7", "flash_crowd", True),
             ("vpT", "E6", "video_peak", True)]


def ablation_table():
    t = pd.read_csv(os.path.join(TAB, "e9_ablations.csv"))
    rows = {}
    for key, _ in ABL:
        r = {}
        for cid, exp, cell, strict in ABL_CELLS:
            if key == "full":
                g = D[(D.exp == exp) & (D.cell == cell) & (D.strict == strict) & (D.slicer == "echoslice3")]
                r[cid] = (g.gap.iloc[0], g.sla_min.iloc[0]) if len(g) else (np.nan, np.nan)
            else:
                g = t[(t.cell == cid) & (t.slicer == key)]
                r[cid] = (g.gap_pct.iloc[0], g.sla_min.iloc[0]) if len(g) else (np.nan, np.nan)
        rows[key] = r
    return rows


def tab_ablation(rows):
    cids = [c[0] for c in ABL_CELLS]
    hdr = {"M1T": "Video", "M2F": "Gaming", "M3T": "Bulk", "dayT": "Day", "flashT": "Flash", "vpT": "Peak"}
    V = _r4("r4_variants.csv")

    def extra(key):
        out = []
        for c in cids:
            g = V[(V.cell == c) & (V.slicer == key)] if not V.empty else V
            out.append((g.gap.iloc[0], g.sla_min.iloc[0]) if len(g) else (np.nan, np.nan))
        return out
    labels = dict(ABL)
    labels.update({"abl-hold24": "Hold 24 s, burn-in 12 s", "full": "Full method (hold 12 s, burn-in 6 s)"})
    spec = ["full", "abl-prior-only", "abl-freeze-at-eval", None, "abl-no-prior", "abl-no-moves", None,
            "abl-no-hold", "abl-hold6", "abl-hold24", "hold36", "hold54", "hold60", "rand-order", "rand-order-hold54", None,
            "abl-pair-sign", "abl-fixed-gain", "abl-share-space", None,
            "count-activity", "count-linger10", "prior-only-activity", "prior-only-linger10"]
    labels.update({"count-activity": "Counts from radio activity", "count-linger10": "Counts kept 10 s after last data",
                   "prior-only-activity": "Prior only, activity counts", "prior-only-linger10": "Prior only, 10 s counts"})
    labels.update({"hold36": "Hold 36 s, burn-in 30 s", "hold54": "Hold 54 s, burn-in 48 s",
                   "hold60": "Hold 60 s, burn-in 54 s", "rand-order": "Random trial order",
                   "rand-order-hold54": "Random trial order, hold 54 s"})
    lines = ["\\begin{tabular}{l" + "r" * (len(cids) + 3) + "}", "\\toprule",
             "Variant & " + " & ".join(hdr[c] for c in cids) + " & mean & worst & SLA \\\\", "\\midrule"]
    rec = {}
    for key in spec:
        if key is None:
            lines.append("\\midrule")
            continue
        vv = [rows[key][c] for c in cids] if key in rows else extra(key)
        v = [x[0] for x in vv]
        sl = [x[1] for x in vv]
        if not np.isfinite(np.array(v, float)).any():
            continue
        rec[key] = dict(m=float(np.nanmean(v)), w=float(np.nanmax(v)), sla=float(np.nanmean(sl)))
        lines.append(labels[key] + " & " + " & ".join(fmt(x) for x in v) +
                     f" & {fmt(rec[key]['m'])} & {fmt(rec[key]['w'])} & {fmt(rec[key]['sla'])} \\\\")
    for key in ("abl-rate0.5", "abl-rate0.5-noprobe", "abl-rate2", "abl-rate2-noprobe"):
        v = [rows[key][c][0] for c in cids]
        s_ = [rows[key][c][1] for c in cids]
        rec[key] = dict(m=float(np.nanmean(v)), w=float(np.nanmax(v)), sla=float(np.nanmean(s_)))
    while lines[-1] == "\\midrule":
        lines.pop()
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_ablation", lines)
    SUMMARY["ablation"] = rec


def _r4(name):
    p = os.path.join(R4DIR, name)
    return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()


def tab_holds(rows):
    """Holds long enough for GCC, and random trial order (review round 4)."""
    V = _r4("r4_variants.csv")
    if V.empty:
        return
    cids = [c[0] for c in ABL_CELLS]
    hdr = {"M1T": "Video", "M2F": "Gaming", "M3T": "Bulk", "dayT": "Day", "flashT": "Flash", "vpT": "Peak"}

    def get(key):
        if key in rows:
            return [rows[key][c] for c in cids]
        out = []
        for c in cids:
            g = V[(V.cell == c) & (V.slicer == key)]
            out.append((g.gap.iloc[0], g.sla_min.iloc[0]) if len(g) else (np.nan, np.nan))
        return out
    spec = [("full", "Hold 12 s, burn-in 6 s (default)"), ("abl-hold24", "Hold 24 s, burn-in 12 s"),
            ("hold36", "Hold 36 s, burn-in 30 s"), ("hold54", "Hold 54 s, burn-in 48 s"), ("hold60", "Hold 60 s, burn-in 54 s"),
            ("rand-order", "Random trial order, hold 12 s"), ("rand-order-hold54", "Random trial order, hold 54 s"),
            ("abl-prior-only", "Prior only, no trials")]
    lines = ["\\begin{tabular}{l" + "r" * (len(cids) + 3) + "}", "\\toprule",
             "Variant & " + " & ".join(hdr[c] for c in cids) + " & mean & worst & SLA \\\\", "\\midrule"]
    rec = {}
    for key, lab in spec:
        vv = get(key)
        v = [x[0] for x in vv]
        sl = [x[1] for x in vv]
        if not np.isfinite(v).any():
            continue
        rec[key] = dict(m=float(np.nanmean(v)), w=float(np.nanmax(v)), sla=float(np.nanmean(sl)), cells=v)
        lines.append(lab + " & " + " & ".join(fmt(x) for x in v) +
                     f" & {fmt(rec[key]['m'])} & {fmt(rec[key]['w'])} & {fmt(rec[key]['sla'])} \\\\")
        if key in ("hold60", "rand-order-hold54"):
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_holds", lines)
    SUMMARY["holds"] = rec


def tab_templates(rows):
    """Template errors in one slice at a time, with and without trials (review round 4)."""
    V = _r4("r4_variants.csv")
    if V.empty:
        return
    cids = [c[0] for c in ABL_CELLS]

    def stat(key):
        if key in rows:
            v = [rows[key][c][0] for c in cids]
        else:
            v = []
            for c in cids:
                g = V[(V.cell == c) & (V.slicer == key)]
                v.append(g.gap.iloc[0] if len(g) else np.nan)
        return float(np.nanmean(v)), float(np.nanmax(v))
    spec = [("Video rate $\\times 0.5$", "video0.5", "video0.5-noprobe"), ("Video rate $\\times 2$", "video2", "video2-noprobe"),
            ("Gaming rate $\\times 0.5$", "game0.5", "game0.5-noprobe"), ("Gaming rate $\\times 2$", "game2", "game2-noprobe"),
            ("Both rates $\\times 0.5$", "abl-rate0.5", "abl-rate0.5-noprobe"), ("Both rates $\\times 2$", "abl-rate2", "abl-rate2-noprobe"),
            ("Right template", "full", "abl-prior-only")]
    lines = ["\\begin{tabular}{lrrrr}", "\\toprule",
             " & \\multicolumn{2}{c}{With trials} & \\multicolumn{2}{c}{Prior only} \\\\",
             "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}", "Template & mean & worst & mean & worst \\\\", "\\midrule"]
    rec = {}
    for lab, k1, k0 in spec:
        a, b = stat(k1), stat(k0)
        rec[k1] = dict(m=a[0], w=a[1], m0=b[0], w0=b[1])
        lines.append(f"{lab} & {fmt(a[0])} & {fmt(a[1])} & {fmt(b[0])} & {fmt(b[1])} \\\\")
        if k1 == "abl-rate2":
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_templates", lines)
    SUMMARY["templates"] = rec


def tab_heldout():
    """Workload families never used for tuning (review round 4)."""
    if H17.empty:
        return
    H = H17.copy()
    H["fam"] = H.cell.str.split(":").str[0]
    fams = [("bw40", "40 MHz"), ("sinr6", "SINR 6 dB"), ("seg2", "2 s segments")]
    sls = ["usage-prop", "forecast+20%", "ol-qoe+10%", "static", "echoslice", "drl-twin", "drl-loop",
           "prior-only", "probe-prior", "drl-prior", "echoslice3"]
    lines = ["\\begin{tabular}{l" + "rr" * len(fams) + "rrr}", "\\toprule",
             " & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{l}}}" for _, l in fams) + " & \\multicolumn{3}{c}{All 12} \\\\",
             "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(fams))) +
             f"\\cmidrule(lr){{{2 + 2 * len(fams)}-{4 + 2 * len(fams)}}}",
             "Slicer & " + " & ".join(["mean & worst"] * len(fams)) + " & mean & worst & SLA \\\\", "\\midrule"]
    rec = {}
    for sl in sls:
        g = H[H.slicer == sl]
        if g.empty:
            continue
        row = [NAME[sl]]
        for f, _ in fams:
            h = g[g.fam == f]
            row += [fmt(h.gap.mean()), fmt(h.gap.max())]
        rec[sl] = dict(m=g.gap.mean(), w=g.gap.max(), sla=g.sla_min.mean(),
                       fam={f: (g[g.fam == f].gap.mean(), g[g.fam == f].gap.max()) for f, _ in fams})
        row += [fmt(g.gap.mean()), fmt(g.gap.max()), fmt(g.sla_min.mean())]
        lines.append(" & ".join(row) + " \\\\")
        if sl in ("ol-qoe+10%", "drl-loop", "drl-prior"):
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_heldout", lines)
    SUMMARY["heldout"] = rec


def tab_politeness():
    """Politeness (offered load over capacity) by capacity per session, from the randomised share steps:
    tests the constant-beta assumption of the knife-edge model (review round 4)."""
    p = os.path.join(ROOT, "results", "E13", "merged.jsonl")
    if not os.path.exists(p):
        return
    rows = []
    for line in open(p):
        r = json.loads(line)
        j = r["job"]
        if j.get("role") != "steps" or not j["cell"].startswith(("video", "gaming", "xr")):
            continue
        names = r["names"]
        K = len(names)
        k = j["slicer"]["k"]
        A = np.array(r["slice_trace"], float)
        t, x, off, srv, prb, n = A[:, 0], A[:, 1 + k], A[:, 1 + K + k], A[:, 1 + 2 * K + k], A[:, 1 + 3 * K + k], A[:, 1 + 4 * K + k]
        rp = np.where(prb > 1, srv / np.maximum(prb, 1e-9), np.nan)
        rp = pd.Series(rp).ffill().bfill().rolling(20, min_periods=1).median().to_numpy()
        cap = x * 273 * rp
        ok = t > 60
        rows += [(j["cell"], c / max(nn, 1), o / max(c, 1e-6)) for c, o, nn in zip(cap[ok], off[ok], n[ok])]
    d = pd.DataFrame(rows, columns=["app", "cps", "ratio"])
    bins = [(1, 2), (2, 4), (4, 8), (8, 16), (16, 32), (32, 64)]
    apps = [("video-tput", "Video, throughput rule"), ("video-bola", "Video, BOLA"), ("video-dyn", "Video, DYNAMIC"),
            ("gaming-gcc", "Gaming, GCC"), ("xr-gcc", "XR, GCC")]
    lines = ["\\begin{tabular}{l" + "r" * len(bins) + "}", "\\toprule",
             "Capacity per session (Mb/s) & " + " & ".join(f"{a}--{b}" for a, b in bins) + " \\\\", "\\midrule"]
    rec = {}
    for app, lab in apps:
        g = d[d.app == app]
        vals = []
        for a, b in bins:
            h = g[(g.cps > a) & (g.cps <= b)]
            vals.append(float(h.ratio.median()) if len(h) >= 200 else np.nan)
        rec[app] = vals
        lines.append(lab + " & " + " & ".join(fmt(v) for v in vals) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_politeness", lines)
    SUMMARY["politeness_by_capacity"] = rec


def family_stats(A=None, key="paired"):
    """Paired comparison of EchoSlice with each baseline over a family of scenarios (default: the 18 shifting and
    changing scenarios): bootstrap of the mean difference (seeds resampled within each scenario) and Holm-adjusted
    per-scenario t-tests."""
    from scipy import stats
    if A is None:
        A = D[D.exp.isin(["E6", "E7"])]
    if A.empty:
        return
    if "cm" not in A:
        A = A.assign(cm=A.cell + "|" + A.strict.astype(str))
    rng = np.random.default_rng(0)

    def gm(sl):
        return {cm: json.loads(g.gaps.iloc[0]) for cm, g in A[A.slicer == sl].groupby("cm")}
    E = gm("echoslice3")
    rec = {}
    for other in ["drl-loop", "drl-twin", "drl-prior", "forecast+20%", "echoslice", "prior-only", "probe-prior", "static",
                  "ol-qoe+10%", "gated", "qoe-feedback", "drl-loop-s1", "drl-loop-s2", "drl-prior-s1", "drl-prior-s2"]:
        O = gm(other)
        cms = sorted(set(E) & set(O))
        if not cms:
            continue
        diffs = [np.array([E[c][k] - O[c][k] for k in E[c] if k in O[c]]) for c in cms]
        bs = np.mean([d[rng.integers(0, len(d), (4000, len(d)))].mean(1) for d in diffs], axis=0)
        p = [stats.ttest_1samp(d, 0).pvalue if d.std() > 0 else 1.0 for d in diffs]
        order = np.argsort(p)
        rej = np.zeros(len(p), bool)
        for i, idx in enumerate(order):
            if p[idx] <= 0.05 / (len(p) - i):
                rej[idx] = True
            else:
                break
        rec[other] = dict(n=len(cms), diff=float(np.mean([d.mean() for d in diffs])),
                          lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                          better=int(sum(r and d.mean() < 0 for d, r in zip(diffs, rej))),
                          worse=int(sum(r and d.mean() > 0 for d, r in zip(diffs, rej))))
    SUMMARY[key] = rec


def fig_ablation(rows):
    cids = [c[0] for c in ABL_CELLS]
    keys = [k for k, _ in ABL]
    labs = {k: l.replace("$\\times 0.5$", "×0.5").replace("$\\times 2$", "×2") for k, l in ABL}
    means = {k: np.nanmean([rows[k][c][0] for c in cids]) for k in keys}
    order = ["full"] + sorted([k for k in keys if k != "full"], key=lambda k: means[k])
    fig, ax = plt.subplots(figsize=(3.5, 3.6))
    for i, k in enumerate(order):
        v = np.array([rows[k][c][0] for c in cids], float)
        col = C["echoslice3"] if k == "full" else "#8a8985"
        ax.plot([np.nanmin(v), np.nanmax(v)], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.scatter(v, [i] * len(v), s=9, color=col, alpha=0.55, lw=0, zorder=2)
        ax.scatter([means[k]], [i], s=34, color=col, edgecolor="white", lw=1.0, zorder=3, marker="D")
    ax.axvline(means["full"], color=C["echoslice3"], lw=0.8, ls=":", zorder=0)
    ax.axvline(0, color=AX, lw=0.8, zorder=0)
    ax.set_yticks(range(len(order)), [labs[k] for k in order], fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel("QoE gap to best static split (%)")
    ax.scatter([], [], s=9, color="#8a8985", alpha=0.6, label="one cell")
    ax.scatter([], [], s=30, color="#8a8985", marker="D", label="mean of 6 cells")
    ax.legend(loc="upper right", fontsize=6.4, handletextpad=0.2)
    save(fig, "fig_ablation")


# ---------------------------------------------------------------- Theory check (E13)
def tab_theory():
    rp = pd.read_csv(os.path.join(TAB, "e13_app_response.csv")).set_index("app")
    km = pd.read_csv(os.path.join(TAB, "e13_knife_pred_vs_meas.csv"))
    meas = km.groupby("app").h_star_meas.agg(["min", "max"])
    order = [("video-tput", "Video, throughput rule"), ("video-bola", "Video, BOLA"), ("video-dyn", "Video, DYNAMIC"),
             ("gaming-gcc", "Gaming, GCC"), ("xr-gcc", "XR, GCC"), ("bulk-cubic", "Bulk, TCP Cubic"),
             ("bulk-prague", "Bulk, TCP Prague")]
    lines = ["\\begin{tabular}{lrrrrr}", "\\toprule",
             "Application & $\\tau$ (s) & $\\beta$ & $h^\\star$ predicted & $h^\\star$ measured & $1/(1+h^\\star_{\\mathrm{meas}})$ \\\\",
             "\\midrule"]
    rec = {}
    for app, lab in order:
        r = rp.loc[app]
        hm = meas.loc[app, "min"] if app in meas.index else np.nan
        imp = 1 / (1 + hm) if np.isfinite(hm) else np.nan
        hp = r.h_star_pred if r.ratio < 1 else np.nan
        rec[app] = dict(tau=r.tau_s, beta=r.ratio, hpred=r.h_star_pred, hmeas=hm, beta_implied=imp)
        lines.append(f"{lab} & {fmt(r.tau_s, 1)} & {fmt(r.ratio)} & {fmt(hp) if np.isfinite(hp) else 'none (greedy)'} & "
                     f"{fmt(hm)} & {fmt(imp)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_theory", lines)
    res = pd.read_csv(os.path.join(TAB, "e13_resonance.csv"))
    from scipy.stats import spearmanr
    rec["resonance"] = {sl: float(spearmanr(g.H, g.xsd).correlation) for sl, g in res.groupby("slicer")}
    SUMMARY["theory"] = rec


def fig_theory():
    ke = pd.read_csv(os.path.join(TAB, "e13_knife_edge.csv"))
    km = pd.read_csv(os.path.join(TAB, "e13_knife_pred_vs_meas.csv"))
    res = pd.read_csv(os.path.join(TAB, "e13_resonance.csv"))
    fig, ax = plt.subplots(1, 2, figsize=(7.16, 2.35), gridspec_kw={"width_ratios": [1.15, 1]})
    a = ax[0]
    apps = [("video-tput", "video, throughput rule", "#2a78d6"), ("video-bola", "video, BOLA", "#1baf7a"),
            ("gaming-gcc", "gaming, GCC", "#eb6834"), ("xr-gcc", "XR, GCC", "#6250d6")]
    for app, lab, col in apps:
        g = ke[(ke.cell == app) & (ke.strict == True)].sort_values("h")  # noqa: E712
        a.plot(g.h, g.x_app, color=col, lw=1.4, marker="o", ms=2.6, label=lab)
        hm = km[(km.app == app) & (km.strict == True)].h_star_meas.iloc[0]  # noqa: E712
        a.axvline(hm, color=col, lw=0.8, ls=":")
    a.set_xlabel("forecast headroom $h$")
    a.set_ylabel("share of the app's slice")
    a.set_title("knife-edge, strict mode (dotted: measured $h^\\star$)", fontsize=7.5, color=TEXT2)
    a.legend(fontsize=6.2, loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=2, columnspacing=1.0)
    b = ax[1]
    sty = {"forecast a=0.3": ("forecast + 20%, α=0.3", "#1baf7a", "s"), "usage a=0.2": ("usage, α=0.2", "#eda100", "o"),
           "usage a=0.5": ("usage, α=0.5", "#eb6834", "o"), "usage a=1": ("usage, α=1", "#e34948", "o")}
    for sl, g in res.groupby("slicer"):
        lab, col, mk = sty.get(sl, (sl, "#8a8985", "o"))
        b.scatter(g.H, g.xsd, s=12, color=col, marker=mk, lw=0, label=lab, alpha=0.9)
    b.set_xlabel("predicted gain $G$ at the segment frequency")
    b.set_ylabel("std of the video share")
    b.set_title("resonance", fontsize=7.5, color=TEXT2)
    b.legend(fontsize=6.4, loc="upper left")
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig_theory")


# ---------------------------------------------------------------- Convergence (E14)
def tab_conv():
    t = pd.read_csv(os.path.join(TAB, "e14_convergence.csv"))
    r4 = _r4("r4_conv.csv")
    if not r4.empty:
        t = pd.concat([t, r4], ignore_index=True)
    sls = ["forecast+20%", "ol-qoe+10%", "drl-loop", "echoslice"] + [x for x in ("prior-only", "probe-prior", "drl-prior")
                                                                       if x in set(t.slicer)] + ["echoslice3-l1", "echoslice3"]
    cells = ["M1F", "M1T", "M2F", "M2T", "M3F", "M3T"]
    lab = {"M1F": "Video sh.", "M1T": "Video str.", "M2F": "Gaming sh.", "M2T": "Gaming str.", "M3F": "Bulk sh.",
           "M3T": "Bulk str."}
    lines = ["\\begin{tabular}{l" + "r" * len(cells) + "r}", "\\toprule",
             "Slicer & " + " & ".join(lab[c] for c in cells) + " & last 10 min \\\\", "\\midrule"]
    rec = {}
    for sl in sls:
        g = t[t.slicer == sl].set_index("cell")
        mins = [g.minutes_to_1pct.get(c, np.nan) for c in cells]
        last = g.gap_last10.reindex(cells).mean()
        rec[sl] = dict(mins=mins, last=last, reached=int(np.isfinite(mins).sum()))
        lines.append(NAME[sl] + " & " + " & ".join("--" if not np.isfinite(m) else f"{m:.0f}" for m in mins) +
                     f" & {fmt(last)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_conv", lines)
    SUMMARY["conv"] = rec


# ---------------------------------------------------------------- XR and L4S (E12)
def tab_xr():
    E = D[D.exp == "E12"]
    l4 = pd.read_csv(os.path.join(TAB, "e12_xr_l4s.csv"))
    sls = ["usage-prop", "forecast+20%", "ol-qoe+10%", "static", "echoslice", "drl-twin", "drl-loop"] + EQ + ["echoslice3"]
    cols = [("X1-xr", False), ("X1-xr", True), ("X2-xr-l4s", False), ("X2-xr-l4s", True), ("X3-game-l4s", False),
            ("X3-game-l4s", True)]
    lab = {"X1-xr": "X1", "X2-xr-l4s": "X2", "X3-game-l4s": "X3"}
    lines = ["\\begin{tabular}{l" + "r" * (len(cols) + 2) + "}", "\\toprule",
             "Slicer & " + " & ".join(f"{lab[c]} {'str.' if s else 'sh.'}" for c, s in cols) + " & mean & L4S delay \\\\",
             "\\midrule"]
    rec = {}
    for sl in sls:
        v = []
        for c, s in cols:
            g = E[(E.cell == c) & (E.strict == s) & (E.slicer == sl)]
            v.append(g.gap.iloc[0] if len(g) else np.nan)
        q = l4[(l4.slicer == sl) & l4.cell.isin(["X2-xr-l4s", "X3-game-l4s"])].l4s_qdelay_ms.mean()
        rec[sl] = dict(m=float(np.nanmean(v)), w=float(np.nanmax(v)), q=float(q))
        lines.append(NAME[sl] + " & " + " & ".join(fmt(x) for x in v) + f" & {fmt(np.nanmean(v))} & {fmt(q)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_xr", lines)
    SUMMARY["E12"] = rec


# ---------------------------------------------------------------- Figures redrawn from the report tables
FAM = [("EchoSlice (v3)", "EchoSlice", C["echoslice3"], "o"), ("DRL, trained in loop", "PPO-Loop", C["drl-loop"], "D"),
       ("DRL, trained on replay", "PPO-Replay", C["drl-twin"], "v"), ("Forecast + h", "Forecast + h", C["forecast+20%"], "s"),
       ("Open-loop QoE + SLA", "Open-loop QoE", C["ol-qoe+10%"], "^")]


def fig_frontier():
    c = pd.read_csv(os.path.join(TAB, "e7_frontier_points.csv"))
    fig, axs = plt.subplots(2, 5, figsize=(7.16, 3.6), squeeze=False)
    for ri, strict in enumerate((False, True)):
        for ci, cell in enumerate(E7C):
            a = axs[ri, ci]
            g = c[(c.cell == cell) & (c.strict == strict)]
            fr = g[g.family.str.startswith("Static")].sort_values("gap_pct")
            if len(fr):
                a.step(fr.gap_pct, fr.sla_min, where="post", color="#8a8985", lw=0.9, ls="--", label="best static splits")
            for fam, lab, col, mk in FAM:
                h = g[g.family == fam].sort_values("slicer")
                if len(h):
                    a.plot(h.gap_pct, h.sla_min, color=col, lw=1.0, marker=mk, ms=3.6, mec="white", mew=0.6, label=lab)
            a.set_title(f"{CELL[cell]}, {'strict' if strict else 'shareable'}", fontsize=6.6, color=TEXT2)
            a.set_ylim(-0.03, 1.0)
            a.axvline(0, color=AX, lw=0.7)
            a.tick_params(labelsize=6)
            if ci == 0:
                a.set_ylabel("worst-slice SLA", fontsize=7)
            if ri == 1:
                a.set_xlabel("QoE gap (%)", fontsize=7)
    seen = {}
    for a in axs.ravel():
        for hh, ll in zip(*a.get_legend_handles_labels()):
            seen.setdefault(ll, hh)
    fig.legend(list(seen.values()), list(seen.keys()), loc="lower center", ncol=6, fontsize=6.6,
               bbox_to_anchor=(0.5, -0.01), columnspacing=1.2, handlelength=1.8)
    fig.tight_layout(rect=(0, 0.06, 1, 1), h_pad=0.8, w_pad=0.6)
    save(fig, "fig_frontier")


CONV_SL = [("echoslice3", "EchoSlice", C["echoslice3"], "-"), ("echoslice3-l1", "EchoSlice, λ=1", C["echoslice3"], "--"),
           ("drl-loop", "PPO-Loop", C["drl-loop"], "-"), ("echoslice", "Online probing", C["echoslice"], "-"),
           ("forecast+20%", "Forecast + 20%", C["forecast+20%"], "-"), ("ol-qoe+10%", "Open-loop QoE", C["ol-qoe+10%"], "-")]


def fig_convergence():
    t = pd.read_csv(os.path.join(TAB, "e14_curves.csv"))
    cells = ["M1F", "M1T", "M2F", "M2T", "M3F", "M3T"]
    title = {"M1F": "video-heavy, shareable", "M1T": "video-heavy, strict", "M2F": "gaming-heavy, shareable",
             "M2T": "gaming-heavy, strict", "M3F": "bulk-heavy, shareable", "M3T": "bulk-heavy, strict"}
    fig, axs = plt.subplots(2, 3, figsize=(7.16, 3.4), sharex=True, sharey=True)
    for a, cell in zip(axs.ravel(), cells):
        g = t[t.cell == cell]
        for sl, lab, col, ls in CONV_SL:
            h = g[g.slicer == sl].sort_values("minute")
            if len(h):
                a.plot(h.minute, h.gap_pct, color=col, ls=ls, lw=1.2, label=lab)
        a.axhline(0, color=AX, lw=0.7)
        a.axhline(1, color=AX, lw=0.6, ls=":")
        a.set_ylim(-2, 12)
        a.set_title(title[cell], fontsize=7, color=TEXT2)
        a.tick_params(labelsize=6.5)
    for a in axs[1]:
        a.set_xlabel("minute", fontsize=7)
    for a in axs[:, 0]:
        a.set_ylabel("QoE gap (%)", fontsize=7)
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=6, fontsize=6.6, bbox_to_anchor=(0.5, -0.01), columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "fig_convergence")


def fig_telemetry():
    t = pd.read_csv(os.path.join(TAB, "e10_telemetry.csv"))
    imps = [("none", "clean"), ("delay2s", "delay\n2 s"), ("delay5s", "delay\n5 s"), ("drop20", "20%\nlost"),
            ("qnoise0.1", "noise\n0.1"), ("qnoise0.3", "noise\n0.3"), ("qoe-from-kpm", "QoE\nfrom KPM")]
    sls = [("echoslice3", "EchoSlice", C["echoslice3"]), ("drl-loop", "PPO-Loop", C["drl-loop"]),
           ("forecast+20%", "Forecast + 20%", C["forecast+20%"]), ("ol-qoe+10%", "Open-loop QoE", C["ol-qoe+10%"])]
    r4 = _r4("r4_telemetry.csv")
    if not r4.empty:
        r4 = r4.rename(columns={"gap": "gap_pct"})
        t = pd.concat([t, r4[["cell", "impairment", "slicer", "gap_pct"]]], ignore_index=True)
        sls += [(k, NAME[k], C[k]) for k in ("prior-only", "drl-prior") if k in set(r4.slicer)]
    fig, ax = plt.subplots(figsize=(3.5, 2.3))
    xs = np.arange(len(imps))
    for sl, lab, col in sls:
        y = [t[(t.slicer == sl) & (t.impairment == k)].gap_pct.mean() for k, _ in imps]
        ax.plot(xs, y, color=col, marker="o", ms=3.2, lw=1.3, label=lab)
    ax.axhline(0, color=AX, lw=0.7)
    ax.set_xticks(xs, [l for _, l in imps], fontsize=5.8)
    ax.set_ylabel("QoE gap (%), mean of 4 cells", fontsize=7)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.legend(fontsize=6.2, loc="upper right", ncol=2, columnspacing=0.8)
    ax.set_ylim(-3.2, 4.2)
    save(fig, "fig_telemetry")


def fig_drl():
    d = pd.read_csv(os.path.join(TAB, "drl_learning.csv"))
    regs = [("loop", "PPO-Loop", C["drl-loop"]), ("twin", "PPO-Replay", C["drl-twin"])]
    pl = os.path.join(ROOT, "policies", "drl_prior_log.jsonl")
    if os.path.exists(pl):
        q = pd.DataFrame([json.loads(x) for x in open(pl)]).assign(regime="prior")
        d = pd.concat([d, q], ignore_index=True)
        regs.append(("prior", "PPO-Prior", C.get("drl-prior", "#52514e")))
    fig, ax = plt.subplots(figsize=(3.5, 2.3))
    for reg, lab, col in regs:
        g = d[d.regime == reg].sort_values("iter")
        ax.plot(g["iter"], g.mean_utility, color=col, lw=1.0, alpha=0.85, label=f"{lab}, training")
        v = g[g.val_utility.notna()]
        ax.scatter(v["iter"], v.val_utility, s=10, color=col, edgecolor="white", lw=0.5, zorder=3,
                   label=f"{lab}, validation")
    ax.set_xlabel("PPO iteration (40 episodes each)", fontsize=7)
    ax.set_ylabel("mean step utility", fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.legend(fontsize=5.6, loc="lower right", ncol=2, columnspacing=0.8)
    save(fig, "fig_drl")



# ---------------------------------------------------------------- final review round (E21-E24, real players)
def _r6(name):
    p = os.path.join(R6DIR, name)
    return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()


EV6 = [("ladder2", "Video rate $\\times 2$"), ("ladder0.5", "Video rate $\\times 0.5$"), ("sinr-6", "SINR $-6$ dB")]
SL6 = ["forecast+20%", "drl-loop", "drl-prior", "qoe-feedback", "probe-prior", "prior-only", "gated", "echoslice3"]


def tab_mismatch():
    M = _r6("r6_mismatch.csv")
    if M.empty:
        return
    sls = [x for x in SL6 if x in set(M.slicer)]
    lines = ["\\begin{tabular}{l" + "rr" * len(EV6) + "r}", "\\toprule",
             "Slicer & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{l}}}" for _, l in EV6) + " & No change \\\\",
             "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(EV6))) + f"\\cmidrule(lr){{{2 + 2 * len(EV6)}-{2 + 2 * len(EV6)}}}",
             " & " + " & ".join(["after & peak"] * len(EV6)) + " & after \\\\", "\\midrule"]
    rec = {}
    for sl in sls:
        row = [NAME.get(sl, sl)]
        r = {}
        for ev, _ in EV6:
            g = M[(M.slicer == sl) & (M.event == ev)]
            rc = g.recover_min
            r[ev] = dict(post=float(g.post_gap.mean()), post_w=float(g.post_gap.max()), peak=float(g.transient.max()),
                         rec=float(rc.max()) if rc.notna().all() else np.nan, lost=float(g.mos_min_lost.mean()))
            row += [fmt(r[ev]["post"]), fmt(r[ev]["peak"])]
        g = M[(M.slicer == sl) & (M.event == "none")]
        r["none"] = dict(post=float(g.post_gap.mean()))
        row.append(fmt(r["none"]["post"]))
        rec[sl] = r
        lines.append(" & ".join(row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_mismatch", lines)
    SUMMARY["mismatch"] = rec


def fig_mismatch():
    Cv = _r6("r6_curves.csv")
    if Cv.empty:
        return
    sls = [x for x in ["drl-loop", "qoe-feedback", "probe-prior", "prior-only", "gated", "echoslice3"] if x in set(Cv.slicer)]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.2), sharey=True)
    for ax, (ev, lab) in zip(axs, EV6):
        for sl in sls:
            g = Cv[(Cv.slicer == sl) & Cv.cell.str.endswith(":" + ev)].groupby("minute").gap.mean()
            ax.plot(g.index, g.values, color=C.get(sl, "#888"), lw=1.3 if sl == "echoslice3" else 1.0,
                    label=PLAIN.get(sl, NAME.get(sl, sl)).replace("EchoSlice, gated trials", "EchoSlice, gated"))
        ax.axhline(0, color=AX, lw=0.8)
        ax.set_title(lab.replace("$\\times 2$", "×2").replace("$\\times 0.5$", "×0.5").replace("$-6$", "−6"), fontsize=7.5)
        ax.set_xlabel("minutes after the change", fontsize=7)
    axs[0].set_ylabel("QoE gap (%), mean of 3 cells", fontsize=7)
    axs[-1].legend(fontsize=5.8, loc="upper right")
    save(fig, "fig_mismatch")


def tab_tfactor():
    T = _r6("r6_tfactor.csv")
    if T.empty:
        return
    fs = sorted(T.factor.dropna().unique())
    var = [("prior", "Prior only"), ("qoefb", "QoE feedback"), ("gated", "EchoSlice, gated trials"), ("echo", "EchoSlice")]
    lines = ["\\begin{tabular}{l" + "r" * len(fs) + "}", "\\toprule",
             "Factor & " + " & ".join(f"{f:g}" for f in fs) + " \\\\", "\\midrule",
             "\\multicolumn{" + str(len(fs) + 1) + "}{l}{Mean gap (\\%) over six scenarios} \\\\"]
    rec = {}
    for v, lab in var:
        g = T[T.variant == v].groupby("factor").gap
        m, w = g.mean(), g.max()
        rec[v] = dict(mean={float(k): float(x) for k, x in m.items()}, worst={float(k): float(x) for k, x in w.items()})
        lines.append(lab + " & " + " & ".join(fmt(m.get(f, np.nan)) for f in fs) + " \\\\")
    lines += ["\\midrule", "\\multicolumn{" + str(len(fs) + 1) + "}{l}{Worst scenario (\\%)} \\\\"]
    for v, lab in var:
        lines.append(lab + " & " + " & ".join(fmt(rec[v]["worst"].get(float(f), np.nan)) for f in fs) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_tfactor", lines)
    SUMMARY["tfactor"] = rec
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.1))
    cols = {"prior": C["prior-only"], "qoefb": C["qoe-feedback"], "gated": C["gated"], "echo": C["echoslice3"]}
    for v, lab in var:
        axs[0].plot(fs, [rec[v]["mean"].get(float(f), np.nan) for f in fs], marker="o", ms=3, color=cols[v], label=lab)
        axs[1].plot(fs, [rec[v]["worst"].get(float(f), np.nan) for f in fs], marker="o", ms=3, color=cols[v], label=lab)
    for ax, t in zip(axs, ("mean of six scenarios", "worst scenario")):
        ax.set_xscale("log", base=2)
        ax.set_xticks(fs, [f"{f:g}" for f in fs], fontsize=6.5)
        ax.axhline(0, color=AX, lw=0.8)
        ax.set_xlabel("template rate factor", fontsize=7)
        ax.set_ylabel(f"QoE gap (%), {t}", fontsize=7)
    axs[0].legend(fontsize=6)
    save(fig, "fig_tfactor")


CNT = [("count-session", "True session count"), ("count-activity", "Radio activity (last 1 s)")] + \
      [(f"count-linger{L}", f"Kept {L} s after last data") for L in (2, 5, 10, 20, 30)] + \
      [("prior-only-session", "Prior only, true count"), ("prior-only-activity", "Prior only, activity"),
       ("prior-only-linger10", "Prior only, kept 10 s")]
CNT_CELLS = [("L1-8s", "8/2/2, 8 s"), ("L2-8s", "12/4/2, 8 s"), ("L3-4s", "16/4/4, 4 s"), ("M1-8s", "56/4/2, 8 s")]


def tab_counts():
    T = _r6("r6_counts.csv")
    if T.empty:
        return
    lines = ["\\begin{tabular}{l" + "r" * len(CNT_CELLS) + "rrr}", "\\toprule",
             "Count source & " + " & ".join(l for _, l in CNT_CELLS) + " & mean & worst & count error \\\\", "\\midrule"]
    rec = {}
    for k, lab in CNT:
        g = T[T.slicer == k].set_index("cell")
        if g.empty:
            continue
        v = [float(g.gap.get(c, np.nan)) for c, _ in CNT_CELLS]
        e = float(np.nanmean(g.err_mean)) if "err_mean" in g and g.err_mean.notna().any() else 0.0
        rec[k] = dict(cells=v, m=float(np.nanmean(v)), w=float(np.nanmax(v)), err=e,
                      err_cells=[float(g.err_mean.get(c, np.nan)) if "err_mean" in g else 0.0 for c, _ in CNT_CELLS])
        lines.append(lab + " & " + " & ".join(fmt(x) for x in v) + f" & {fmt(rec[k]['m'])} & {fmt(rec[k]['w'])} & "
                     + f"{100 * e:.0f}\\% \\\\")
        if k in ("count-linger30",):
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_counts", lines)
    SUMMARY["counts"] = rec


DEP_CELLS = [("churn-abandon", "Churn, leave"), ("M1-abandon", "Video-heavy, leave"), ("files-bal", "Files, balanced"),
             ("files-bulkheavy", "Files, bulk-heavy")]
DEP_SL = ["usage-prop", "forecast+20%", "static", "drl-loop", "drl-prior", "qoe-feedback", "probe-prior", "prior-only",
          "gated", "echoslice3"]


def tab_depart():
    T = _r6("r6_depart.csv")
    if T.empty:
        return
    lines = ["\\begin{tabular}{l" + "r" * len(DEP_CELLS) + "rrr}", "\\toprule",
             "Slicer & " + " & ".join(l for _, l in DEP_CELLS) + " & mean & worst & left \\\\", "\\midrule"]
    rec = {}
    for sl in DEP_SL:
        g = T[T.slicer == sl].set_index("cell")
        if g.empty:
            continue
        v = [float(g.gap.get(c, np.nan)) for c, _ in DEP_CELLS]
        ab = float(np.nanmean([g.abandoned.get(c, np.nan) for c in ("churn-abandon", "M1-abandon")])) if "abandoned" in g else np.nan
        rec[sl] = dict(cells=v, m=float(np.nanmean(v)), w=float(np.nanmax(v)), left=ab,
                       files=[float(g.files.get(c, np.nan)) for c in ("files-bal", "files-bulkheavy")] if "files" in g else [])
        lines.append(NAME.get(sl, sl) + " & " + " & ".join(fmt(x) for x in v) +
                     f" & {fmt(rec[sl]['m'])} & {fmt(rec[sl]['w'])} & {fmt(ab, 1)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_depart", lines)
    SUMMARY["depart"] = rec


RP = os.path.join(R6DIR, "realplayer_summary.csv")
RPT = os.path.join(R6DIR, "realplayer_runs.jsonl")


def tab_realplayer():
    if not os.path.exists(RP):
        return
    A = pd.read_csv(RP)
    T = A[A.set == "short"].set_index("tag")
    L = A[A.set == "long"].set_index("tag") if (A.set == "long").any() else pd.DataFrame()
    grid = [t for t in T.index if t.startswith("static-")]
    best = max(grid, key=lambda t: T.mos[t])
    rows = [("usage", "Usage-proportional"), ("forecast+10%", "Forecast + 10\\%"), ("forecast+30%", "Forecast + 30\\%"),
            ("static-0.5", "Static equal"), (best, f"Best static (video {best.split('-')[1]})"),
            ("prior", "Prior only"), ("echoslice", "EchoSlice"),
            ("prior-rho0.5", "Prior only, template $\\times 0.5$"), ("echoslice-rho0.5", "EchoSlice, template $\\times 0.5$")]
    lines = ["\\begin{tabular}{lrrrrrrr}", "\\toprule",
             "Slicer & gap & worst & video share & video MOS & worst player & stall (s) & bulk MOS \\\\", "\\midrule",
             "\\multicolumn{8}{l}{240 s runs, 12 s hold scored over 6 s} \\\\"]
    rec = {}

    def add(Tb, t, lab, key):
        r = Tb.loc[t]
        rec[key] = {k: float(r[k]) for k in ("gap", "gap_max", "share", "mos_v", "min_v", "stall_s", "mos_b", "mos")}
        lines.append(f"{lab} & {fmt(r.gap)} & {fmt(r.gap_max)} & {fmt(r.share)} & {fmt(r.mos_v)} & {fmt(r.min_v)} & "
                     f"{fmt(r.stall_s, 1)} & {fmt(r.mos_b)} \\\\")
    for t, lab in rows:
        if t in T.index:
            add(T, t, lab, t)
            if t in ("forecast+30%", best, "echoslice"):
                lines.append("\\midrule")
    if not L.empty:
        lg = [t for t in L.index if t.startswith("static-")]
        lb = max(lg, key=lambda t: L.mos[t])
        lines += ["\\midrule", "\\multicolumn{8}{l}{600 s runs, 36 s hold scored over 24 s} \\\\"]
        for t, lab in [(lb, f"Best static (video {lb.split('-')[1]})"), ("prior", "Prior only"),
                       ("echoslice-h36", "EchoSlice"), ("prior-rho0.5", "Prior only, template $\\times 0.5$"),
                       ("echoslice-h36-rho0.5", "EchoSlice, template $\\times 0.5$")]:
            if t in L.index:
                add(L, t, lab, "long:" + t)
    lines += ["\\bottomrule", "\\end{tabular}"]
    write("tab_realplayer", lines)
    SUMMARY["realplayer"] = dict(best=best, rows=rec)


def fig_realplayer():
    if not os.path.exists(RPT):
        return
    runs = [json.loads(l) for l in open(RPT)]
    sel = [("usage", "Usage-proportional", C["usage-prop"]), ("forecast+10%", "Forecast + 10%", C["forecast+20%"]),
           ("prior", "Prior only", C["prior-only"]), ("echoslice", "EchoSlice", C["echoslice3"])]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.2))
    for t, lab, col in sel:
        rr = [r for r in runs if r["tag"] == t and r["seed"] == 1 and r.get("set", "short") == "short"]
        if not rr:
            continue
        tr = np.array(rr[0]["trace"])
        axs[0].plot(tr[:, 0], tr[:, 1], color=col, lw=1.0, label=lab)
        axs[1].plot(tr[:, 0], pd.Series(tr[:, 2]).rolling(10, min_periods=1).mean(), color=col, lw=1.0, label=lab)
    axs[0].set_ylabel("video share", fontsize=7)
    axs[1].set_ylabel("video slice served (Mb/s), 10 s mean", fontsize=7)
    for ax in axs:
        ax.set_xlabel("time (s)", fontsize=7)
    axs[0].legend(fontsize=6)
    save(fig, "fig_realplayer")

def main():
    tab_main()
    tab_e1()
    fig_cells()
    rows = ablation_table()
    tab_ablation(rows)
    fig_ablation(rows)
    tab_holds(rows)
    tab_templates(rows)
    tab_heldout()
    family_stats()
    tab_overall()
    family_stats(H17, "paired_heldout")
    tab_politeness()
    tab_theory()
    fig_theory()
    tab_conv()
    tab_xr()
    fig_frontier()
    fig_convergence()
    fig_telemetry()
    fig_drl()
    tab_mismatch()
    fig_mismatch()
    tab_tfactor()
    tab_counts()
    tab_depart()
    tab_realplayer()
    fig_realplayer()
    json.dump(SUMMARY, open(os.path.join(HERE, "assets_summary.json"), "w"), indent=1, default=float)
    print("tables:", sorted(os.listdir(OT)))
    print("figures:", sorted(os.listdir(OF)))


if __name__ == "__main__":
    main()
