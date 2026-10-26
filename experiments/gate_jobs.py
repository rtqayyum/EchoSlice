"""Job lists for the go/no-go gate.

E1  effect size: open-loop slicers vs the best static share (oracle) and
    EchoSlice-lite, over 2-slice and 3-slice cells, three loads, ABR rules,
    work-conserving (min-ratio) and strict (dedicated) isolation.
E2  resonance: slicer period x segment length.
E3  load step: tracking after extra bulk flows arrive.
"""
import json
import sys

DYN = [
    {"type": "usage"},
    {"type": "forecast", "h": 0.2},
    {"type": "olqoe", "h": 0.1},
    {"type": "echo"},
]


def grid2(step=0.1):
    return [[round(v, 2), round(1 - v, 2)] for v in [i * step for i in range(1, int(round(1 / step)))]]


def grid3():
    pts = []
    for v in (0.2, 0.3, 0.4, 0.5, 0.6):
        for g in (0.05, 0.1, 0.2, 0.3):
            b = round(1 - v - g, 2)
            if b >= 0.1 - 1e-9:
                pts.append([v, g, b])
    return pts


def e1(seeds=(1, 2, 3)):
    jobs = []
    loads2 = [(16, 0, 4), (32, 0, 6), (48, 0, 8)]
    loads3 = [(16, 6, 4), (24, 8, 6), (32, 12, 8)]
    for strict in (False, True):
        for (nv, ng, nb), abrs, grid in [(l, ("tput", "dyn", "bola"), grid2()) for l in loads2] + \
                                        [(l, ("tput", "dyn"), grid3()) for l in loads3]:
            for abr in abrs:
                sc = dict(n_video=nv, n_game=ng, n_bulk=nb, abr=abr, strict=strict)
                sls = list(DYN) + [{"type": "static", "x": x} for x in grid]
                sls.append({"type": "static"})              # equal split
                if not strict:
                    sls.append({"type": "shared"})
                for sl in sls:
                    for s in seeds:
                        jobs.append({"exp": "E1", "scenario": sc, "slicer": sl, "seed": s})
    return jobs


def e2(seeds=(1, 2, 3)):
    jobs = []
    for abr in ("tput", "dyn"):
        for L in (2.0, 4.0, 6.0):
            for Ts in (0.1, 0.5, 1.0, 2.0, 5.0):
                sc = dict(n_video=24, n_game=8, n_bulk=6, abr=abr, seg_dur=L, Ts=Ts)
                for sl in ({"type": "usage"}, {"type": "forecast", "h": 0.2},
                           {"type": "olqoe", "h": 0.1, "every": max(Ts, 0.5)}):
                    for s in seeds:
                        jobs.append({"exp": "E2", "scenario": sc, "slicer": sl, "seed": s})
            sc = dict(n_video=24, n_game=8, n_bulk=6, abr=abr, seg_dur=L, Ts=1.0)
            for s in seeds:
                jobs.append({"exp": "E2", "scenario": sc, "slicer": {"type": "static", "x": [0.4, 0.2, 0.4]}, "seed": s})
    return jobs


def e4(seeds=(1, 2, 3)):
    """QoE-model sensitivity: same cells scored with P.1203 'mobile' (separate runs);
    bulk-MOS saturation is re-scored offline from stored per-flow throughput."""
    jobs = []
    cells = [(dict(n_video=32, n_game=0, n_bulk=6, abr="tput"), grid2()),
             (dict(n_video=24, n_game=8, n_bulk=6, abr="dyn"), grid3())]
    for device in ("pc", "mobile"):
        for sc, grid in cells:
            sc = dict(sc, device=device)
            sls = list(DYN) + [{"type": "static", "x": x} for x in grid] + [{"type": "static"}, {"type": "shared"}]
            for sl in sls:
                for s in seeds:
                    jobs.append({"exp": "E4", "scenario": sc, "slicer": sl, "seed": s})
    return jobs


def e5(seeds=(1, 2, 3)):
    """Headroom sweep for forecast-then-allocate: tests the predicted knife-edge
    (spiral down below h* = 1/0.9 - 1, path-dependent hold, climb above the ladder step)."""
    jobs = []
    for sc in (dict(n_video=32, n_game=0, n_bulk=6, abr="tput"), dict(n_video=32, n_game=0, n_bulk=6, abr="tput", strict=True),
               dict(n_video=24, n_game=8, n_bulk=6, abr="dyn")):
        for h in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0):
            for s in seeds:
                jobs.append({"exp": "E5", "scenario": sc, "slicer": {"type": "forecast", "h": h}, "seed": s})
    return jobs


if __name__ == "__main__":
    which = sys.argv[1]
    jobs = {"E1": e1, "E2": e2, "E4": e4, "E5": e5}[which]()
    json.dump(jobs, open(sys.argv[2], "w"))
    print(len(jobs), "jobs")
