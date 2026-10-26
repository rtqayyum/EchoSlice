"""HPC campaign driver.

  prepare  write results/<EXP>/jobs.json and a per-task assignment of the jobs not yet done
  run      one Slurm task: run its assigned jobs, append to results/<EXP>/parts/<tag>_t<task>.jsonl
  status   progress of every experiment (done / errors / missing)
  report   merge parts, analyse, draw figures, write summary JSON + Markdown report
  warmup   compile the numba kernel once (fills NUMBA_CACHE_DIR before the parallel step)
  bench    time a few jobs per experiment and estimate the CPU hours of the campaign

Resuming is automatic: a job counts as done when any part file holds a successful
result for it. Error lines are kept for diagnosis and the job is retried next time.
"""
import argparse
import glob
import hashlib
import json
import os
import resource
import socket
import sys
import time
import traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from experiments import campaign_jobs as CJ  # noqa: E402


def key(job):
    return json.dumps(job, sort_keys=True)


def exp_dir(root, exp):
    return os.path.join(root, "results", exp)


def scan_parts(root, exp):
    """Return {job_key: 'ok' | 'error'} over all part files (ok wins)."""
    st = {}
    for f in glob.glob(os.path.join(exp_dir(root, exp), "parts", "*.jsonl")):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue          # a line cut by a killed task
                k = key(r["job"])
                if "error" in r:
                    st.setdefault(k, "error")
                else:
                    st[k] = "ok"
    return st


def cmd_prepare(a):
    for exp in a.exps.split(","):
        d = exp_dir(a.root, exp)
        os.makedirs(os.path.join(d, "parts"), exist_ok=True)
        jobs = CJ.build(exp, a.seeds)
        if a.smoke and exp == "E7":
            # one unbalanced cell and the flash crowd (with its pre-change runs), strict, every 4th grid point
            keep = {("stationary", "M2-gaming-heavy"), ("stationary", "M1-video-heavy"), ("dynamic", "flash_crowd"),
                    ("phaseA", "flash_crowd")}
            gx = [g for i, g in enumerate(CJ.grid3w()) if i % 4 == 0]
            jobs = [j for j in jobs if (j["role"], j["cell"]) in keep
                    and (j["scenario"].get("strict", False) or j["cell"] == "M1-video-heavy")
                    and (j["slicer"].get("x") is None or j["slicer"]["x"] in gx)]
        elif a.smoke and exp not in ("E9", "E10", "E11", "E12", "E13", "E14"):
            # one complete cell per experiment (all slicers and grid points), so every analysis runs
            s0 = jobs[0]["scenario"]
            pat, strict = s0.get("pattern", ""), s0.get("strict", False)
            jobs = [j for j in jobs if j["scenario"] == s0 or
                    (j.get("role") == "phaseA" and j.get("pattern_of") == pat and j["scenario"].get("strict", False) == strict)]
        if a.smoke and exp in ("E9", "E10", "E11", "E12", "E13", "E14"):
            # first cell of each role, every slicer, so each analysis runs end to end
            seen = {}
            for j in jobs:
                k = (j.get("role", ""), j.get("impairment", ""))
                seen.setdefault(k, json.dumps(j["scenario"], sort_keys=True))
            keep_sc = set(seen.values())
            jobs = [j for j in jobs if json.dumps(j["scenario"], sort_keys=True) in keep_sc]
            if exp in ("E12",):
                jobs = [j for j in jobs if j["slicer"].get("x") is None or j["slicer"]["x"] in CJ.grid3w()[::4]]
        if a.max_jobs and len(jobs) > a.max_jobs:
            step = len(jobs) / a.max_jobs
            jobs = [jobs[int(i * step)] for i in range(a.max_jobs)]
        tmp = os.path.join(d, f".jobs_{a.tag}.json")
        with open(tmp, "w") as f:
            json.dump(jobs, f)
        os.replace(tmp, os.path.join(d, "jobs.json"))          # atomic: other jobs may be reading it
        st = scan_parts(a.root, exp)
        todo = [i for i, j in enumerate(jobs) if st.get(key(j)) != "ok"]
        if a.drl == "skip":
            todo = [i for i in todo if not CJ.is_drl(jobs[i])]
        elif a.drl == "only":
            todo = [i for i in todo if CJ.is_drl(jobs[i])]
        # spread costly configurations evenly: order by a hash, then deal round-robin
        todo.sort(key=lambda i: hashlib.md5(key(jobs[i]).encode()).hexdigest())
        assign = {str(t): todo[t::a.ntasks] for t in range(a.ntasks)}
        with open(os.path.join(d, f"assign_{a.tag}.json"), "w") as f:
            json.dump(assign, f)
        n_err = sum(1 for j in jobs if st.get(key(j)) == "error")
        print(f"[prepare] {exp}: {len(jobs)} jobs, {sum(1 for j in jobs if st.get(key(j)) == 'ok')} done, "
              f"{len(todo)} to run now (DRL runs: {a.drl}; {n_err} retried after errors) over {a.ntasks} tasks",
              flush=True)


