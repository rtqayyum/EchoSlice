"""Job lists for the full HPC campaign (paper-grade, 30 seeds by default).

E1  effect size        2-slice and 3-slice cells, 3 loads, 3 ABR rules, shareable and strict
E2  slicer period      T_s 0.1-5 s x segment length 2/4/6 s x 2 ABR rules
E4  QoE sensitivity    P.1203 pc vs mobile (bulk-MOS saturation re-scored offline)
E5  headroom           forecast headroom 0-100% in three cells
E6  dynamic load       gaming surge, bulk wave, video peak, churn (1200 s runs),
                       plus stationary phase-A runs to pick a deploy-time static split
"""
import json
import os
import sys

ECHO2 = {"type": "echo2", "alpha": 1.0, "mos_ok": 4.4, "boost_cycles": 4}   # EchoSlice v2, parameters fixed on held-out seeds 101-104

DYN = [
    {"type": "usage"},
    {"type": "forecast", "h": 0.2},
    {"type": "olqoe", "h": 0.1},
    {"type": "echo"},
    ECHO2,
]


def grid2(step=0.05):
    n = int(round(1 / step))
    return [[round(i * step, 3), round(1 - i * step, 3)] for i in range(2, n - 1)]   # 0.10 .. 0.90


def grid3():
    pts = []
    for v in (0.2, 0.3, 0.4, 0.5, 0.6):
        for g in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
            b = round(1 - v - g, 3)
            if b >= 0.1 - 1e-9:
                pts.append([v, g, b])
    return pts


def _slicers(n_game, strict, grid):
    sls = list(DYN) + [{"type": "static"}] + [{"type": "static", "x": x} for x in grid]
    if not strict:
        sls.append({"type": "shared"})
    return sls


def e1(seeds):
    jobs = []
    cells = [((16, 0, 4), grid2()), ((32, 0, 6), grid2()), ((48, 0, 8), grid2()),
             ((16, 6, 4), grid3()), ((24, 8, 6), grid3()), ((32, 12, 8), grid3())]
    for strict in (False, True):
        for (nv, ng, nb), grid in cells:
            for abr in ("tput", "dyn", "bola"):
                sc = dict(n_video=nv, n_game=ng, n_bulk=nb, abr=abr, strict=strict)
                for sl in _slicers(ng, strict, grid):
                    for s in seeds:
                        jobs.append({"exp": "E1", "scenario": sc, "slicer": sl, "seed": s})
    return jobs


def e2(seeds):
    jobs = []
    for abr in ("tput", "dyn"):
        for L in (2.0, 4.0, 6.0):
            for Ts in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
                sc = dict(n_video=24, n_game=8, n_bulk=6, abr=abr, seg_dur=L, Ts=Ts)
                for sl in ({"type": "usage"}, {"type": "forecast", "h": 0.2},
                           {"type": "olqoe", "h": 0.1, "every": max(Ts, 0.5)}, {"type": "echo"}, ECHO2):
                    for s in seeds:
                        jobs.append({"exp": "E2", "scenario": sc, "slicer": sl, "seed": s})
            sc = dict(n_video=24, n_game=8, n_bulk=6, abr=abr, seg_dur=L, Ts=1.0)
            for sl in ({"type": "static"}, {"type": "static", "x": [0.4, 0.3, 0.3]}):
                for s in seeds:
                    jobs.append({"exp": "E2", "scenario": sc, "slicer": sl, "seed": s})
    return jobs


def e4(seeds):
    jobs = []
    cells = [(dict(n_video=32, n_game=0, n_bulk=6, abr="tput"), grid2()),
             (dict(n_video=24, n_game=8, n_bulk=6, abr="dyn"), grid3())]
    for device in ("pc", "mobile"):
        for sc, grid in cells:
            sc = dict(sc, device=device)
            for sl in _slicers(sc["n_game"], False, grid):
                for s in seeds:
                    jobs.append({"exp": "E4", "scenario": sc, "slicer": sl, "seed": s})
    return jobs


def e5(seeds):
    jobs = []
    for sc in (dict(n_video=32, n_game=0, n_bulk=6, abr="tput"),
               dict(n_video=32, n_game=0, n_bulk=6, abr="tput", strict=True),
               dict(n_video=24, n_game=8, n_bulk=6, abr="dyn")):
        for h in (0.0, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0):
            for s in seeds:
                jobs.append({"exp": "E5", "scenario": sc, "slicer": {"type": "forecast", "h": h}, "seed": s})
    return jobs


E6_MAX = dict(n_video=32, n_game=12, n_bulk=8)
E6_PATTERNS = ("game_surge", "bulk_wave", "video_peak", "churn")


