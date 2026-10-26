"""Diagnostic: does v2 lose to v1 in E6 bulk_wave/churn because count jumps also move the elastic bulk slice?
Variant v2-nobulk applies count jumps only to the video and gaming slices. Held-out seeds 101-104, shareable."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, time
import numpy as np
sys.path.insert(0, _ROOT)
from multiprocessing import Pool
from sim.engine import Scenario, simulate
from sim import slicers as SL

class EchoNoBulk(SL.EchoSlice):
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng); self.be = names.index("bulk") if "bulk" in names else None
        self.name = "echoslice-nobulk"
    def decide(self, t, kpm):
        if self.be is not None:
            kpm = dict(kpm); fa = kpm["flow_active"].copy()
            # hide bulk session changes from the jump rule: count bulk flows as always active
            fa[kpm["flow_slice"] == self.be] = True
            kpm["flow_active"] = fa
        return super().decide(t, kpm)

def run(args):
    pat, var, seed = args
    sc = Scenario(n_video=32, n_game=12, n_bulk=8, abr="dyn", strict=False, pattern=pat, T=1200.0, t_eval0=200.0)
    sl = {"v1": SL.EchoSliceLite, "v2": SL.EchoSlice, "v2-nobulk": EchoNoBulk}[var]()
    t0 = time.time(); r = simulate(sc, sl, seed)
    return dict(pat=pat, var=var, seed=seed, mos=float(r["mos_user"]), mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()},
                jumps=len(getattr(sl, "jumps", [])), jump_log=[(float(t), [round(v, 2) for v in rt]) for t, rt, _ in getattr(sl, "jumps", [])][:12],
                wall=time.time() - t0)

if __name__ == "__main__":
    jobs = [(p, v, s) for p in ("bulk_wave", "churn") for v in ("v1", "v2", "v2-nobulk") for s in (101, 102, 103, 104)]
    with Pool(2) as p, open(sys.argv[1], "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["pat"], r["var"], r["seed"], round(r["mos"], 4), "jumps", r["jumps"], f"{r['wall']:.0f}s", flush=True)
