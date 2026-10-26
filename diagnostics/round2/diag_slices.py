"""Per-slice MOS for v2 (equal start), v2 warm-started from forecast, and forecast in M1 shareable, seeds 101-104."""
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json
sys.path.insert(0, _ROOT); sys.path.insert(0, _HERE)
from multiprocessing import Pool
from sim.engine import Scenario, simulate
from sim import slicers as SL
from diag_prior import EchoPrior

def run(a):
    var, seed = a
    sl = {"v2": SL.EchoSlice, "v2+prior": EchoPrior, "forecast": lambda: SL.ForecastHeadroom(0.2), "static@oracle": lambda: SL.Static([0.7, 0.2, 0.1])}[var]()
    r = simulate(Scenario(n_video=56, n_game=4, n_bulk=2, abr="dyn"), sl, seed)
    return dict(var=var, seed=seed, mos=float(r["mos_user"]), mos_slice={k: float(v) for k, v in dict(r["mos_slice"]).items()})

if __name__ == "__main__":
    jobs = [(v, s) for v in ("v2", "forecast", "static@oracle") for s in (101, 102, 103, 104)]
    with Pool(2) as p, open(sys.argv[1], "w") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush(); print(r, flush=True)