def phase_a_counts(pattern, base_frac=0.34):
    """Flow counts that are on before the pattern starts (what an operator
    would have tuned a static split for)."""
    c = dict(E6_MAX)
    key = {"game_surge": "n_game", "bulk_wave": "n_bulk", "video_peak": "n_video"}
    keys = list(key.values()) if pattern == "churn" else [key[pattern]]
    for k in keys:
        c[k] = max(1, int(round(base_frac * E6_MAX[k])))
    return c


def e6(seeds):
    jobs = []
    for pattern in E6_PATTERNS:
        for strict in (False, True):
            sc = dict(E6_MAX, abr="dyn", strict=strict, pattern=pattern, T=1200.0, t_eval0=200.0)
            for sl in _slicers(12, strict, grid3()):
                for s in seeds:
                    jobs.append({"exp": "E6", "role": "dynamic", "scenario": sc, "slicer": sl, "seed": s})
            # stationary phase A: the load before the pattern starts
            sa = dict(phase_a_counts(pattern), abr="dyn", strict=strict)
            for x in grid3():
                for s in seeds:
                    jobs.append({"exp": "E6", "role": "phaseA", "pattern_of": pattern, "scenario": sa,
                                 "slicer": {"type": "static", "x": x}, "seed": s})
    return jobs


def grid3w():
    """Wider share grid for unbalanced mixes (video, game, bulk), each slice >= 0.05."""
    vals = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
    pts = []
    for v in vals:
        for g in vals:
            b = round(1 - v - g, 3)
            if v >= 0.1 and b >= 0.05 - 1e-9:
                pts.append([v, g, b])
    return pts


E7_MIXES = {"M1-video-heavy": (56, 4, 2), "M2-gaming-heavy": (12, 20, 2), "M3-bulk-heavy": (8, 4, 16)}
E7_DAY = dict(n_video=56, n_game=20, n_bulk=16, abr="dyn", pattern="day_cycle", T=2000.0, t_eval0=200.0)
E7_FLASH = dict(n_video=24, n_game=24, n_bulk=6, abr="dyn", pattern="flash_crowd", T=1200.0, t_eval0=200.0, jitter_s=10.0)
E7_FLASH_A = dict(n_video=24, n_game=2, n_bulk=6, abr="dyn")


def e7(seeds):
    """Cells where no fixed split can be right: unbalanced mixes, a compressed day whose
    dominant slice changes (video -> gaming -> bulk), and a 10x gaming flash crowd."""
    jobs = []
    grid = grid3w()
    for strict in (False, True):
        for mix, (nv, ng, nb) in E7_MIXES.items():
            sc = dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn", strict=strict)
            for sl in _slicers(ng, strict, grid):
                for s in seeds:
                    jobs.append({"exp": "E7", "role": "stationary", "cell": mix, "scenario": sc, "slicer": sl, "seed": s})
        for cell, base in (("day_cycle", E7_DAY), ("flash_crowd", E7_FLASH)):
            sc = dict(base, strict=strict)
            for sl in _slicers(1, strict, grid):
                for s in seeds:
                    jobs.append({"exp": "E7", "role": "dynamic", "cell": cell, "scenario": sc, "slicer": sl, "seed": s})
        # load before the flash crowd, to pick the static split an operator would deploy
        sa = dict(E7_FLASH_A, strict=strict)
        for x in grid:
            for s in seeds:
                jobs.append({"exp": "E7", "role": "phaseA", "cell": "flash_crowd", "scenario": sa,
                             "slicer": {"type": "static", "x": x}, "seed": s})
    return jobs


# ============================================================================ round 3 (final campaign)
# EchoSlice v3: defaults live in sim/slicers.py (EchoSlice3), fixed on held-out seeds 101-104.
ECHO3 = {"type": "echo3"}


def echo3(lam=0.0, tag=None, **kw):
    sp = dict(ECHO3)
    if lam:
        sp["lam"] = lam
    sp.update(kw)
    if tag:
        sp["tag"] = tag
    return sp


def drl(regime, lam=0.0):
    tag = f"drl-{regime}" + (f"-l{lam:g}" if lam else "")
    sp = {"type": "drl", "policy": f"policies/drl_{regime}.json", "tag": tag}
    if lam:
        sp["lam"] = lam
    return sp


def is_drl(job):
    return job["slicer"].get("type") == "drl"


def olsla(lam):
    return {"type": "olqoe", "h": 0.1, "lam": lam}


NEW_CORE = [echo3(0.0), echo3(1.0), olsla(1.0)]
FC_SWEEP = [{"type": "forecast", "h": h} for h in (0.1, 0.3, 0.5)]


def _add(jobs, base, sls, seeds):
    for sl in sls:
        for s in seeds:
            j = dict(base)
            j["slicer"] = sl
            j["seed"] = s
            jobs.append(j)


