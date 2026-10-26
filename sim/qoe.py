"""QoE models used by the gate pilot.

Video   : ITU-T P.1203 mode 0 (reference implementation itu-p1203, pc/1080p
          display by default). Used for all reported video MOS.
Gaming  : simplified G.1072-style impairment model on an R scale (coding,
          delay and late-frame impairments), mapped to MOS with the G.107
          R-to-MOS curve. A placeholder for the full G.1072 model.
Bulk    : log-throughput MOS (G.1030-style), MOS 1 at T_lo and 5 at T_hi.
A fast video proxy (per-level P.1203 MOS minus stall/switch penalties) is
used online by QoE-aware slicers, never for reported results.
"""
import logging
import numpy as np

def _quiet():
    for n in list(logging.root.manager.loggerDict):
        if "p1203" in n:
            lg = logging.getLogger(n)
            lg.setLevel(logging.CRITICAL)
            lg.propagate = False
            for h in list(lg.handlers):
                h.setLevel(logging.CRITICAL)

# Apple HLS authoring spec, H.264 16:9 ladder (kb/s, resolution)
LADDER_KBPS = np.array([145, 365, 730, 1100, 2000, 3000, 4500, 6000, 7800], dtype=float)
LADDER_RES = ["416x234", "640x360", "768x432", "768x432", "960x540",
              "1280x720", "1280x720", "1920x1080", "1920x1080"]
LADDER_BPS = LADDER_KBPS * 1e3

# P.1203 MOS of a stall-free 300 s session held at one level (pc, 1080p display)
LEVEL_MOS_PC = np.array([1.878, 2.690, 3.411, 3.496, 4.168, 4.713, 4.793, 4.850, 4.837])
LEVEL_MOS_MOBILE = np.array([2.100, 3.203, 3.785, 3.888, 4.462, 4.806, 4.806, 4.837, 4.837])


def p1203_session(levels, seg_dur, stalls, device="pc"):
    """levels: ladder index per segment in play order.
    stalls: list of (media_time_s, duration_s) inside the session."""
    from itu_p1203 import P1203Standalone
    _quiet()
    if len(levels) == 0:
        return 1.0
    segs = []
    t = 0.0
    for lv in levels:
        segs.append({"bitrate": float(LADDER_KBPS[lv]), "codec": "h264",
                     "duration": float(seg_dur), "fps": 30.0,
                     "resolution": LADDER_RES[lv], "start": t})
        t += seg_dur
    st = [[0.0, 0.0]] + [[float(m), float(d)] for (m, d) in stalls if d > 0]
    inp = {"I11": {"segments": [{"bitrate": 128, "codec": "aaclc", "duration": t, "start": 0}],
                   "streamId": 1},
           "I13": {"segments": segs, "streamId": 1},
           "I23": {"stalling": st, "streamId": 1},
           "IGen": {"device": device, "displaySize": "1920x1080", "viewingDistance": "150cm"}}
    return float(P1203Standalone(inp).calculate_complete()["O46"])


def video_proxy(levels, stall_time, n_stalls, window_s, device="pc"):
    """Fast P.1203-like proxy for online use. Coefficients fitted against
    P.1203 on simulated sessions (see calibrate_proxy in experiments)."""
    tab = LEVEL_MOS_PC if device == "pc" else LEVEL_MOS_MOBILE
    if len(levels) == 0:
        return 1.0
    lv = np.asarray(levels)
    base = tab[lv].mean()
    sw = np.abs(np.diff(tab[lv])).sum() / max(window_s / 60.0, 1e-6) if len(lv) > 1 else 0.0
    m = base - PROXY_COEF["switch"] * sw - PROXY_COEF["stall_n"] * n_stalls / max(window_s / 60.0, 1e-6) \
        - PROXY_COEF["stall_frac"] * stall_time / window_s
    return float(np.clip(m, 1.0, 5.0))


PROXY_COEF = {"switch": 0.08, "stall_n": 0.35, "stall_frac": 4.0}


def r_to_mos(R):
    R = np.clip(R, 0.0, 100.0)
    return 1.0 + 0.035 * R + R * (R - 60.0) * (100.0 - R) * 7e-6


# Real-time classes: (coding saturation rate r0 [bit/s], delay knee d0 [ms RTT], delay slope kd [R per ms]).
# Cloud gaming follows the simplified G.1072-style model below; XR (split rendering / volumetric
# streaming) needs a higher rate and is more delay-sensitive. XR values are modelling assumptions.
RT_QOE = {"game": (5e6, 50.0, 0.15), "xr": (20e6, 30.0, 0.30)}
# GCC rate bounds and one-way frame budget per real-time class (bit/s, bit/s, s)
RT_SENDER = {"game": (1.0e6, 20.0e6, 0.100), "xr": (5.0e6, 60.0e6, 0.020)}


def game_mos(rate_bps, rtt_s, late_frac, kind="game"):
    """Simplified G.1072-style model. rate: mean encoded bitrate; rtt: mean
    network round-trip incl. queueing; late_frac: share of time a frame would
    miss the class's one-way budget (100 ms gaming, 20 ms XR)."""
    r0, d0, kd = RT_QOE[kind]
    rate = np.asarray(rate_bps, dtype=float)
    i_cod = 60.0 * np.exp(-rate / r0)
    i_del = np.maximum(0.0, np.asarray(rtt_s) * 1000.0 - d0) * kd
    i_late = np.minimum(60.0, 250.0 * np.asarray(late_frac))
    return r_to_mos(100.0 - i_cod - i_del - i_late)


BULK_T_LO = 1e6
BULK_T_HI = 100e6


def bulk_mos(tput_bps, t_lo=None, t_hi=None):
    lo = BULK_T_LO if t_lo is None else t_lo
    hi = BULK_T_HI if t_hi is None else t_hi
    x = np.log(np.maximum(np.asarray(tput_bps, dtype=float), 1.0) / lo) / np.log(hi / lo)
    return 1.0 + 4.0 * np.clip(x, 0.0, 1.0)


def video_rate_mos(rate_bps, device="pc"):
    """MOS of a stall-free stream as a function of per-client rate, for
    open-loop QoE optimisers: highest ladder level the rate can carry."""
    tab = LEVEL_MOS_PC if device == "pc" else LEVEL_MOS_MOBILE
    r = np.asarray(rate_bps, dtype=float)
    idx = np.searchsorted(LADDER_BPS, r, side="right") - 1
    out = np.where(idx < 0, 1.0 + (tab[0] - 1.0) * r / LADDER_BPS[0], tab[np.clip(idx, 0, None)])
    return out
