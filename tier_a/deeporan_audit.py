#!/usr/bin/env python3
"""Tier A audit of the DeepORAN-Agent v2 dataset for the reaction-aware slicing paper.

Runs the checks from the proposal and writes a Markdown report, CSV tables
and figures to --out:

  A0  schema, provenance, run/scenario/slice counts, sampling intervals
  A0b correlation: lag-1 autocorrelation and effective sample size per run
  A0c SLA label saturation, latency quantiles, alternative thresholds
  A0d control-knob check: which columns could carry the slice quota
  A1  event study of throughput around control changes, TCP vs UDP scenarios
  A2  backhaul_delay as a natural experiment: TCP throughput vs added delay
  A3  open-loop forecaster: error near control changes, TCP vs UDP; UDP->TCP transfer
  A4  stack maps for simulator calibration (MCS/BLER/RSRP/PRB -> throughput, RTT, jitter)

All statistics are per scenario run (scenario_run_id); confidence intervals use a
block bootstrap over runs, never over rows.

Usage
  python deeporan_audit.py --data /path/to/release_dir --out audit_out
  python deeporan_audit.py --data "/path/*.parquet" --map mcs=dl_mcs --map action=ctrl_action
Needs: polars>=1.0, numpy, scikit-learn, matplotlib
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import polars as pl

# ---------------------------------------------------------------- columns
CANDIDATES = {
    "run": ["scenario_run_id", "run_id"],
    "scenario": ["scenario_id", "scenario", "scenario_name"],
    "ts": ["timestamp_utc", "timestamp", "ts", "time"],
    "ue": ["ue_id", "imsi", "rnti", "ue"],
    "slice": ["slice_id", "slice_type", "slice", "nssai", "sst"],
    "tput": ["throughput_mbps", "dl_throughput_mbps", "throughput", "tput_mbps"],
    "lat": ["latency_ms", "rtt_ms", "latency"],
    "jitter": ["jitter_ms", "jitter"],
    "loss": ["packet_loss_ratio", "loss_ratio", "packet_loss"],
    "prb": ["prb_utilization", "prb_util", "prb_usage"],
    "sla": ["sla_violation", "sla_violated", "sla_label"],
    "mcs": ["mcs", "dl_mcs", "ul_mcs", "mcs_index"],
    "bler": ["bler", "dl_bler", "ul_bler"],
    "rsrp": ["rsrp", "rsrp_dbm", "ss_rsrp"],
    "sinr": ["sinr", "sinr_db", "cqi"],
    "epoch": ["control_epoch", "epoch"],
    "action": ["control_action_id", "action_id", "control_action"],
    "proto": ["protocol", "traffic_protocol", "transport", "traffic_type", "l4_protocol"],
    "split": ["split"],
}
REQUIRED = ["run", "scenario", "ts", "slice", "tput"]

# Scenario -> transport class, from the proposal (iperf3 TCP vs UDP). Override with --proto-map.
TCP_SCEN = {"normal", "peak", "embb_heavy", "prb_contention", "backhaul_delay"}
UDP_SCEN = {"off_peak", "urllc_heavy", "mmtc_burst", "backhaul_loss"}


def resolve_columns(cols, overrides):
    m = {}
    low = {c.lower(): c for c in cols}
    for key, cands in CANDIDATES.items():
        if key in overrides:
            m[key] = overrides[key]
            continue
        hit = None
        for c in cands:
            if c in cols:
                hit = c
                break
            if c.lower() in low:
                hit = low[c.lower()]
                break
        if hit is None:
            for c in cols:
                if any(cc.lower() in c.lower() for cc in cands if len(cc) > 3):
                    hit = c
                    break
        if hit is not None:
            m[key] = hit
    return m


def find_files(data):
    if os.path.isdir(data):
        pq = sorted(glob.glob(os.path.join(data, "*.parquet")))
        csv = sorted(glob.glob(os.path.join(data, "*.csv")))
        files = pq if pq else csv
    else:
        files = sorted(glob.glob(data))
    if not files:
        sys.exit(f"no parquet/csv files found at {data}")
    return files


def load(files, cmap_over, max_rows=None):
    frames = []
    for f in files:
        lf = pl.scan_parquet(f) if f.endswith(".parquet") else pl.scan_csv(f, try_parse_dates=True)
        name = os.path.basename(f).lower()
        sp = "train" if "train" in name else "validation" if "valid" in name else "test" if "test" in name else "all"
        if "split" not in lf.collect_schema().names():
            lf = lf.with_columns(pl.lit(sp).alias("split"))
        frames.append(lf)
    lf = pl.concat(frames, how="diagonal_relaxed")
    cols = lf.collect_schema().names()
    cm = resolve_columns(cols, cmap_over)
    missing = [k for k in REQUIRED if k not in cm]
    if missing:
        sys.exit(f"required columns not found: {missing}. Columns are: {cols}. Use --map key=column.")
    keep = sorted(set(cm.values()))
    if max_rows:
        lf = lf.head(max_rows)
    df = lf.select(keep).collect()
    # canonical names
    df = df.rename({v: k for k, v in cm.items() if v in df.columns and k != v})
    ts = df.schema["ts"]
    if ts == pl.Utf8:
        df = df.with_columns(pl.col("ts").str.to_datetime(strict=False))
    elif ts in (pl.Float64, pl.Int64):
        unit = "ms" if df["ts"].max() > 1e11 else "s"
        mult = 1 if unit == "ms" else 1000
        df = df.with_columns((pl.col("ts") * mult).cast(pl.Int64).cast(pl.Datetime("ms")))
    if "ue" not in df.columns:
        df = df.with_columns(pl.lit(0).alias("ue"))
    for c in ("run", "scenario", "slice", "ue"):
        df = df.with_columns(pl.col(c).cast(pl.Utf8))
    return df, cm, cols


def transport_class(df, proto_map):
    if "proto" in df.columns:
        p = pl.col("proto").cast(pl.Utf8).str.to_lowercase()
        return df.with_columns(pl.when(p.str.contains("tcp")).then(pl.lit("TCP"))
                               .when(p.str.contains("udp")).then(pl.lit("UDP")).otherwise(pl.lit("other")).alias("tclass"))
    sc = pl.col("scenario").str.to_lowercase()
    tcp = TCP_SCEN | {k for k, v in proto_map.items() if v == "TCP"}
    udp = UDP_SCEN | {k for k, v in proto_map.items() if v == "UDP"}
    expr = pl.lit("other")
    for s in tcp:
        expr = pl.when(sc.str.contains(s)).then(pl.lit("TCP")).otherwise(expr)
    for s in udp:
        expr = pl.when(sc.str.contains(s)).then(pl.lit("UDP")).otherwise(expr)
    # 'off_peak' contains 'peak': resolve UDP first by applying it last
    return df.with_columns(expr.alias("tclass"))


def block_bootstrap(values_by_run, stat=np.mean, B=2000, seed=0):
    v = np.asarray(values_by_run, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    bs = [stat(rng.choice(v, len(v), replace=True)) for _ in range(B)]
    return (stat(v), np.percentile(bs, 2.5), np.percentile(bs, 97.5))


# ---------------------------------------------------------------- checks
def a0_schema(df, cm, allcols, R):
    R.h("A0. Schema and provenance")
    R.p(f"Rows: {df.height:,}. Columns in release: {len(allcols)}. Columns used: {len(df.columns)}.")
    R.table("Column mapping (canonical -> dataset)", [(k, v) for k, v in sorted(cm.items())], ["key", "column"])
    miss = [k for k in CANDIDATES if k not in cm]
    if miss:
        R.p("Not found (check DATA_DICTIONARY.md, then pass --map key=column): " + ", ".join(miss))
    g = df.group_by("scenario").agg(pl.col("run").n_unique().alias("runs"), pl.len().alias("rows"),
                                    pl.col("tclass").first().alias("class")).sort("scenario")
    R.table("Runs per scenario", g.rows(), g.columns)
    R.csv("a0_runs_per_scenario.csv", g)
    rr = df.group_by("run").agg(pl.len().alias("rows"), (pl.col("ts").max() - pl.col("ts").min()).dt.total_seconds().alias("dur_s"))
    R.p(f"Scenario runs: {rr.height}. Rows per run: median {rr['rows'].median():,.0f}, min {rr['rows'].min():,}, max {rr['rows'].max():,}. "
        f"Run duration: median {rr['dur_s'].median():.0f} s.")
    dts = (df.sort(["run", "ue", "slice", "ts"])
             .with_columns(pl.col("ts").diff().over(["run", "ue", "slice"]).dt.total_milliseconds().alias("dt_ms"))
             .filter(pl.col("dt_ms") > 0)["dt_ms"])
    if dts.len():
        R.p(f"Sampling interval per (run, UE, slice): median {dts.median():.0f} ms, p5 {dts.quantile(0.05):.0f} ms, "
            f"p95 {dts.quantile(0.95):.0f} ms.")
    R.p(f"UEs: {df['ue'].n_unique()}. Slices: {sorted(df['slice'].unique().to_list())}.")
    nulls = [(c, f"{df[c].null_count() / df.height:.3%}") for c in df.columns if df[c].null_count() > 0]
    if nulls:
        R.table("Null rates", nulls, ["column", "null share"])


def resample(df, grid_ms):
    aggs = [pl.col(c).mean().alias(c) for c in ("tput", "lat", "jitter", "loss", "prb", "mcs", "bler", "rsrp", "sinr")
            if c in df.columns and df.schema[c].is_numeric()]
    for c in ("epoch", "action", "sla", "tclass", "scenario", "split"):
        if c in df.columns:
            aggs.append(pl.col(c).last().alias(c))
    d = (df.sort("ts").group_by_dynamic("ts", every=f"{grid_ms}ms", group_by=["run", "ue", "slice"]).agg(aggs))
    return d.sort(["run", "ue", "slice", "ts"])


def a0b_correlation(rs, n_rows, R):
    R.h("A0b. Correlation and effective sample size")
    def ac1(s):
        s = np.asarray(s, dtype=float)
        s = s[np.isfinite(s)]
        if len(s) < 10 or s.std() == 0:
            return np.nan
        return np.corrcoef(s[:-1], s[1:])[0, 1]
    rows = []
    neff = 0.0
    for (run, ue, sl), g in rs.group_by(["run", "ue", "slice"]):
        r = ac1(g["tput"].to_numpy())
        n = g.height
        if np.isfinite(r):
            neff += n * (1 - r) / (1 + r)
        rows.append((run, sl, r, n))
    rr = np.array([x[2] for x in rows], dtype=float)
    R.p(f"Lag-1 autocorrelation of throughput on the resampled grid: median {np.nanmedian(rr):.2f} "
        f"(IQR {np.nanpercentile(rr, 25):.2f} to {np.nanpercentile(rr, 75):.2f}).")
    R.p(f"Effective sample size (AR(1) approximation, summed over series): about {neff:,.0f}, versus {n_rows:,} rows. "
        f"Report per-run results and block-bootstrap over scenario_run_id.")


def a0c_sla(df, R):
    R.h("A0c. SLA label saturation")
    if "sla" not in df.columns:
        R.p("No SLA column found.")
        return
    s = pl.col("sla").cast(pl.Float64)
    R.p(f"Overall violation share: {df.select(s.mean()).item():.1%}.")
    g = df.group_by("slice").agg(s.mean().alias("violation_share"), pl.len().alias("rows")).sort("slice")
    R.table("Violation share per slice", [(a, f"{b:.1%}", c) for a, b, c in g.rows()], ["slice", "violation", "rows"])
    g2 = df.group_by(["scenario", "slice"]).agg(s.mean().alias("v")).pivot(on="slice", index="scenario", values="v").sort("scenario")
    R.csv("a0c_violation_by_scenario_slice.csv", g2)
    if "lat" in df.columns:
        q = df.group_by("slice").agg([pl.col("lat").quantile(x).alias(f"p{int(x*100)}") for x in (0.05, 0.5, 0.95, 0.99)]).sort("slice")
        R.table("Latency quantiles (ms) per slice", [tuple([r[0]] + [f"{v:.2f}" for v in r[1:]]) for r in q.rows()], q.columns)
        thr = [1, 5, 10, 20, 50]
        rows = []
        for sl in sorted(df["slice"].unique().to_list()):
            l = df.filter(pl.col("slice") == sl)["lat"]
            rows.append(tuple([sl] + [f"{(l > t).mean():.1%}" for t in thr]))
        R.table("Share of rows above alternative latency thresholds", rows, ["slice"] + [f">{t} ms" for t in thr])
        R.p("If the ping path crosses gNB, UPF and an external DN on separate VMs, a 1 ms URLLC target cannot be met. "
            "Relabel from RAN-segment latency or app-level thresholds before using the label.")


def a0d_knob(df, allcols, R):
    R.h("A0d. Control knob check")
    hits = [c for c in allcols if any(k in c.lower() for k in ("prb", "ratio", "quota", "share", "buffer", "rlc", "pdcp", "dl_", "ul_", "action", "epoch"))]
    R.p("Columns that may carry the slice quota or DL resources: " + (", ".join(hits) if hits else "none"))
    if "action" in df.columns:
        na = df["action"].n_unique()
        R.p(f"Distinct control actions: {na}.")
        if "prb" in df.columns:
            g = df.group_by(["slice", "action"]).agg(pl.col("prb").mean().alias("prb_mean"), pl.len().alias("rows")).sort(["slice", "action"])
            R.csv("a0d_prb_by_action.csv", g)
            R.p("Mean prb_utilization per (slice, action) written to a0d_prb_by_action.csv. If PRB use moves with the action, "
                "the action id encodes the quota; if not, the quota is not observable in v2.")


def change_points(rs):
    key = "action" if "action" in rs.columns else ("epoch" if "epoch" in rs.columns else None)
    if key is None:
        return None, key
    ch = (rs.with_columns((pl.col(key) != pl.col(key).shift(1)).over(["run", "ue", "slice"]).fill_null(False).alias("chg")))
    return ch, key


def a1_event_study(rs, grid_ms, R, pre_s=5.0, post_s=10.0):
    R.h("A1. Event study around control changes")
    ch, key = change_points(rs)
    if ch is None:
        R.p("No control_action_id or control_epoch column: event study skipped.")
        return None
    pre, post = int(pre_s * 1000 / grid_ms), int(post_s * 1000 / grid_ms)
    curves = {"TCP": [], "UDP": [], "other": []}
    per_run = {"TCP": {}, "UDP": {}, "other": {}}
    for (run, ue, sl), g in ch.group_by(["run", "ue", "slice"]):
        y = g["tput"].to_numpy().astype(float)
        c = np.where(g["chg"].to_numpy())[0]
        cls = g["tclass"][0]
        for i in c:
            if i - pre < 0 or i + post >= len(y):
                continue
            base = np.nanmean(y[i - pre:i])
            if not np.isfinite(base) or base <= 0:
                continue
            w = y[i - pre:i + post] / base
            curves[cls].append(w)
            per_run[cls].setdefault(run, []).append(np.nanmean(np.abs(w[pre:] - 1.0)))
    out = {}
    rows = []
    for cls, cv in curves.items():
        if not cv:
            continue
        a = np.vstack(cv)
        out[cls] = a
        runs = [np.mean(v) for v in per_run[cls].values()]
        m, lo, hi = block_bootstrap(runs)
        rows.append((cls, len(cv), len(runs), f"{m:.3f} [{lo:.3f}, {hi:.3f}]"))
    R.table(f"Mean |relative throughput change| in the {post_s:.0f} s after a change of {key}",
            rows, ["class", "events", "runs", "mean abs change, 95% CI over runs"])
    R.p("A reactive (TCP) class should show a clear step after changes; open-loop UDP should stay flat unless the "
        "quota binds. A flat TCP curve means v2 controls did not bind, which is itself a finding for the v3 design.")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        tt = (np.arange(-pre, post) * grid_ms) / 1000.0
        fig, ax = plt.subplots(figsize=(6, 3.5))
        for cls, a in out.items():
            mu = np.nanmean(a, 0)
            se = np.nanstd(a, 0) / np.sqrt(max(a.shape[0], 1))
            ax.plot(tt, mu, label=f"{cls} (n={a.shape[0]})")
            ax.fill_between(tt, mu - 1.96 * se, mu + 1.96 * se, alpha=0.2)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel(f"time from {key} change (s)")
        ax.set_ylabel("throughput / pre-change mean")
        ax.legend(frameon=False)
        fig.tight_layout()
        R.fig(fig, "a1_event_study.png")
    except Exception as e:
        R.p(f"(figure skipped: {e})")
    return out


def a2_backhaul_delay(rs, R):
    R.h("A2. backhaul_delay as a natural experiment")
    sc = rs["scenario"].str.to_lowercase()
    bd = rs.filter(sc.str.contains("backhaul_delay"))
    nm = rs.filter(sc == "normal")
    if bd.height == 0 or nm.height == 0:
        R.p("Needs both 'normal' and 'backhaul_delay' scenarios; skipped.")
        return
    def per_run(d):
        return d.group_by(["run", "slice"]).agg(pl.col("tput").mean().alias("tput"),
                                                 (pl.col("lat").mean() if "lat" in d.columns else pl.lit(np.nan)).alias("lat"))
    a, b = per_run(nm), per_run(bd)
    rows = []
    for sl in sorted(set(a["slice"].to_list()) & set(b["slice"].to_list())):
        ta = a.filter(pl.col("slice") == sl)["tput"].to_numpy()
        tb = b.filter(pl.col("slice") == sl)["tput"].to_numpy()
        la = a.filter(pl.col("slice") == sl)["lat"].to_numpy()
        lb = b.filter(pl.col("slice") == sl)["lat"].to_numpy()
        rng = np.random.default_rng(1)
        el = []
        for _ in range(2000):
            xa, xb = rng.choice(ta, len(ta)), rng.choice(tb, len(tb))
            ya, yb = rng.choice(la, len(la)), rng.choice(lb, len(lb))
            if np.mean(xa) > 0 and np.mean(ya) > 0 and np.mean(yb) != np.mean(ya):
                el.append(np.log(np.mean(xb) / np.mean(xa)) / np.log(np.mean(yb) / np.mean(ya)))
        e = np.log(ta.mean() / tb.mean() if tb.mean() > 0 else np.nan)
        rows.append((sl, len(ta), len(tb), f"{ta.mean():.2f}", f"{tb.mean():.2f}", f"{np.nanmean(la):.1f}", f"{np.nanmean(lb):.1f}",
                     f"{np.median(el):.2f} [{np.percentile(el, 2.5):.2f}, {np.percentile(el, 97.5):.2f}]" if el else "n/a"))
    R.table("Throughput and latency, normal vs backhaul_delay (per-run means)", rows,
            ["slice", "runs normal", "runs delay", "tput normal", "tput delay", "lat normal", "lat delay", "elasticity d log tput / d log RTT [95% CI]"])
    R.p("Loss-based TCP in steady state follows roughly throughput ~ 1/RTT (elasticity near -1) when the bottleneck is the window; "
        "an elasticity near 0 means the bottleneck is elsewhere (radio share or iperf3 target rate).")


def a3_forecaster(rs, grid_ms, R, horizon_s=1.0, nlags=10):
    R.h("A3. Open-loop forecaster: where does it fail?")
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception:
        R.p("scikit-learn missing; skipped.")
        return
    h = max(1, int(horizon_s * 1000 / grid_ms))
    ch, key = change_points(rs)
    d = ch if ch is not None else rs.with_columns(pl.lit(False).alias("chg"))
    # slice-level demand series (sum over UEs)
    agg = [pl.col("tput").sum().alias("tput")]
    for c in ("prb", "lat"):
        if c in d.columns:
            agg.append(pl.col(c).mean().alias(c))
    agg += [pl.col("chg").any().alias("chg"), pl.col("tclass").first().alias("tclass"), pl.col("split").first().alias("split")]
    s = d.group_by(["run", "slice", "ts"]).agg(agg).sort(["run", "slice", "ts"])
    feats = []
    ex = []
    for l in range(1, nlags + 1):
        ex.append(pl.col("tput").shift(l).over(["run", "slice"]).alias(f"tput_l{l}"))
        feats.append(f"tput_l{l}")
    for c in ("prb", "lat"):
        if c in s.columns:
            ex.append(pl.col(c).shift(1).over(["run", "slice"]).alias(f"{c}_l1"))
            feats.append(f"{c}_l1")
    ex.append(pl.col("tput").shift(-h).over(["run", "slice"]).alias("y"))
    # time since last control change (in steps), to split errors into near / far from changes
    s = s.with_columns(ex).with_columns(pl.col("chg").cast(pl.Int32).cum_sum().over(["run", "slice"]).alias("seg"))
    s = s.with_columns(pl.int_range(pl.len()).over(["run", "slice", "seg"]).alias("since_chg"))
    s = s.drop_nulls(feats + ["y"])
    s = s.with_columns(pl.col("slice").cast(pl.Categorical).to_physical().alias("slice_code"))
    feats.append("slice_code")
    runs = s["run"].unique().sort().to_list()
    rng = np.random.default_rng(0)
    test_runs = set(rng.choice(runs, max(1, len(runs) // 4), replace=False).tolist()) if "split" not in s.columns or \
        s["split"].n_unique() < 2 else set(s.filter(pl.col("split") != "train")["run"].unique().to_list())
    rows = []
    for train_cls in ("UDP", "TCP"):
        tr = s.filter((pl.col("tclass") == train_cls) & (~pl.col("run").is_in(list(test_runs))))
        if tr.height < 500:
            continue
        mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.1)
        mdl.fit(tr.select(feats).to_numpy(), tr["y"].to_numpy())
        for test_cls in ("UDP", "TCP"):
            te = s.filter((pl.col("tclass") == test_cls) & (pl.col("run").is_in(list(test_runs))))
            if te.height < 100:
                continue
            p = mdl.predict(te.select(feats).to_numpy())
            err = np.abs(p - te["y"].to_numpy())
            scale = max(np.mean(np.abs(te["y"].to_numpy())), 1e-9)
            near = te["since_chg"].to_numpy() < h + int(5000 / grid_ms)
            per_run = []
            for r in te["run"].unique().to_list():
                m = (te["run"] == r).to_numpy()
                per_run.append(err[m].mean() / scale)
            m_, lo, hi = block_bootstrap(per_run)
            rows.append((train_cls, test_cls, te["run"].n_unique(), f"{m_:.3f} [{lo:.3f}, {hi:.3f}]",
                         f"{err[near].mean() / scale:.3f}" if near.any() else "n/a",
                         f"{err[~near].mean() / scale:.3f}" if (~near).any() else "n/a"))
    R.table(f"Normalised MAE of a {horizon_s:.0f} s-ahead slice-throughput forecaster (gradient boosting on lags)",
            rows, ["train", "test", "test runs", "nMAE [95% CI over runs]", "nMAE within 5 s after a change", "nMAE elsewhere"])
    R.p("Reactivity shows up as a larger error just after control changes on TCP runs than on UDP runs, for the same model. "
        "UDP->TCP transfer error mixes reactivity with plain distribution shift, so use the near/far split as the main evidence.")


def a4_stack_maps(df, R):
    R.h("A4. Stack maps for simulator calibration")
    have = [c for c in ("mcs", "bler", "rsrp", "sinr", "prb") if c in df.columns]
    if "prb" not in have:
        R.p("No PRB column; stack maps skipped.")
        return
    d = df.filter(pl.col("prb") > 0.02)
    d = d.with_columns((pl.col("tput") / pl.col("prb")).alias("tput_per_prbshare"))
    if "mcs" in have:
        t = (d.with_columns(pl.col("mcs").round(0).alias("mcs_bin"))
               .group_by(["slice", "mcs_bin"]).agg(pl.len().alias("rows"),
                                                    pl.col("tput_per_prbshare").median().alias("tput_per_prbshare_median"),
                                                    *( [pl.col("bler").mean().alias("bler_mean")] if "bler" in have else []),
                                                    *( [pl.col("lat").median().alias("lat_median")] if "lat" in d.columns else []),
                                                    *( [pl.col("jitter").median().alias("jitter_median")] if "jitter" in d.columns else []))
               .sort(["slice", "mcs_bin"]))
        R.csv("a4_stack_map_by_mcs.csv", t)
        R.p("Per-MCS median throughput per unit of PRB share, BLER, latency and jitter written to a4_stack_map_by_mcs.csv "
            "(feed this to the simulator's link layer).")
    if "rsrp" in have:
        t = (d.with_columns((pl.col("rsrp") / 2).round(0) * 2).group_by(["slice", "rsrp"]).agg(
            pl.len().alias("rows"), pl.col("tput_per_prbshare").median().alias("tput_per_prbshare_median")).sort(["slice", "rsrp"]))
        R.csv("a4_stack_map_by_rsrp.csv", t)
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.model_selection import GroupKFold
        X = d.select([c for c in have]).to_numpy()
        y = d["tput"].to_numpy()
        grp = d["run"].to_numpy()
        if len(y) > 2000:
            sc = []
            for tr, te in GroupKFold(n_splits=min(5, len(np.unique(grp)))).split(X, y, grp):
                m = HistGradientBoostingRegressor(max_iter=200).fit(X[tr], y[tr])
                p = m.predict(X[te])
                sc.append(1 - np.sum((p - y[te]) ** 2) / np.sum((y[te] - y[te].mean()) ** 2))
            R.p(f"Throughput ~ f({', '.join(have)}): R^2 = {np.mean(sc):.2f} (group k-fold over runs).")
    except Exception as e:
        R.p(f"(stack-map fit skipped: {e})")


# ---------------------------------------------------------------- report
class Report:
    def __init__(self, out):
        self.out = out
        os.makedirs(out, exist_ok=True)
        self.lines = ["# DeepORAN v2 audit (Tier A)", "", f"Generated {time.strftime('%Y-%m-%d %H:%M')}", ""]

    def h(self, t):
        self.lines += ["", f"## {t}", ""]
        print(f"\n== {t}", flush=True)

    def p(self, t):
        self.lines += [t, ""]
        print(t, flush=True)

    def table(self, title, rows, cols):
        self.lines += [f"**{title}**", "", "| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
        for r in rows:
            self.lines.append("| " + " | ".join(str(x) for x in r) + " |")
        self.lines.append("")
        print(title)
        for r in rows[:30]:
            print("  ", r)

    def csv(self, name, df):
        df.write_csv(os.path.join(self.out, name))

    def fig(self, fig, name):
        fig.savefig(os.path.join(self.out, name), dpi=160)
        self.lines += [f"![{name}]({name})", ""]

    def save(self):
        with open(os.path.join(self.out, "AUDIT_REPORT.md"), "w") as f:
            f.write("\n".join(self.lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="release directory or glob of parquet/csv files")
    ap.add_argument("--out", default="audit_out")
    ap.add_argument("--map", action="append", default=[], help="override a column: key=column (keys: %s)" % ", ".join(CANDIDATES))
    ap.add_argument("--proto-map", action="append", default=[], help="scenario=TCP|UDP")
    ap.add_argument("--grid-ms", type=int, default=100)
    ap.add_argument("--max-rows", type=int, default=None, help="for a quick dry run")
    a = ap.parse_args()
    over = dict(kv.split("=", 1) for kv in a.map)
    pmap = {k.lower(): v.upper() for k, v in (kv.split("=", 1) for kv in a.proto_map)}
    t0 = time.time()
    files = find_files(a.data)
    R = Report(a.out)
    R.p("Files: " + ", ".join(os.path.basename(f) for f in files))
    df, cm, allcols = load(files, over, a.max_rows)
    df = transport_class(df, pmap)
    a0_schema(df, cm, allcols, R)
    a0c_sla(df, R)
    a0d_knob(df, allcols, R)
    rs = resample(df, a.grid_ms)
    R.p(f"Resampled to a {a.grid_ms} ms grid: {rs.height:,} rows.")
    a0b_correlation(rs, df.height, R)
    a1_event_study(rs, a.grid_ms, R)
    a2_backhaul_delay(rs, R)
    a3_forecaster(rs, a.grid_ms, R)
    a4_stack_maps(df, R)
    R.p(f"Done in {(time.time() - t0) / 60:.1f} min.")
    R.save()
    print(f"\nreport: {os.path.join(a.out, 'AUDIT_REPORT.md')}")


if __name__ == "__main__":
    main()