def e1_r3(seeds):
    jobs = e1(seeds)
    cells = [(16, 0, 4), (32, 0, 6), (48, 0, 8), (16, 6, 4), (24, 8, 6), (32, 12, 8)]
    for strict in (False, True):
        for nv, ng, nb in cells:
            for abr in ("tput", "dyn", "bola"):
                sc = dict(n_video=nv, n_game=ng, n_bulk=nb, abr=abr, strict=strict)
                sls = list(NEW_CORE) + ([drl("loop"), drl("twin")] if ng > 0 else [])
                _add(jobs, {"exp": "E1", "scenario": sc}, sls, seeds)
    return jobs


def e2_r3(seeds):
    jobs = e2(seeds)
    for abr in ("tput", "dyn"):
        for L in (2.0, 4.0, 6.0):
            for Ts in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
                sc = dict(n_video=24, n_game=8, n_bulk=6, abr=abr, seg_dur=L, Ts=Ts)
                _add(jobs, {"exp": "E2", "scenario": sc}, [echo3(0.0)], seeds)
    return jobs


def e4_r3(seeds):
    jobs = e4(seeds)
    cells = [dict(n_video=32, n_game=0, n_bulk=6, abr="tput"), dict(n_video=24, n_game=8, n_bulk=6, abr="dyn")]
    for device in ("pc", "mobile"):
        for sc in cells:
            _add(jobs, {"exp": "E4", "scenario": dict(sc, device=device)}, [echo3(0.0)], seeds)
    return jobs


def e6_r3(seeds):
    jobs = e6(seeds)
    for pattern in E6_PATTERNS:
        for strict in (False, True):
            sc = dict(E6_MAX, abr="dyn", strict=strict, pattern=pattern, T=1200.0, t_eval0=200.0)
            sls = list(NEW_CORE) + FC_SWEEP + [drl("loop"), drl("twin"), drl("loop", 1.0), drl("twin", 1.0)]
            _add(jobs, {"exp": "E6", "role": "dynamic", "scenario": sc}, sls, seeds)
    return jobs


E7_EXTRA = ([echo3(0.5), echo3(2.0), olsla(0.5), olsla(2.0)] + FC_SWEEP +
            [drl("loop"), drl("twin"), drl("loop", 1.0), drl("twin", 1.0)])


