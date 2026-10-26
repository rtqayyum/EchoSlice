"""Diagnostic: EchoSlice as a closed-loop residual on top of a forecast slicer.
x(t) = project(f(t) + D + probe), where f(t) is the forecast+20% split recomputed every period and the
offset D (sums to zero, |D_k| <= 0.4) is learned by the same SPSA probes as EchoSlice-lite.
No tuning: delta, hold, settle, step and max_step as in EchoSlice-lite. Held-out seeds 101-104."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, time
import numpy as np
sys.path.insert(0, _ROOT)
from multiprocessing import Pool
from sim.engine import Scenario, simulate
from sim import slicers as SL
sys.path.insert(0, _os.path.join(_ROOT, "experiments"))
from campaign_jobs import E7_DAY, E7_FLASH

class EchoResidual(SL.EchoSliceLite):
    def __init__(self, dmax=0.4, **kw):
        super().__init__(**kw); self.dmax = dmax; self.name = "echoslice-residual"
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.fc = SL.ForecastHeadroom(0.2); self.fc.reset(sc, names, S, mon, rng)
        self.D = np.zeros(self.K); self.Dhist = []
    def decide(self, t, kpm):
        f = self.fc.decide(t, kpm)
        if t - self.t_phase >= self.hold:
            U = self._utility(t); self.t_phase = t
            if self.phase == 0:
                self.Up = U; self.phase = 1
            else:
                g = (self.Up - U) / (2 * self.delta) * self.dir
                stp = np.clip(self.step * g * self.delta, -self.max_step, self.max_step)
                self.D = np.clip(self.D + stp, -self.dmax, self.dmax); self.D -= self.D.mean()
                self.Dhist.append((float(t), self.D.round(3).tolist()))
                self.dir = self._newdir(); self.phase = 0
        s = 1.0 if self.phase == 0 else -1.0
        self.x = SL.project(f + self.D + s * self.delta * self.dir)
        return self.x

CELLS = {"M1F": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=False), [0.7, 0.2, 0.1]),
         "M1T": (dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True), [0.8, 0.1, 0.1]),
         "M2F": (dict(n_video=12, n_game=20, n_bulk=2, abr="dyn", strict=False), [0.2, 0.7, 0.1]),
         "M3T": (dict(n_video=8, n_game=4, n_bulk=16, abr="dyn", strict=True), [0.1, 0.1, 0.8]),
         "dayT": (dict(E7_DAY, strict=True), [0.4, 0.3, 0.3]),
         "flashT": (dict(E7_FLASH, strict=True), [0.4, 0.4, 0.2])}

def run(args):
    cell, var, seed = args
    kw, ox = CELLS[cell]
    sc = Scenario(**kw)
    sl = {"resid": lambda: EchoResidual(), "v2": lambda: SL.EchoSlice(), "forecast": lambda: SL.ForecastHeadroom(0.2),
          "static@oracle": lambda: SL.Static(ox)}[var]()
    t0 = time.time(); r = simulate(sc, sl, seed)
    cm = r.get("chunk_mos_user")
    return dict(cell=cell, var=var, seed=seed, mos=float(r["mos_user"]),
                mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()},
                chunk_mos=[float(v) for v in cm] if cm is not None else None,
                D_end=getattr(sl, "D", np.zeros(1)).round(3).tolist(), wall=time.time() - t0)

if __name__ == "__main__":
    seeds = [101, 102, 103, 104]
    jobs = [(c, "resid", s) for c in ("M1F", "M1T", "M2F", "M3T") for s in seeds]
    jobs += [(c, v, s) for c in ("dayT", "flashT") for v in ("resid", "v2", "forecast", "static@oracle") for s in seeds]
    with Pool(2) as p, open(sys.argv[1], "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["cell"], r["var"], r["seed"], round(r["mos"], 4), r["D_end"], f"{r['wall']:.0f}s", flush=True)
