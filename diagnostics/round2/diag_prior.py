"""Diagnostic: warm-starting EchoSlice from the forecast+20% split (a demand prior) instead of the equal split.
For the first t_prior seconds the slicer acts exactly like forecast+20%; then the SPSA centre starts from
the mean forecast split of the last 10 s. Held-out seeds 101-104."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, time
import numpy as np
sys.path.insert(0, _ROOT)
from multiprocessing import Pool
from sim.engine import Scenario, simulate
from sim import slicers as SL

class EchoPrior(SL.EchoSlice):
    def __init__(self, t_prior=40.0, **kw):
        super().__init__(**kw); self.t_prior = t_prior; self.name = "echoslice+prior"
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.fc = SL.ForecastHeadroom(0.2); self.fc.reset(sc, names, S, mon, rng); self.fx = []; self.started = False
    def decide(self, t, kpm):
        if t < self.t_prior:
            x = self.fc.decide(t, kpm)
            if t >= self.t_prior - 10: self.fx.append(x.copy())
            self.x = x; return x
        if not self.started:
            self.started = True
            self.c = SL.project(np.mean(self.fx, 0)); self.t_phase = t; self.phase = 0
            self.dir = self._newdir(); self.x = SL.project(self.c + self.delta * self.dir); self.c_start = self.c.copy()
            self.n_ref = None
            return self.x
        return super().decide(t, kpm)

CELLS = {"M1F": dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=False),
         "M1T": dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True),
         "M3T": dict(n_video=8, n_game=4, n_bulk=16, abr="dyn", strict=True),
         "M2F": dict(n_video=12, n_game=20, n_bulk=2, abr="dyn", strict=False)}

def run(args):
    cell, var, seed = args
    sc = Scenario(**CELLS[cell])
    OX = {"M1F": [0.7, 0.2, 0.1], "M1T": [0.8, 0.1, 0.1], "M3T": [0.1, 0.1, 0.8], "M2F": [0.2, 0.7, 0.1]}
    sl = {"v2": lambda: SL.EchoSlice(), "v2+prior": lambda: EchoPrior(), "forecast": lambda: SL.ForecastHeadroom(0.2),
          "static@oracle": lambda: SL.Static(OX[cell])}[var]()
    t0 = time.time(); r = simulate(sc, sl, seed)
    extra = {}
    if var == "v2+prior": extra["c_start"] = [float(v) for v in sl.c_start]; extra["c_end"] = [float(v) for v in sl.c]
    if var == "v2": extra["c_end"] = [float(v) for v in sl.c]
    return dict(cell=cell, var=var, seed=seed, mos=float(r["mos_user"]), mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()},
                wall=time.time() - t0, **extra)

if __name__ == "__main__":
    seeds = [101, 102, 103, 104]
    jobs = [(c, v, s) for c in CELLS for v in ("v2+prior",) for s in seeds]
    jobs += [(c, v, s) for c in ("M3T", "M2F") for v in ("v2", "forecast", "static@oracle") for s in seeds]
    with Pool(2) as p, open(sys.argv[1], "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["cell"], r["var"], r["seed"], round(r["mos"], 4), r.get("c_start"), f"{r['wall']:.0f}s", flush=True)
