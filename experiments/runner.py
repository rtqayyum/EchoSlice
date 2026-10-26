"""Parallel, resumable experiment runner. One JSON line per run.

Usage (HPC job arrays): python -m experiments.runner jobs.json out.jsonl --workers 32 [--shard i/n]
"""
import argparse
import json
import os
import sys
import time
import traceback
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Scenario, simulate          # noqa: E402
from sim import slicers as SL                       # noqa: E402


def make_slicer(spec):
    t = spec["type"]
    if t == "static":
        return SL.Static(spec.get("x"))
    if t == "shared":
        return SL.Shared()
    if t == "usage":
        return SL.UsageProp(spec.get("alpha", 0.5))
    if t == "forecast":
        return SL.ForecastHeadroom(spec.get("h", 0.2), spec.get("alpha", 0.3))
    if t == "olqoe":
        return SL.OpenLoopQoE(spec.get("h", 0.1), spec.get("every", 1.0), spec.get("W", 10.0), spec.get("lam", 0.0))
    if t == "echo2":
        kw = {k: v for k, v in spec.items() if k != "type"}
        return SL.EchoSlice(**kw)
    if t == "echo":
        kw = {k: v for k, v in spec.items() if k != "type"}
        return SL.EchoSliceLite(**kw)
    if t == "echo3":
        kw = {k: v for k, v in spec.items() if k not in ("type", "tag")}
        return SL.EchoSlice3(name=spec.get("tag"), **kw)
    if t == "qoefb":
        kw = {k: v for k, v in spec.items() if k not in ("type", "tag")}
        return SL.QoEFeedback(name=spec.get("tag", "qoe-feedback"), **kw)
    if t == "steps":
        kw = {k: v for k, v in spec.items() if k != "type"}
        return SL.RandomSteps(**kw)
    if t == "drl":
        from experiments import drl
        return drl.PolicySlicer(spec["policy"], lam=spec.get("lam", 0.0), name=spec.get("tag"))
    raise ValueError(t)


def job_key(job):
    return json.dumps(job, sort_keys=True)


def run_job(job):
    try:
        sc = Scenario(**job["scenario"])
        sl = make_slicer(job["slicer"])
        t0 = time.time()
        r = simulate(sc, sl, job["seed"], slice_trace_every=float(job.get("trace", 0.0)))
        out = dict(r)
        out["flow_mos"] = [None if not np.isfinite(v) else float(v) for v in r["flow_mos"]]
        out["job"] = job
        out["slicer_name"] = sl.name
        out["wall_s"] = time.time() - t0
        return out
    except Exception:
        return {"job": job, "error": traceback.format_exc()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--shard", default=None, help="i/n: run every n-th job starting at i")
    a = ap.parse_args()
    jobs = json.load(open(a.jobs))
    if a.shard:
        i, n = map(int, a.shard.split("/"))
        jobs = jobs[i::n]
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            try:
                done.add(job_key(json.loads(line)["job"]))
            except Exception:
                pass
    todo = [j for j in jobs if job_key(j) not in done]
    print(f"{len(jobs)} jobs, {len(todo)} to run", flush=True)
    t0 = time.time()
    with Pool(a.workers) as pool, open(a.out, "a") as f:
        for n, r in enumerate(pool.imap_unordered(run_job, todo, chunksize=1), 1):
            f.write(json.dumps(r, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
            f.flush()
            if n % 20 == 0 or n == len(todo):
                el = time.time() - t0
                print(f"{n}/{len(todo)}  {el/60:.1f} min  eta {el/n*(len(todo)-n)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
