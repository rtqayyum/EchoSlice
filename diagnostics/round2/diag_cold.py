"""Diagnostic: is EchoSlice's E7 stationary gap a cold-start (convergence) problem?
Runs v2 from the equal split and from the oracle split, plus the oracle static and forecast+20%,
on held-out seeds, and records the centre trajectory."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, time
import numpy as np
sys.path.insert(0, _ROOT)
from multiprocessing import Pool
from sim.engine import Scenario, simulate
from sim import slicers as SL

class EchoFrom(SL.EchoSlice):
    def __init__(self, c0, **kw):
        super().__init__(**kw); self.c0 = np.asarray(c0, float); self.name = "echoslice@" + ",".join(f"{v:.2f}" for v in c0)
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.c = SL.project(self.c0.copy()); self.x = SL.project(self.c + self.delta * self.dir)

CELLS = {"M1F": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=False), [0.70, 0.20, 0.10]),
         "M1T": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True), [0.80, 0.10, 0.10])}

def run(args):
    cell, var, seed = args
    sc_kw, ox = CELLS[cell]
    sc = Scenario(**sc_kw)
    if var == "v2": sl = SL.EchoSlice()
    elif var == "v2@oracle": sl = EchoFrom(ox)
    elif var == "static@oracle": sl = SL.Static(ox)
    elif var == "forecast": sl = SL.ForecastHeadroom(0.2)
    elif var == "v2-long":   # same, but scored after 1500 s of learning
        sc = Scenario(**dict(sc_kw, T=1800.0, t_eval0=1500.0)); sl = SL.EchoSlice()
    t0 = time.time()
    r = simulate(sc, sl, seed)
    traj = [(float(t), [float(v) for v in c]) for (t, c, *_ ) in getattr(sl, "hist", [])]
    return dict(cell=cell, var=var, seed=seed, mos=float(r["mos_user"]), wall=time.time() - t0, traj=traj[::5] + traj[-1:])

if __name__ == "__main__":
    out = sys.argv[1]
    seeds = [101, 102, 103, 104]
    jobs = [(c, v, s) for c in CELLS for v in ("v2", "v2@oracle", "static@oracle", "forecast", "v2-long") for s in seeds]
    with Pool(2) as p, open(out, "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["cell"], r["var"], r["seed"], round(r["mos"], 4), f"{r['wall']:.0f}s", flush=True)
