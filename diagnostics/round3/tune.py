"""Local tuning harness for EchoSlice v3 on held-out seeds (101-104; never used in the campaign).

python diagnostics/round3/tune.py <variant-json> [--cells fast|all] [--seeds 101,102,103,104]
  variant-json: a slicer spec as used in job lists, e.g. '{"type":"echo3","lam":0}'
Baselines (best static split from the 30-seed campaign, v2, forecast+20%) are cached in
diagnostics/round3/cache.jsonl, so only the new variant is simulated.
"""
import argparse, json, os, sys, time
import numpy as np
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))
from sim.engine import Scenario, simulate          # noqa: E402
from sim.slicers import SLA_TARGET                  # noqa: E402
from experiments.runner import make_slicer          # noqa: E402
from campaign_jobs import E7_DAY, E7_FLASH          # noqa: E402

E6 = dict(n_video=32, n_game=12, n_bulk=8, abr="dyn", T=1200.0, t_eval0=200.0)
CELLS = {
    "M1F": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn"), [0.7, 0.2, 0.1]),
    "M1T": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True), [0.8, 0.1, 0.1]),
    "M2F": (dict(n_video=12, n_game=20, n_bulk=2, abr="dyn"), [0.2, 0.7, 0.1]),
    "M2T": (dict(n_video=12, n_game=20, n_bulk=2, abr="dyn", strict=True), [0.2, 0.7, 0.1]),
    "M3F": (dict(n_video=8, n_game=4, n_bulk=16, abr="dyn"), [0.1, 0.2, 0.7]),
    "M3T": (dict(n_video=8, n_game=4, n_bulk=16, abr="dyn", strict=True), [0.1, 0.1, 0.8]),
    "dayF": (dict(E7_DAY), [0.2, 0.7, 0.1]),
    "dayT": (dict(E7_DAY, strict=True), [0.4, 0.3, 0.3]),
    "flashF": (dict(E7_FLASH), [0.2, 0.7, 0.1]),
    "flashT": (dict(E7_FLASH, strict=True), [0.4, 0.4, 0.2]),
    "bwF": (dict(E6, pattern="bulk_wave"), [0.4, 0.4, 0.2]),
    "churnF": (dict(E6, pattern="churn"), [0.4, 0.3, 0.3]),
    "vpT": (dict(E6, pattern="video_peak", strict=True), [0.4, 0.3, 0.3]),
    "gsT": (dict(E6, pattern="game_surge", strict=True), [0.4, 0.3, 0.3]),
    "B3T": (dict(n_video=24, n_game=8, n_bulk=6, abr="dyn", strict=True), [0.4, 0.3, 0.3]),
    "B3F": (dict(n_video=24, n_game=8, n_bulk=6, abr="dyn"), [0.4, 0.3, 0.3]),
    "B2F": (dict(n_video=32, n_game=0, n_bulk=6, abr="tput"), [0.65, 0.35]),
}
FAST = ["M1F", "M1T", "M2F", "M3T", "dayT", "flashT", "bwF", "B3T", "B2F"]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.jsonl")


def sla_of(r, names):
    cm = np.array([[np.nan if v is None else v for v in row] for row in r["chunk_flow_mos"]], dtype=float)
    fs = np.array(r["flow_slice"])
    out = {}
    for k, nm in enumerate(names):
        v = cm[fs == k].ravel()
        v = v[np.isfinite(v)]
        if len(v):
            out[nm] = float((v >= SLA_TARGET[nm]).mean())
    return out


def run(args):
    cell, spec, seed = args
    kw, ox = CELLS[cell]
    sp = dict(spec)
    if sp.get("type") == "static" and sp.get("x") == "oracle":
        sp["x"] = ox
    t0 = time.time()
    r = simulate(Scenario(**kw), make_slicer(sp), seed)
    cmu = [v for v in r["chunk_mos_user"] if v is not None]
    return dict(cell=cell, spec=json.dumps(spec, sort_keys=True), seed=seed, mos=float(np.mean(cmu)),
                slice=r["mos_slice"], sla=sla_of(r, r["names"]), wall=time.time() - t0)


def load_cache():
    c = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            d = json.loads(line)
            c[(d["cell"], d["spec"], d["seed"])] = d
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variants", nargs="+")
    ap.add_argument("--cells", default="fast")
    ap.add_argument("--seeds", default="101,102,103,104")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    a = ap.parse_args()
    cells = FAST if a.cells == "fast" else (list(CELLS) if a.cells == "all" else a.cells.split(","))
    seeds = [int(s) for s in a.seeds.split(",")]
    base = [{"type": "static", "x": "oracle"}, {"type": "echo2", "alpha": 1.0, "mos_ok": 4.4, "boost_cycles": 4},
            {"type": "forecast", "h": 0.2}]
    specs = base + [json.loads(v) for v in a.variants]
    cache = load_cache()
    todo = [(c, s, sd) for c in cells for s in specs for sd in seeds
            if (c, json.dumps(s, sort_keys=True), sd) not in cache]
    print(f"{len(todo)} runs to do", flush=True)
    with Pool(a.workers) as p, open(CACHE, "a") as f:
        for r in p.imap_unordered(run, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
            cache[(r["cell"], r["spec"], r["seed"])] = r
    names = ["oracle", "v2", "fc20"] + [f"V{i}" for i in range(len(a.variants))]
    print("gap (%) to the best static split, mean over seeds; [worst-slice SLA]")
    print(f"{'cell':8s} " + " ".join(f"{n:>14s}" for n in names[1:]))
    tot = {n: [] for n in names[1:]}
    for c in cells:
        row = []
        for n, s in zip(names[1:], specs[1:]):
            g, w = [], []
            for sd in seeds:
                o = cache[(c, json.dumps(specs[0], sort_keys=True), sd)]["mos"]
                d = cache[(c, json.dumps(s, sort_keys=True), sd)]
                g.append(100 * (o - d["mos"]) / o)
                w.append(min(d["sla"].values()))
            tot[n].append(np.mean(g))
            row.append(f"{np.mean(g):7.2f} [{np.mean(w):.2f}]")
        print(f"{c:8s} " + " ".join(f"{x:>14s}" for x in row))
    print(f"{'mean':8s} " + " ".join(f"{np.mean(tot[n]):14.2f}" for n in names[1:]))
    print(f"{'worst':8s} " + " ".join(f"{np.max(tot[n]):14.2f}" for n in names[1:]))
    for i, v in enumerate(a.variants):
        print(f"V{i} = {v}")


if __name__ == "__main__":
    main()