def e7_cells():
    out = []
    for strict in (False, True):
        for mix, (nv, ng, nb) in E7_MIXES.items():
            out.append(("stationary", mix, dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn", strict=strict)))
        for cell, base in (("day_cycle", E7_DAY), ("flash_crowd", E7_FLASH)):
            out.append(("dynamic", cell, dict(base, strict=strict)))
    return out


def e7_r3(seeds):
    jobs = e7(seeds)
    for role, cell, sc in e7_cells():
        _add(jobs, {"exp": "E7", "role": role, "cell": cell, "scenario": sc}, list(NEW_CORE) + E7_EXTRA, seeds)
    return jobs


def ablation_cells():
    """Cells for ablations and robustness (scenario dicts identical to E7/E6/E1, so their best static
    split is reused)."""
    m = E7_MIXES
    st = lambda mix, strict: dict(n_video=m[mix][0], n_game=m[mix][1], n_bulk=m[mix][2], abr="dyn", strict=strict)
    return {"M1T": ("E7", st("M1-video-heavy", True)), "M2F": ("E7", st("M2-gaming-heavy", False)),
            "M3T": ("E7", st("M3-bulk-heavy", True)), "dayT": ("E7", dict(E7_DAY, strict=True)),
            "flashT": ("E7", dict(E7_FLASH, strict=True)),
            "vpT": ("E6", dict(E6_MAX, abr="dyn", strict=True, pattern="video_peak", T=1200.0, t_eval0=200.0)),
            "B3T": ("E1", dict(n_video=24, n_game=8, n_bulk=6, abr="dyn", strict=True))}


ABLATIONS = [
    echo3(tag="abl-prior-only", freeze_after=0.0),
    echo3(tag="abl-no-prior", prior=False, space="share", a0=0.06, c0=0.05, max_step=0.05),
    echo3(tag="abl-no-moves", count_moves=False),
    echo3(tag="abl-no-hold", hold=2.0, settle=1.0),
    echo3(tag="abl-hold6", hold=6.0, settle=3.0),
    echo3(tag="abl-hold24", hold=24.0, settle=12.0),
    echo3(tag="abl-share-space", space="share", a0=0.06, c0=0.05, max_step=0.05),
    echo3(tag="abl-pair-sign", space="share", optimizer="pair"),
    echo3(tag="abl-fixed-gain", gain_decay=False),
    echo3(tag="abl-rate0.5", rate_scale=0.5),
    echo3(tag="abl-rate2", rate_scale=2.0),
    echo3(tag="abl-rate0.5-noprobe", rate_scale=0.5, freeze_after=0.0),
    echo3(tag="abl-rate2-noprobe", rate_scale=2.0, freeze_after=0.0),
    echo3(tag="abl-freeze-at-eval", freeze_after=300.0),
    {"type": "echo2", "alpha": 1.0, "mos_ok": 4.4, "boost_cycles": 4},
]


def e9(seeds):
    jobs = []
    for name, (src, sc) in ablation_cells().items():
        if name == "B3T":
            continue
        _add(jobs, {"exp": "E9", "cell": name, "ref_exp": src, "scenario": sc}, ABLATIONS, seeds)
    return jobs


IMPAIRMENTS = [("delay2s", {"kpm_delay_s": 2.0}), ("delay5s", {"kpm_delay_s": 5.0}), ("drop20", {"kpm_drop": 0.2}),
               ("qnoise0.1", {"qoe_noise": 0.1}), ("qnoise0.3", {"qoe_noise": 0.3}), ("qoe-from-kpm", {"qoe_source": "kpm"})]


def e10(seeds):
    jobs = []
    sls = [echo3(0.0), echo3(1.0), {"type": "forecast", "h": 0.2}, {"type": "olqoe", "h": 0.1}, {"type": "usage"},
           drl("loop")]
    for name in ("M1T", "dayT", "flashT", "B3T"):
        src, sc = ablation_cells()[name]
        for imp, kv in IMPAIRMENTS:
            _add(jobs, {"exp": "E10", "cell": name, "ref_exp": src, "impairment": imp, "scenario": dict(sc, **kv)},
                 sls, seeds)
    return jobs


def x_cells():
    base = dict(n_video=24, n_bulk=6, abr="dyn")
    out = []
    for strict in (False, True):
        out.append(("X1-xr", dict(base, n_game=6, rt_kind="xr", strict=strict)))
        out.append(("X2-xr-l4s", dict(base, n_game=6, rt_kind="xr", bulk_cc="prague", video_cc="prague", strict=strict)))
        out.append(("X3-game-l4s", dict(base, n_game=8, bulk_cc="prague", video_cc="prague", strict=strict)))
    return out


def e11(seeds):
    jobs = []
    sls = [echo3(tag="hint", hint=True), echo3(tag="hint-liar", hint=True, liar="game"),
           echo3(tag="hint-l1", hint=True, lam=1.0)]
    for role, cell, sc in e7_cells():
        _add(jobs, {"exp": "E11", "cell": cell, "ref_exp": "E7", "scenario": sc}, sls, seeds)
    for cell, sc in x_cells():
        if cell.startswith("X1"):
            _add(jobs, {"exp": "E11", "cell": cell, "ref_exp": "E12", "scenario": sc}, sls, seeds)
    return jobs


def e12(seeds):
    jobs = []
    for cell, sc in x_cells():
        sls = _slicers(sc["n_game"], sc["strict"], grid3w()) + list(NEW_CORE) + [drl("loop"), drl("twin")]
        _add(jobs, {"exp": "E12", "cell": cell, "scenario": sc}, sls, seeds)
    return jobs


STEP_CELLS = {
    "video-tput": (dict(n_video=12, n_game=0, n_bulk=2, abr="tput"), 0),
    "video-bola": (dict(n_video=12, n_game=0, n_bulk=2, abr="bola"), 0),
    "video-dyn": (dict(n_video=12, n_game=0, n_bulk=2, abr="dyn"), 0),
    "gaming-gcc": (dict(n_video=0, n_game=6, n_bulk=2), 0),
    "xr-gcc": (dict(n_video=0, n_game=3, n_bulk=2, rt_kind="xr"), 0),
    "bulk-cubic": (dict(n_video=8, n_game=0, n_bulk=4, abr="dyn"), 1),
    "bulk-prague": (dict(n_video=8, n_game=0, n_bulk=4, abr="dyn", bulk_cc="prague"), 1),
}
KNIFE_CELLS = {
    "video-tput": dict(n_video=32, n_game=0, n_bulk=6, abr="tput"),
    "video-dyn": dict(n_video=32, n_game=0, n_bulk=6, abr="dyn"),
    "video-bola": dict(n_video=32, n_game=0, n_bulk=6, abr="bola"),
    "gaming-gcc": dict(n_video=0, n_game=12, n_bulk=6),
    "xr-gcc": dict(n_video=0, n_game=6, n_bulk=6, rt_kind="xr"),
}


def e13(seeds):
    jobs = []
    for cls, (sc, k) in STEP_CELLS.items():
        sc = dict(sc, strict=True, T=1200.0, t_eval0=1100.0, min_eval_s=30.0)
        _add(jobs, {"exp": "E13", "role": "steps", "cell": cls, "trace": 1.0, "scenario": sc},
             [{"type": "steps", "k": k, "lo": 0.1, "hi": 0.6}], seeds)
    hs = [round(0.02 * i, 2) for i in range(16)]
    for cls, sc in KNIFE_CELLS.items():
        for strict in (False, True):
            _add(jobs, {"exp": "E13", "role": "knife", "cell": cls, "scenario": dict(sc, strict=strict)},
                 [{"type": "forecast", "h": h} for h in hs], seeds)
    for alpha in (0.2, 1.0):
        for L in (2.0, 4.0, 6.0):
            for Ts in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
                sc = dict(n_video=24, n_game=8, n_bulk=6, abr="tput", seg_dur=L, Ts=Ts)
                _add(jobs, {"exp": "E13", "role": "resonance", "cell": f"usage-a{alpha:g}", "scenario": sc},
                     [{"type": "usage", "alpha": alpha}], seeds)
    return jobs


CONV_CELLS = {"M1F": ("E7", "M1-video-heavy", False), "M1T": ("E7", "M1-video-heavy", True),
              "M2F": ("E7", "M2-gaming-heavy", False), "M2T": ("E7", "M2-gaming-heavy", True),
              "M3F": ("E7", "M3-bulk-heavy", False), "M3T": ("E7", "M3-bulk-heavy", True)}


def e14(seeds):
    jobs = []
    sls = [{"type": "echo2", "alpha": 1.0, "mos_ok": 4.4, "boost_cycles": 4}, echo3(0.0), echo3(1.0),
           {"type": "forecast", "h": 0.2}, {"type": "olqoe", "h": 0.1}, drl("loop")]
    for name, (src, mix, strict) in CONV_CELLS.items():
        nv, ng, nb = E7_MIXES[mix]
        base = dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn", strict=strict)
        sc = dict(base, T=1800.0, t_eval0=0.0, chunk_s=60.0, min_eval_s=30.0)
        _add(jobs, {"exp": "E14", "cell": name, "ref_exp": src, "ref_scenario": base, "scenario": sc}, sls, seeds)
    return jobs


# ============================================================================ round 4 (review)
# Equally informed baselines and the count-plus-template prior on its own, everywhere the main
# results are reported; holds long enough for GCC; random trial order; per-slice template errors;
# workload families that were never used for tuning.
PRIOR_ONLY = echo3(tag="prior-only", freeze_after=0.0)                       # counts + template, no trials
PROBE_PRIOR = echo3(tag="probe-prior", space="share", a0=0.06, c0=0.05, max_step=0.05)   # SPSA on shares from the same prior


def main_cells():
    """(ref experiment, cell label, scenario, three-slice?) for every scenario of the main results."""
    out = []
    for strict in (False, True):
        for nv, ng, nb in [(16, 0, 4), (32, 0, 6), (48, 0, 8), (16, 6, 4), (24, 8, 6), (32, 12, 8)]:
            for abr in ("tput", "dyn", "bola"):
                out.append(("E1", f"{nv}v/{ng}g/{nb}b-{abr}", dict(n_video=nv, n_game=ng, n_bulk=nb, abr=abr, strict=strict), ng > 0))
    for pattern in E6_PATTERNS:
        for strict in (False, True):
            out.append(("E6", pattern, dict(E6_MAX, abr="dyn", strict=strict, pattern=pattern, T=1200.0, t_eval0=200.0), True))
    for role, cell, sc in e7_cells():
        out.append(("E7", cell, sc, True))
    for cell, sc in x_cells():
        out.append(("E12", cell, sc, True))
    return out


def e15(seeds):
    jobs = []
    for src, cell, sc, three in main_cells():
        sls = [PRIOR_ONLY, PROBE_PRIOR] + ([drl("prior")] if three else [])
        _add(jobs, {"exp": "E15", "cell": cell, "ref_exp": src, "scenario": sc}, sls, seeds)
    return jobs


R4_VARIANTS = [
    echo3(tag="hold36", hold=36.0, settle=30.0),
    echo3(tag="hold54", hold=54.0, settle=48.0),          # burn-in 48 s >= GCC's measured 47.6 s
    echo3(tag="hold60", hold=60.0, settle=54.0),
    echo3(tag="rand-order", rand_order=True),
    echo3(tag="rand-order-hold54", rand_order=True, hold=54.0, settle=48.0),
    echo3(tag="video0.5", rates={"video": 3.0e6}), echo3(tag="video0.5-noprobe", rates={"video": 3.0e6}, freeze_after=0.0),
    echo3(tag="video2", rates={"video": 12.0e6}), echo3(tag="video2-noprobe", rates={"video": 12.0e6}, freeze_after=0.0),
    echo3(tag="game0.5", rates={"game": 6.0e6}), echo3(tag="game0.5-noprobe", rates={"game": 6.0e6}, freeze_after=0.0),
    echo3(tag="game2", rates={"game": 24.0e6}), echo3(tag="game2-noprobe", rates={"game": 24.0e6}, freeze_after=0.0),
]


def e16(seeds):
    jobs = []
    for name, (src, sc) in ablation_cells().items():
        if name == "B3T":
            continue
        _add(jobs, {"exp": "E16", "cell": name, "ref_exp": src, "scenario": sc}, R4_VARIANTS, seeds)
    return jobs


R5_COUNTS = [
    echo3(tag="count-activity", count_src="activity"),
    echo3(tag="count-linger10", count_src="linger", linger=10.0),
    echo3(tag="prior-only-activity", count_src="activity", freeze_after=0.0),
    echo3(tag="prior-only-linger10", count_src="linger", linger=10.0, freeze_after=0.0),
]


def e20(seeds):
    """Session counts taken from radio activity instead of a session counter (second review)."""
    jobs = []
    for name, (src, sc) in ablation_cells().items():
        if name == "B3T":
            continue
        _add(jobs, {"exp": "E20", "cell": name, "ref_exp": src, "scenario": sc}, R5_COUNTS, seeds)
    return jobs


HELDOUT_FAMILIES = {"bw40": {"B": 106}, "sinr6": {"sinr_mean_db": 6.0}, "seg2": {"seg_dur": 2.0}}


def e17(seeds):
    """Workload families never used to pick the template rates or any EchoSlice parameter:
    a 40 MHz cell, poor coverage, and 2 s video segments. Strict mode, own static grid."""
    jobs = []
    grid = grid3w()
    bases = [(mix, dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn")) for mix, (nv, ng, nb) in E7_MIXES.items()]
    bases.append(("flash_crowd", dict(E7_FLASH)))
    sls = ([{"type": "usage"}, {"type": "forecast", "h": 0.2}, {"type": "olqoe", "h": 0.1}, ECHO2, {"type": "static"}] +
           [{"type": "static", "x": x} for x in grid] +
           [echo3(0.0), PRIOR_ONLY, PROBE_PRIOR, drl("loop"), drl("twin"), drl("prior")])
    for fam, kv in HELDOUT_FAMILIES.items():
        for mix, base in bases:
            sc = dict(base, strict=True, **kv)
            _add(jobs, {"exp": "E17", "cell": f"{fam}:{mix}", "family": fam, "scenario": sc}, sls, seeds)
    return jobs


def e18(seeds):
    jobs = []
    for name, (src, mix, strict) in CONV_CELLS.items():
        nv, ng, nb = E7_MIXES[mix]
        base = dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn", strict=strict)
        sc = dict(base, T=1800.0, t_eval0=0.0, chunk_s=60.0, min_eval_s=30.0)
        _add(jobs, {"exp": "E18", "cell": name, "ref_exp": src, "ref_scenario": base, "scenario": sc},
             [PRIOR_ONLY, PROBE_PRIOR, drl("prior")], seeds)
    return jobs


def e19(seeds):
    jobs = []
    for name in ("M1T", "dayT", "flashT", "B3T"):
        src, sc = ablation_cells()[name]
        for imp, kv in IMPAIRMENTS:
            _add(jobs, {"exp": "E19", "cell": name, "ref_exp": src, "impairment": imp, "scenario": dict(sc, **kv)},
                 [PRIOR_ONLY, drl("prior")], seeds)
    return jobs


# ---------------------------------------------------------------- final review round (E21-E26)
# The QoE feedback baseline and the gated variant are tuned on seeds 101-104 (E27) before the main runs.
# diagnostics/round5/select_tuned.py writes the chosen settings to diagnostics/round5/tuned.json.
_TUNED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagnostics", "round5", "tuned.json")
_T = json.load(open(_TUNED)) if os.path.exists(_TUNED) else {}
FB_STEP, FB_BAND = _T.get("fb_step", 0.05), _T.get("fb_band", 0.5)
GATE_M, GATE_TOL = _T.get("gate_m", 4), _T.get("gate_tol", 0.04)
GATED = echo3(tag="gated", gate=True, gate_m=GATE_M, gate_tol=GATE_TOL)   # trials stop once settled, reopen on a QoE drop
QOE_FB = {"type": "qoefb", "tag": "qoe-feedback", "fb_step": FB_STEP, "fb_band": FB_BAND}


def drl_seed(regime, s):
    return {"type": "drl", "policy": f"policies/drl_{regime}_s{s}.json", "tag": f"drl-{regime}-s{s}"}


def _own_grid_sls(extra):
    grid = grid3w()
    return [{"type": "static"}] + [{"type": "static", "x": x} for x in grid] + list(extra)


R6_BASES = {"M1T": dict(n_video=56, n_game=4, n_bulk=2, abr="dyn", strict=True),
            "BALT": dict(n_video=32, n_game=12, n_bulk=8, abr="dyn", strict=True),
            "M3T": dict(n_video=8, n_game=4, n_bulk=16, abr="dyn", strict=True)}
R6_EVENTS = {"none": [], "ladder2": [[900.0, "ladder", 2.0]], "ladder0.5": [[900.0, "ladder", 0.5]],
             "sinr-6": [[900.0, "sinr", -6.0]]}
R6_CORE = [echo3(0.0), GATED, PRIOR_ONLY, PROBE_PRIOR, QOE_FB, {"type": "forecast", "h": 0.2}]


def e21(seeds):
    """The prior becomes wrong during a run: at 900 s video needs twice (or half) the rate per rung, or every
    user's SINR drops by 6 dB. Session counts do not change. 1800 s runs scored per minute, own static grid."""
    jobs = []
    sls = _own_grid_sls(R6_CORE + [drl("loop"), drl("prior")])
    for b, base in R6_BASES.items():
        for ev, evs in R6_EVENTS.items():
            sc = dict(base, T=1800.0, t_eval0=300.0, chunk_s=60.0, min_eval_s=30.0, events=evs)
            _add(jobs, {"exp": "E21", "cell": f"{b}:{ev}", "event": ev, "scenario": sc}, sls, seeds)
    return jobs


R6_LIGHT = {"L1-8s": dict(n_video=8, n_game=2, n_bulk=2, seg_dur=8.0),
            "L2-8s": dict(n_video=12, n_game=4, n_bulk=2, seg_dur=8.0),
            "L3-4s": dict(n_video=16, n_game=4, n_bulk=4, seg_dur=4.0),
            "M1-8s": dict(n_video=56, n_game=4, n_bulk=2, seg_dur=8.0)}
R6_COUNT_SLS = ([echo3(tag="count-session"), echo3(tag="count-activity", count_src="activity")] +
                [echo3(tag=f"count-linger{int(L)}", count_src="linger", linger=L) for L in (2.0, 5.0, 10.0, 20.0, 30.0)] +
                [echo3(tag="prior-only-session", freeze_after=0.0),
                 echo3(tag="prior-only-activity", count_src="activity", freeze_after=0.0),
                 echo3(tag="prior-only-linger10", count_src="linger", linger=10.0, freeze_after=0.0)])


def e22(seeds):
    """Session-count estimators in light cells and with long segments, where players idle more."""
    jobs = []
    sls = _own_grid_sls(R6_COUNT_SLS)
    for name, kv in R6_LIGHT.items():
        sc = dict(kv, abr="dyn", strict=True)
        _add(jobs, {"exp": "E22", "cell": name, "scenario": sc}, sls, seeds)
    return jobs


R6_DEPART = {"churn-abandon": dict(n_video=32, n_game=12, n_bulk=8, pattern="churn", abandon_stall_s=8.0,
                                   T=1200.0, t_eval0=200.0),
             "M1-abandon": dict(n_video=56, n_game=4, n_bulk=2, abandon_stall_s=8.0),
             "files-bal": dict(n_video=32, n_game=12, n_bulk=40, bulk_files_mb=300.0, T=1200.0, t_eval0=200.0),
             "files-bulkheavy": dict(n_video=8, n_game=4, n_bulk=80, bulk_files_mb=300.0, T=1200.0, t_eval0=200.0)}


def e23(seeds):
    """Departures that depend on the shares: video users who leave after a long stall, and finite bulk files."""
    jobs = []
    sls = _own_grid_sls(R6_CORE + [{"type": "usage"}, drl("loop"), drl("prior")])
    for name, kv in R6_DEPART.items():
        sc = dict(kv, abr="dyn", strict=True)
        _add(jobs, {"exp": "E23", "cell": name, "scenario": sc}, sls, seeds)
    return jobs


R6_FACTORS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0)


def e24(seeds):
    """How wrong the templates must be before the trials pay off: both rates scaled by a factor."""
    jobs = []
    for name, (src, sc) in ablation_cells().items():
        if name == "B3T":
            continue
        sls = []
        for f in R6_FACTORS:
            r = {"video": 6.0e6 * f, "game": 12.0e6 * f}
            sls += [echo3(tag=f"tf{f:g}-echo", rates=r), dict(GATED, tag=f"tf{f:g}-gated", rates=r),
                    echo3(tag=f"tf{f:g}-prior", rates=r, freeze_after=0.0),
                    dict(QOE_FB, tag=f"tf{f:g}-qoefb", rates=r)]
        _add(jobs, {"exp": "E24", "cell": name, "ref_exp": src, "scenario": sc}, sls, seeds)
    return jobs


def heldout_cells():
    bases = [(mix, dict(n_video=nv, n_game=ng, n_bulk=nb, abr="dyn")) for mix, (nv, ng, nb) in E7_MIXES.items()]
    bases.append(("flash_crowd", dict(E7_FLASH)))
    return [(f"{fam}:{mix}", dict(base, strict=True, **kv)) for fam, kv in HELDOUT_FAMILIES.items() for mix, base in bases]


def e25(seeds):
    """The gated variant and the QoE feedback baseline in all 72 scenarios of the overall table."""
    jobs = []
    for src, cell, sc, three in main_cells():
        _add(jobs, {"exp": "E25", "cell": cell, "ref_exp": src, "scenario": sc}, [GATED, QOE_FB], seeds)
    for cell, sc in heldout_cells():
        _add(jobs, {"exp": "E25", "cell": cell, "ref_exp": "E17", "scenario": sc}, [GATED, QOE_FB], seeds)
    return jobs


PPO_SEEDS = (1, 2)


def e26(seeds):
    """Extra PPO training seeds (PPO-Loop and PPO-Prior) in the 18 changing and 12 held-out scenarios."""
    jobs = []
    sls = [drl_seed(r, s) for r in ("loop", "prior") for s in PPO_SEEDS]
    for src, cell, sc, three in main_cells():
        if src in ("E6", "E7"):
            _add(jobs, {"exp": "E26", "cell": cell, "ref_exp": src, "scenario": sc}, sls, seeds)
    for cell, sc in heldout_cells():
        _add(jobs, {"exp": "E26", "cell": cell, "ref_exp": "E17", "scenario": sc}, sls, seeds)
    return jobs


TUNE_SEEDS = (101, 102, 103, 104)
TUNE_FB = [(s, b) for s in (0.025, 0.05, 0.1, 0.2) for b in (0.25, 0.5, 0.75, 1.0)]
TUNE_GATE = [(4, 0.04), (3, 0.06), (3, 0.1), (2, 0.1), (2, 0.2)]


def e27(seeds):
    """Tuning runs on seeds 101-104 only, in the six ablation cells: QoE feedback step and band, and the
    gated variant's settle rule. Selection by mean user QoE (no static reference is needed)."""
    jobs = []
    sls = ([{"type": "qoefb", "tag": f"fb-s{s:g}-b{b:g}", "fb_step": s, "fb_band": b} for s, b in TUNE_FB] +
           [echo3(tag=f"gated-m{m}-t{t:g}", gate=True, gate_m=m, gate_tol=t) for m, t in TUNE_GATE] +
           [echo3(tag="echo"), echo3(tag="prior", freeze_after=0.0)])
    for name, (src, sc) in ablation_cells().items():
        if name == "B3T":
            continue
        _add(jobs, {"exp": "E27", "cell": name, "scenario": sc}, sls, list(TUNE_SEEDS))
    return jobs


EXPERIMENTS = {"E1": e1_r3, "E2": e2_r3, "E4": e4_r3, "E5": e5, "E6": e6_r3, "E7": e7_r3,
               "E9": e9, "E10": e10, "E11": e11, "E12": e12, "E13": e13, "E14": e14,
               "E15": e15, "E16": e16, "E17": e17, "E18": e18, "E19": e19, "E20": e20,
               "E21": e21, "E22": e22, "E23": e23, "E24": e24, "E25": e25, "E26": e26, "E27": e27}
TITLES = {"E1": "effect size", "E2": "slicer period", "E4": "QoE-model sensitivity",
          "E5": "forecast headroom", "E6": "dynamic load", "E7": "unbalanced and shifting",
          "E9": "ablations", "E10": "imperfect telemetry", "E11": "app hints", "E12": "XR and L4S",
          "E13": "theory checks", "E14": "convergence",
          "E15": "equal-info baselines", "E16": "holds and templates", "E17": "held-out families", "E20": "count source",
          "E18": "convergence, round 4", "E19": "telemetry, round 4",
          "E21": "mid-run mismatch", "E22": "count estimators", "E23": "endogenous departures",
          "E24": "template error sweep", "E25": "gated and QoE feedback", "E26": "PPO training seeds",
          "E27": "tuning, round 6"}


def build(exp, n_seeds):
    seeds = list(range(1, n_seeds + 1))
    return EXPERIMENTS[exp](seeds)


if __name__ == "__main__":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    tot = 0
    drl_tot = 0
    for e in (sys.argv[1].split(",") if sys.argv[1] != "ALL" else EXPERIMENTS):
        j = build(e, n)
        nd = sum(1 for x in j if is_drl(x))
        tot += len(j)
        drl_tot += nd
        print(f"{e:3s} {TITLES[e]:24s} {len(j):7d} runs ({nd} DRL)")
    print(f"total {tot} runs ({drl_tot} DRL)")