def cmd_run(a):
    from experiments.runner import run_job
    task = int(os.environ.get("SLURM_PROCID", a.task))
    d = exp_dir(a.root, a.exp)
    jobs = json.load(open(os.path.join(d, "jobs.json")))
    assign = json.load(open(os.path.join(d, f"assign_{a.tag}.json")))
    mine = assign.get(str(task), [])
    out = os.path.join(d, "parts", f"{a.tag}_t{task:03d}.jsonl")
    host = socket.gethostname()
    print(f"[{a.exp} t{task:03d}] host {host}, {len(mine)} jobs -> {out}", flush=True)
    t0 = time.time()
    n_err = 0
    with open(out, "a") as f:
        for n, idx in enumerate(mine, 1):
            r = run_job(jobs[idx])
            r["host"] = host
            if "error" in r:
                n_err += 1
                print(f"[{a.exp} t{task:03d}] ERROR job {idx}: {r['error'].strip().splitlines()[-1]}", flush=True)
            f.write(json.dumps(r, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
            f.flush()
            if n % 10 == 0 or n == len(mine):
                el = time.time() - t0
                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                print(f"[{a.exp} t{task:03d}] {n}/{len(mine)} done, {n_err} errors, {el / n:.1f} s/run, "
                      f"eta {el / n * (len(mine) - n) / 60:.1f} min, maxrss {rss:.0f} MB", flush=True)
    print(f"[{a.exp} t{task:03d}] finished in {(time.time() - t0) / 60:.1f} min, {n_err} errors", flush=True)
    sys.exit(3 if n_err else 0)


def exp_status(root, exp):
    d = exp_dir(root, exp)
    jf = os.path.join(d, "jobs.json")
    if not os.path.exists(jf):
        return None
    jobs = json.load(open(jf))
    st = scan_parts(root, exp)
    ok = sum(1 for j in jobs if st.get(key(j)) == "ok")
    er = sum(1 for j in jobs if st.get(key(j)) == "error")
    parts = glob.glob(os.path.join(d, "parts", "*.jsonl"))
    return dict(jobs=len(jobs), done_ok=ok, errors=er, missing=len(jobs) - ok - er, part_files=len(parts))


def cmd_status(a):
    exps = a.exps.split(",") if a.exps else list(CJ.EXPERIMENTS)
    print(f"{'exp':4s} {'title':24s} {'jobs':>7s} {'done':>7s} {'errors':>7s} {'missing':>8s} {'%':>6s} parts")
    for e in exps:
        s = exp_status(a.root, e)
        if s is None:
            print(f"{e:4s} {CJ.TITLES[e]:24s}   (not prepared)")
            continue
        pct = 100 * s["done_ok"] / max(s["jobs"], 1)
        print(f"{e:4s} {CJ.TITLES[e]:24s} {s['jobs']:7d} {s['done_ok']:7d} {s['errors']:7d} {s['missing']:8d} {pct:6.1f} {s['part_files']}")


def cmd_warmup(a):
    from sim.engine import Scenario, simulate
    from sim import slicers as SL
    t0 = time.time()
    simulate(Scenario(n_video=2, n_game=1, n_bulk=1, T=20.0, t_eval0=10.0, abr="dyn", min_eval_s=5.0), SL.Static(), 1)
    print(f"[warmup] numba kernel ready in {time.time() - t0:.1f} s (cache: {os.environ.get('NUMBA_CACHE_DIR', 'default')})")


def cmd_bench(a):
    from experiments.runner import run_job
    import numpy as np
    tot = 0.0
    rows = []
    for exp in a.exps.split(","):
        jobs = CJ.build(exp, a.seeds)
        rng = np.random.default_rng(0)
        pick = rng.choice(len(jobs), min(a.per_exp, len(jobs)), replace=False)
        ts = []
        for i in pick:
            t0 = time.time()
            r = run_job(jobs[i])
            ts.append(time.time() - t0)
            if "error" in r:
                print(r["error"])
        m = float(np.mean(ts))
        cpu_h = m * len(jobs) / 3600
        tot += cpu_h
        rows.append((exp, len(jobs), m, cpu_h))
        print(f"[bench] {exp}: {len(jobs)} jobs x {m:.1f} s = {cpu_h:.1f} CPU-h (sample of {len(ts)})", flush=True)
    print(f"[bench] total {tot:.1f} CPU-h; wall with 40 tasks about {tot / 40 * 1.15:.1f} h (15% imbalance margin)")


def cmd_report(a):
    from experiments import campaign_report as CR
    code = CR.report(a.root, a.exps.split(","), a.tag)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--root", required=True); p.add_argument("--exps", required=True)
    p.add_argument("--seeds", type=int, default=30); p.add_argument("--max-jobs", type=int, default=0)
    p.add_argument("--ntasks", type=int, required=True); p.add_argument("--tag", required=True)
    p.add_argument("--smoke", action="store_true", help="one cell per experiment, for a quick end-to-end test")
    p.add_argument("--drl", choices=["all", "skip", "only"], default="all",
                   help="skip: leave DRL runs for later (policies not trained yet); only: just the DRL runs")
    p = sub.add_parser("run"); p.add_argument("--root", required=True); p.add_argument("--exp", required=True)
    p.add_argument("--tag", required=True); p.add_argument("--task", type=int, default=0)
    p = sub.add_parser("status"); p.add_argument("--root", required=True); p.add_argument("--exps", default="")
    p = sub.add_parser("report"); p.add_argument("--root", required=True); p.add_argument("--exps", required=True)
    p.add_argument("--tag", default="manual")
    sub.add_parser("warmup")
    p = sub.add_parser("bench"); p.add_argument("--exps", default="E1,E2,E4,E5,E6,E7,E9,E10,E11,E12,E13,E14")
    p.add_argument("--seeds", type=int, default=30); p.add_argument("--per-exp", type=int, default=4)
    a = ap.parse_args()
    {"prepare": cmd_prepare, "run": cmd_run, "status": cmd_status, "report": cmd_report,
     "warmup": cmd_warmup, "bench": cmd_bench}[a.cmd](a)


if __name__ == "__main__":
    main()
