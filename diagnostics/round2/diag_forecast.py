"""Diagnostic: how Forecast+20% splits M1 (56 video, 4 gaming, 2 bulk), and what the gaming flows send.
Records the share vector and per-slice offered load every second after warm-up."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json
import numpy as np
sys.path.insert(0, _ROOT)
from sim.engine import Scenario, simulate
from sim import slicers as SL

class Rec(SL.ForecastHeadroom):
    def reset(self, *a):
        super().reset(*a); self.log = []
    def decide(self, t, kpm):
        x = super().decide(t, kpm)
        if t >= 300 and int(t) % 5 == 0:
            cap = kpm["eff"] * self.sc.B
            self.log.append(dict(t=float(t), x=[float(v) for v in x], need=[float(v) for v in (self.f * (1 + self.h) / cap)],
                                 offered_mbps=[float(v) / 1e6 for v in kpm["offered"]]))
        return x

out = {}
for strict in (False, True):
    for seed in (101, 102):
        sl = Rec(0.2)
        r = simulate(Scenario(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=strict), sl, seed)
        L = sl.log
        out[f"{strict}-{seed}"] = dict(mos=r["mos_user"], mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()},
            x_mean=np.mean([l["x"] for l in L], 0).round(3).tolist(),
            need_mean=np.mean([l["need"] for l in L], 0).round(3).tolist(),
            offered_mbps=np.mean([l["offered_mbps"] for l in L], 0).round(2).tolist())
        print(strict, seed, out[f"{strict}-{seed}"], flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
