"""Diagnostic: EchoSlice with an exogenous prior (sketch of a v3; not tuned).
Prior split = active sessions x a per-session reference rate (a slice-template value fixed a priori:
video 4 Mb/s, gaming 10 Mb/s), divided by the slice's cell capacity; bulk (best effort) gets the rest,
>= 0.05. The centre starts at the prior. When a bounded-rate slice's session count changes by >= max(2, 25%),
the centre moves with the prior and keeps the learned correction: c <- project(prior_new + (c - prior_old)).
Bulk session changes do not move anything. Probing as in EchoSlice-lite, boosted after each move.
Held-out seeds 101-104."""
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

REF = {"video": 4e6, "game": 10e6}

class EchoSlice3(SL.EchoSlice):
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.name = "echoslice-v3sketch"
        self.be = names.index("bulk") if "bulk" in names else None
        self.r = np.array([REF.get(n, 0.0) for n in names])
        self.p0 = None
        self.moves = []
    def _prior(self, kpm, n):
        cap = kpm["eff"] * self.sc.B
        need = n * self.r / np.maximum(cap, 1.0)
        x = need.copy()
        if self.be is not None:
            pri = [k for k in range(self.K) if k != self.be]
            s = x[pri].sum()
            if s > 1 - SL.XMIN:
                x[pri] *= (1 - SL.XMIN) / s
            x[self.be] = 1 - x[pri].sum()
        return SL.project(x)
    def decide(self, t, kpm):
        a = kpm["flow_active"]
        n = np.array([float(((kpm["flow_slice"] == k) & a).sum()) for k in range(self.K)])
        pri = np.array([k != self.be for k in range(self.K)])
        moved = False
        if self.p0 is None:
            self.p0 = self._prior(kpm, n); self.c = self.p0.copy(); self.n_ref = n; moved = True
        elif np.any((np.abs(n - self.n_ref) >= np.maximum(2.0, 0.25 * self.n_ref)) & pri):
            p1 = self._prior(kpm, n)
            self.c = SL.project(p1 + (self.c - self.p0)); self.p0 = p1; self.n_ref = n; moved = True
            self.moves.append((float(t), p1.round(3).tolist()))
        if moved:
            self.boost = self.boost_cycles; self.d_pair = self.delta * self.boost_delta
            self.dir = self._newdir(); self.phase = 0; self.t_phase = t
            self.x = SL.project(self.c + self.d_pair * self.dir)
            return self.x
        if t - self.t_phase < self.hold:
            return self.x
        U = self._utility(t); self.t_phase = t
        if self.phase == 0:
            self.Up = U; self.phase = 1; self.x = SL.project(self.c - self.d_pair * self.dir)
        else:
            g = (self.Up - U) / (2 * self.d_pair) * self.dir
            k = self.boost_step if self.boost else 1.0
            stp = np.clip(self.step * k * g * self.d_pair, -self.max_step * k, self.max_step * k)
            self.c = SL.project(self.c + stp)
            self.boost = max(0, self.boost - 1)
            self.d_pair = self.delta * (self.boost_delta if self.boost else 1.0)
            self.dir = self._newdir(); self.phase = 0
            self.x = SL.project(self.c + self.d_pair * self.dir)
        return self.x

CELLS = {"M1F": dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=False),
         "M1T": dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True),
         "M2F": dict(n_video=12, n_game=20, n_bulk=2, abr="dyn", strict=False),
         "M3T": dict(n_video=8, n_game=4, n_bulk=16, abr="dyn", strict=True),
         "dayT": dict(E7_DAY, strict=True), "flashT": dict(E7_FLASH, strict=True),
         "bulk_wave": dict(n_video=32, n_game=12, n_bulk=8, abr="dyn", strict=False, pattern="bulk_wave", T=1200.0, t_eval0=200.0),
         "churn": dict(n_video=32, n_game=12, n_bulk=8, abr="dyn", strict=False, pattern="churn", T=1200.0, t_eval0=200.0)}

def run(args):
    cell, seed = args
    sl = EchoSlice3()
    t0 = time.time(); r = simulate(Scenario(**CELLS[cell]), sl, seed)
    cm = r.get("chunk_mos_user")
    return dict(cell=cell, var="v3sketch", seed=seed, mos=float(r["mos_user"]),
                mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()},
                chunk_mos=[float(v) for v in cm] if cm is not None else None,
                c_end=sl.c.round(3).tolist(), prior0=sl.p0.round(3).tolist(), moves=len(sl.moves), wall=time.time() - t0)

if __name__ == "__main__":
    jobs = [(c, s) for c in CELLS for s in (101, 102, 103, 104)]
    with Pool(2) as p, open(sys.argv[1], "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["cell"], r["seed"], round(r["mos"], 4), "prior", r["prior0"], "end", r["c_end"], "moves", r["moves"], f"{r['wall']:.0f}s", flush=True)
