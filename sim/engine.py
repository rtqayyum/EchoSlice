"""Scenario set-up, the slicer loop, and end-of-run metrics."""
from collections import namedtuple
from dataclasses import dataclass, field, asdict
import math
import numpy as np

from . import kernel as K
from . import qoe

MAXSEG = 700
MAXST = 300


@dataclass
class Scenario:
    n_video: int = 24
    n_game: int = 0
    n_bulk: int = 4
    abr: str = "tput"            # tput | bola | dyn | mix
    seg_dur: float = 4.0
    T: float = 600.0             # simulated seconds
    t_eval0: float = 300.0       # metrics over [t_eval0, T]
    Ts: float = 1.0              # slicer period (s)
    strict: bool = False         # True: dedicated shares, no PRB sharing
    B: int = 273                 # 100 MHz, 30 kHz SCS
    dt: float = 0.01
    sinr_mean_db: float = 12.0
    sinr_std_db: float = 6.0
    shadow_sigma_db: float = 4.0
    shadow_tau_s: float = 2.0
    fast_sigma_db: float = 1.5
    layers: float = 2.0
    rtt_video: float = 0.030
    rtt_bulk: float = 0.040
    rtt_game: float = 0.020
    qmax_video: float = 3e6
    qmax_bulk: float = 3e6
    qmax_game: float = 1e6
    device: str = "pc"
    bulk_start: float = 0.0      # set > 0 for a load step
    n_bulk_late: int = 0         # extra bulk flows that start at bulk_start
    pattern: str = ""            # "" | game_surge | bulk_wave | video_peak | churn
    base_frac: float = 0.34      # share of a class's flows that are always on under a pattern
    chunk_s: float = 300.0       # QoE is scored in windows of this length (P.1203 is valid up to ~5 min)
    min_eval_s: float = 60.0     # a flow needs this much active time in a window to be scored
    jitter_s: float = 30.0       # spread of scheduled arrivals/departures (E7 schedules)
    # app classes (round 3)
    rt_kind: str = "game"        # real-time class in the 'game' slice: game (cloud gaming) | xr
    bulk_cc: str = "cubic"       # cubic | prague (L4S: TCP Prague + ECN marking at ~1 ms queue delay)
    video_cc: str = "cubic"      # cubic | prague (DASH over L4S)
    cbr: list = field(default_factory=list)   # per-flow fixed rates (bit/s): open-loop twin, apps do not adapt
    # telemetry seen by the slicer (round 3 robustness)
    kpm_delay_s: float = 0.0     # KPM and QoE reports reach the xApp this late
    kpm_drop: float = 0.0        # probability that a period's report is lost (the slicer keeps its shares)
    qoe_noise: float = 0.0       # std of the error of the RAN-side per-flow QoE estimate (MOS)
    qoe_source: str = "ideal"    # ideal (app-level logs) | kpm (QoE inferred from served rate and queue delay only)
    # final review round: mid-run changes and endogenous departures
    events: list = field(default_factory=list)  # [[t, "ladder", f]] video needs f x the rate per rung from t on;
                                                 # [[t, "sinr", d]] every user's mean SINR shifts by d dB at t
    abandon_stall_s: float = 0.0  # > 0: a video user leaves when one stall lasts this long (rest of session at MOS 1)
    bulk_files_mb: float = 0.0    # > 0: bulk flows are finite files of mean size (MB), arriving over the run

    def slices(self):
        s = []
        if self.n_video > 0:
            s.append("video")
        if self.n_game > 0:
            s.append("game")
        if self.n_bulk + self.n_bulk_late > 0:
            s.append("bulk")
        return s


def bola_params(device="pc", stable_buf=12.0):
    """dash.js BolaRule parameterisation."""
    br = qoe.LADDER_BPS
    util = np.log(br) - np.log(br[0]) + 1.0
    buffer_time = max(stable_buf, 10.0 + 2.0 * len(br))
    gp = (util[-1] - 1.0) / (buffer_time / 10.0 - 1.0)
    Vp = 10.0 / gp
    return util, Vp, gp


INF = 1e18

# Explicit load schedules for E7 (flow counts per class over time).
SCHEDULES = {
    # compressed day: video-heavy evening (0-800 s), gaming-heavy night (800-1400 s), bulk backups (1400-2000 s)
    "day_cycle": {
        K.VIDEO: [(8, 0.0, INF), (4, 0.0, 1400.0), ("rest", 0.0, 800.0)],
        K.GAME: [(4, 0.0, INF), ("rest", 800.0, 1400.0)],
        K.BULK: [(2, 0.0, INF), ("rest", 1400.0, INF)],
    },
    # sudden 10x gaming crowd (600-900 s) that pushes the cell close to overload
    "flash_crowd": {
        K.GAME: [(2, 0.0, INF), ("rest", 600.0, 900.0)],
    },
}


def session_windows(sc, ftype, t_start, rng):
    """Start/stop time of every flow. With no pattern all flows stay on.
    Under a pattern, a base share of each class stays on and the rest
    follow the pattern, so the load changes during the run."""
    t_stop = np.full(len(ftype), INF)
    if not sc.pattern:
        return t_start, t_stop
    if sc.pattern in SCHEDULES:
        # explicit schedule: per class, groups of (count, start, stop); 'rest' takes the remaining flows.
        # Scheduled boundaries (not 0 / INF) get +-30 s jitter so arrivals are staggered.
        for c, groups in SCHEDULES[sc.pattern].items():
            idx = list(np.where(ftype == c)[0])
            for cnt, a, b in groups:
                take = idx if cnt == "rest" else idx[:cnt]
                idx = [] if cnt == "rest" else idx[cnt:]
                for i in take:
                    if a > 0:
                        t_start[i] = a + rng.uniform(-sc.jitter_s, sc.jitter_s)
                    if b < INF:
                        t_stop[i] = b + rng.uniform(-sc.jitter_s, sc.jitter_s)
        return t_start, t_stop
    cls_of = {"game_surge": K.GAME, "bulk_wave": K.BULK, "video_peak": K.VIDEO}
    for c in (K.VIDEO, K.GAME, K.BULK):
        idx = np.where(ftype == c)[0]
        if len(idx) == 0:
            continue
        if sc.pattern != "churn" and cls_of.get(sc.pattern) != c:
            continue
        nb = max(1, int(round(sc.base_frac * len(idx))))
        extra = idx[nb:]
        for i in extra:
            if sc.pattern == "game_surge":
                t_start[i], t_stop[i] = rng.uniform(480, 520), rng.uniform(830, 870)
            elif sc.pattern == "bulk_wave":
                t_start[i], t_stop[i] = rng.uniform(430, 470), rng.uniform(880, 920)
            elif sc.pattern == "video_peak":
                t_start[i], t_stop[i] = rng.uniform(400, 600), rng.uniform(900, 1100)
            elif sc.pattern == "churn":
                L = rng.uniform(200, 600)
                a = rng.uniform(0, max(1.0, sc.T - L))
                t_start[i], t_stop[i] = a, a + L
    return t_start, t_stop


def build_state(sc: Scenario, seed: int):
    rng = np.random.default_rng(seed)
    names = sc.slices()
    sidx = {n: i for i, n in enumerate(names)}
    ft, sl, rtt, qm, tst, abr = [], [], [], [], [], []
    abr_map = {"tput": K.ABR_TPUT, "bola": K.ABR_BOLA, "dyn": K.ABR_DYN}
    for j in range(sc.n_video):
        ft.append(K.VIDEO); sl.append(sidx["video"]); rtt.append(sc.rtt_video); qm.append(sc.qmax_video)
        tst.append(rng.uniform(0, 10))
        if sc.abr == "mix":
            abr.append([K.ABR_TPUT, K.ABR_BOLA, K.ABR_DYN][j % 3])
        else:
            abr.append(abr_map[sc.abr])
    for j in range(sc.n_game):
        ft.append(K.GAME); sl.append(sidx["game"]); rtt.append(sc.rtt_game); qm.append(sc.qmax_game)
        tst.append(rng.uniform(0, 5)); abr.append(0)
    for j in range(sc.n_bulk + sc.n_bulk_late):
        ft.append(K.BULK); sl.append(sidx["bulk"]); rtt.append(sc.rtt_bulk); qm.append(sc.qmax_bulk)
        if j < sc.n_bulk:
            tst.append(rng.uniform(0, 5))
        else:
            tst.append(sc.bulk_start + rng.uniform(0, 2))
        abr.append(0)
    N = len(ft)
    tst, tsp = session_windows(sc, np.array(ft), np.array(tst, dtype=float), rng)
    if sc.bulk_files_mb > 0:
        # finite transfers: the bulk pool arrives at uniform random times over the run (a Poisson stream given
        # the count); each flow stops when its file is done, so the number of active bulk flows is endogenous
        bi = np.where(np.array(ft) == K.BULK)[0]
        tst[bi] = np.sort(rng.uniform(0.0, sc.T * 0.95, len(bi)))
        tsp[bi] = INF
    ftn = np.array(ft, dtype=np.int64)
    gmin, gmax, glate = qoe.RT_SENDER[sc.rt_kind]
    cc = np.zeros(N, dtype=np.int64)
    if sc.bulk_cc == "prague":
        cc[ftn == K.BULK] = K.CC_PRAGUE
    if sc.video_cc == "prague":
        cc[ftn == K.VIDEO] = K.CC_PRAGUE
    cbr = np.zeros(N)
    if sc.cbr:
        assert len(sc.cbr) == N, "cbr needs one rate per flow"
        cbr = np.maximum(np.asarray(sc.cbr, dtype=float), 1.0)
    enc0 = np.where((ftn == K.GAME) & (cbr > 0), cbr, 2e6)
    n_chunk = max(1, int(math.ceil((sc.T - sc.t_eval0) / sc.chunk_s - 1e-9)))
    f = lambda v=0.0: np.full(N, v, dtype=np.float64)
    c_ = lambda: np.zeros((N, n_chunk))
    i_ = lambda v=0: np.full(N, v, dtype=np.int64)
    sinr = np.clip(rng.normal(sc.sinr_mean_db, sc.sinr_std_db, N), -5.0, 28.0)
    d = dict(
        p_dt=np.array([sc.dt]), p_B=np.array([float(sc.B)]), p_strict=np.array([int(sc.strict)]),
        p_rho=np.array([math.exp(-sc.dt / sc.shadow_tau_s)]), p_sig_shadow=np.array([sc.shadow_sigma_db]),
        p_sig_fast=np.array([sc.fast_sigma_db]), p_layers=np.array([sc.layers]),
        p_t_eval0=np.array([sc.t_eval0]), p_init_tput=np.array([1.0e6]), p_chunk=np.array([sc.chunk_s]),
        t=np.zeros(1),
        ftype=np.array(ft, dtype=np.int64), fslice=np.array(sl, dtype=np.int64),
        sinr_mean=sinr, shadow=rng.normal(0, sc.shadow_sigma_db, N), rprb=f(),
        base_rtt=np.array(rtt), t_start=tst, t_stop=tsp, stopped=i_(), q=f(), qmax=np.array(qm),
        srate=f(), srtt=np.array(rtt), cwnd=f(K.IW), ssthresh=f(K.RWND), wmax=f(K.IW),
        epoch=f(), last_loss=f(-10.0), in_ss=i_(1), last_active=f(),
        acc_arr=f(), acc_srv=f(), acc_qd=f(),
        acc_arr_k=np.zeros(len(names)), acc_srv_k=np.zeros(len(names)), acc_prb_k=np.zeros(len(names)),
        ev_srv=f(), ev_lost=f(), ev_time=f(), ev_qd=f(), ev_rate=f(), ev_late=f(),
        evc_srv=c_(), evc_time=c_(), evc_qd=c_(), evc_rate=c_(), evc_late=c_(),
        vstate=i_(K.V_IDLE), unsent=f(), undeliv=f(), seg_dur=f(sc.seg_dur), t_first=f(),
        seg_bytes=f(), ewf=f(), ewf_w=f(), ews=f(), ews_w=f(), seg_idx=i_(),
        seg_level=np.full((N, MAXSEG), -1, dtype=np.int64), seg_tdone=np.zeros((N, MAXSEG)),
        seg_tput=np.zeros((N, MAXSEG)), buf=f(), level=i_(), playing=i_(), played=f(),
        stall_t0=f(), stall_media=f(), started=i_(), n_stall=i_(),
        st_wall=np.zeros((N, MAXST)), st_dur=np.zeros((N, MAXST)), st_media=np.zeros((N, MAXST)),
        t_play0=f(), abr=np.array(abr, dtype=np.int64), use_bola=i_(), t_req=f(),
        enc_rate=enc0.astype(np.float64), g_sent=f(), g_recv_acc=f(), g_lost=f(), g_tnext=f(), g_smooth=f(),
        g_ptr=i_(), g_dly=np.zeros((N, K.GCC_WIN)), g_tim=np.zeros((N, K.GCC_WIN)), g_n=i_(),
        g_recv=f(2e6), g_gamma=f(12.5), g_over_t=f(-1.0), g_ocount=i_(), g_hyp=i_(),
        g_prev_slope=f(), g_A=f(2e6), g_tdec=f(-10.0), g_avgmax=f(-1.0), g_state=i_(K.G_INC),
        g_loss_t=f(), g_Aloss=f(gmax),
        cc=cc, l4s=(cc == K.CC_PRAGUE).astype(np.int64), pr_alpha=f(), mark=f(), ev_mark=f(),
        cbr=cbr, g_min=f(gmin), g_max=f(gmax), late_s=f(glate),
    )
    St = namedtuple("St", list(d.keys()))
    return St(**d), names


def read_kpm(S, names, Ts):
    """Per-period counters a near-RT xApp would get over E2 (KPM)."""
    Kn = len(names)
    kpm = dict(
        prb=S.acc_prb_k / Ts,                  # average PRBs used per slice
        served=S.acc_srv_k / Ts,               # bit/s
        offered=S.acc_arr_k / Ts,              # bit/s arriving at gNB
        flow_served=S.acc_srv / Ts,
        flow_offered=S.acc_arr / Ts,
        flow_qdelay=S.acc_qd / Ts,
        flow_slice=S.fslice, flow_type=S.ftype,
        flow_active=(S.t_start <= S.t[0]) & (S.t[0] < S.t_stop),
        rprb=S.rprb.copy(),
    )
    eff = np.zeros(Kn)
    for k in range(Kn):
        m = (S.fslice == k) & kpm["flow_active"]
        eff[k] = S.rprb[m].mean() if m.any() else S.rprb.mean()
    kpm["eff"] = eff
    for a in ("acc_prb_k", "acc_srv_k", "acc_arr_k", "acc_srv", "acc_arr", "acc_qd"):
        getattr(S, a)[:] = 0.0
    return kpm


def qoe_monitor(S, names, sc, t0, t1, device="pc", hold_last=False):
    """Per-flow QoE estimate over [t0, t1] from logs. Stands in for a RAN-side
    QoE inference module (idealised: no inference error except added noise).
    A player that completed no segment in the window is scored as delivering no video (MOS 1).
    hold_last: score it at the quality of its last completed segment instead. Off by default; on
    held-out seeds it made EchoSlice v3 worse (diagnostics/round3/TUNING.md), so no slicer uses it."""
    N = S.ftype.shape[0]
    out = np.full(N, np.nan)
    W = t1 - t0
    for i in range(N):
        if S.t_start[i] > t0 or S.t_stop[i] < t1:
            continue
        ft = S.ftype[i]
        if ft == K.VIDEO:
            n = S.seg_idx[i]
            td = S.seg_tdone[i, :n]
            lv = S.seg_level[i, :n][(td >= t0) & (td < t1)]
            if hold_last and len(lv) == 0:
                prev = S.seg_level[i, :n][td < t1]
                if len(prev):
                    lv = prev[-1:]
            ns = S.n_stall[i]
            sw = S.st_wall[i, :ns]
            sd = S.st_dur[i, :ns]
            m = (sw >= t0) & (sw < t1)
            stime = sd[m].sum()
            if S.playing[i] == 0 and S.started[i] == 1 and S.stall_t0[i] >= t0:
                stime += t1 - S.stall_t0[i]
            out[i] = qoe.video_proxy(lv, stime, int(m.sum()), W, device)
    return out


class Monitor:
    """Keeps windowed per-flow throughput / delay so slicers can query QoE."""

    def __init__(self, S, names, sc, window, seed=0):
        self.S, self.names, self.sc, self.window = S, names, sc, window
        self.hist = []   # (t, flow_served, flow_offered, flow_qdelay, enc_rate, late_flag)
        self.delay = float(sc.kpm_delay_s)
        self.rng = np.random.default_rng(seed + 104729)

    def push(self, t, kpm):
        S = self.S
        late = (S.base_rtt * 0.5 + S.q * 8.0 / np.maximum(S.srate, 1e5)) > S.late_s
        self.hist.append((t, kpm["flow_served"].copy(), kpm["flow_offered"].copy(),
                          kpm["flow_qdelay"].copy(), S.enc_rate.copy(), late))
        while self.hist and self.hist[0][0] < t - 120.0:
            self.hist.pop(0)

    def flow_means(self, t, W):
        t = t - self.delay
        h = [x for x in self.hist if t - W < x[0] <= t + 1e-9]
        if not h:
            return None
        srv = np.mean([x[1] for x in h], axis=0)
        off = np.mean([x[2] for x in h], axis=0)
        qd = np.mean([x[3] for x in h], axis=0)
        enc = np.mean([x[4] for x in h], axis=0)
        late = np.mean([x[5] for x in h], axis=0)
        return srv, off, qd, enc, late

    def qoe(self, t, W, noise=0.0, rng=None, hold_last=False):
        """Per-flow MOS estimate over the last W seconds (as reported kpm_delay_s late).
        qoe_source='ideal': video from the player's segment levels and stalls (app-level logs);
        'kpm': every class inferred from served rate and queue delay only. In the open-loop twin
        (cbr flows) video is always inferred from the served rate."""
        S = self.S
        sc = self.sc
        te = t - self.delay
        fm = self.flow_means(t, W)
        twin = bool(sc.cbr)
        if sc.qoe_source == "kpm" or twin:
            mos = np.full(S.ftype.shape[0], np.nan)
        else:
            mos = qoe_monitor(S, self.names, sc, te - W, te, sc.device, hold_last=hold_last)
        if fm is None:
            return mos
        srv, off, qd, enc, late = fm
        v = S.ftype == K.VIDEO
        if sc.qoe_source == "kpm" or twin:
            mos[v] = qoe.video_rate_mos(srv[v], sc.device)
        g = S.ftype == K.GAME
        rate_g = srv[g] if (sc.qoe_source == "kpm" or twin) else enc[g]
        mos[g] = qoe.game_mos(rate_g, S.base_rtt[g] + 2 * qd[g], late[g], sc.rt_kind)
        b = S.ftype == K.BULK
        mos[b] = qoe.bulk_mos(srv[b])
        mos[(S.t_start > te - W) | (S.t_stop < te)] = np.nan
        if sc.qoe_noise > 0:
            mos = np.clip(mos + self.rng.normal(0, sc.qoe_noise, mos.shape), 1.0, 5.0)
        if noise > 0 and rng is not None:
            mos = mos + rng.normal(0, noise, mos.shape)
        return mos


def simulate(sc: Scenario, slicer, seed: int, trace=False, score=True, slice_trace_every=0.0):
    """Run one scenario under one slicer. score=False skips end-of-run QoE scoring (DRL training).
    slice_trace_every > 0 records per-slice share/offered/served/PRB every that many seconds."""
    import time as _time
    K.seed_kernel(seed)
    S, names = build_state(sc, seed)
    util, Vp, gp = bola_params(sc.device)
    ladder = qoe.LADDER_BPS.astype(np.float64)
    n_per = max(1, int(round(sc.Ts / sc.dt)))
    n_periods = int(round(sc.T / (n_per * sc.dt)))
    mon = Monitor(S, names, sc, window=10.0, seed=seed)
    slicer.reset(sc, names, S, mon, np.random.default_rng(seed + 7919))
    x = np.asarray(slicer.initial(), dtype=np.float64)
    xs, ts, prb_log, extra_log = [], [], [], []
    vid = S.ftype == K.VIDEO
    gam = S.ftype == K.GAME
    d_per = int(round(sc.kpm_delay_s / (n_per * sc.dt)))
    kq = []
    trng = np.random.default_rng(seed + 31337)
    dec_t, n_dec = 0.0, 0
    st_log, st_next = [], 0.0
    events = sorted([list(e) for e in sc.events], key=lambda e: e[0])
    abandoned = {}
    erng = np.random.default_rng(seed + 4242)
    fsize = None
    if sc.bulk_files_mb > 0:
        fsize = erng.exponential(sc.bulk_files_mb * 8e6, S.ftype.shape[0])
        fsize[S.ftype != K.BULK] = np.inf
        fdone = np.zeros(S.ftype.shape[0])
    for p in range(n_periods):
        while events and S.t[0] + 1e-9 >= events[0][0]:
            _, kind, val = events.pop(0)
            if kind == "ladder":
                ladder = qoe.LADDER_BPS.astype(np.float64) * float(val)
            elif kind == "sinr":
                S.sinr_mean[:] = S.sinr_mean + float(val)
            else:
                raise ValueError(kind)
        K.run_ticks(S, x, n_per, ladder, util, Vp, gp)
        t = S.t[0]
        kpm = read_kpm(S, names, n_per * sc.dt)
        if sc.abandon_stall_s > 0:
            st = (vid & (S.started == 1) & (S.playing == 0) & (S.t_start <= t) & (t < S.t_stop)
                  & (t - S.stall_t0 >= sc.abandon_stall_s))
            for i in np.where(st)[0]:
                abandoned[int(i)] = (float(t), float(S.t_stop[i]))
                S.t_stop[i] = t
        if fsize is not None:
            fdone += kpm["flow_served"] * n_per * sc.dt
            fin = (fdone >= fsize) & (S.t_start <= t) & (t < S.t_stop)
            S.t_stop[fin] = t
        mon.push(t, kpm)
        if slice_trace_every > 0 and t + 1e-9 >= st_next:
            st_next = t + slice_trace_every
            act = kpm["flow_active"]
            st_log.append([round(float(t), 3)] + [round(float(v), 4) for v in x] +
                          [round(float(v) / 1e6, 4) for v in kpm["offered"]] +
                          [round(float(v) / 1e6, 4) for v in kpm["served"]] +
                          [round(float(v), 3) for v in kpm["prb"]] +
                          [int(((S.fslice == k) & act).sum()) for k in range(len(names))])
        if d_per > 0:
            kq.append(kpm)
            if len(kq) <= d_per:
                continue                      # no report has reached the xApp yet
            kpm = kq.pop(0)
        if sc.kpm_drop > 0 and trng.random() < sc.kpm_drop:
            if trace or t >= sc.t_eval0:
                xs.append(x.copy()); ts.append(t); prb_log.append(kpm["prb"].copy())
            continue                          # report lost: shares stay as they are
        c0 = _time.perf_counter()
        if trace:
            extra_log.append((kpm["served"].copy(), kpm["offered"].copy(),
                              qoe.LADDER_KBPS[S.level[vid]].mean() / 1e3 if vid.any() else np.nan,
                              S.enc_rate[gam].mean() / 1e6 if gam.any() else np.nan,
                              (S.q[gam] * 8 / np.maximum(S.srate[gam], 1e5)).mean() * 1e3 if gam.any() else np.nan,
                              S.buf[vid].mean() if vid.any() else np.nan))
        x = np.asarray(slicer.decide(t, kpm), dtype=np.float64)
        dec_t += _time.perf_counter() - c0
        n_dec += 1
        if trace or t >= sc.t_eval0:
            xs.append(x.copy()); ts.append(t); prb_log.append(kpm["prb"].copy())
    if not score:
        return dict(names=names, decide_ms=1e3 * dec_t / max(n_dec, 1), slice_trace=st_log)
    res = metrics(S, names, sc, abandoned=abandoned)
    res["decide_ms"] = 1e3 * dec_t / max(n_dec, 1)
    if hasattr(slicer, "diag"):
        res["slicer_diag"] = slicer.diag()
    if sc.abandon_stall_s > 0:
        res["n_abandoned"] = len(abandoned)
    if fsize is not None:
        b = S.ftype == K.BULK
        res["files_done"] = int(((fdone >= fsize) & b).sum())
    if slice_trace_every > 0:
        res["slice_trace"] = st_log
    xs = np.array(xs); ts = np.array(ts)
    ev = ts >= sc.t_eval0
    res["share_mean"] = xs[ev].mean(axis=0).tolist()
    res["share_std"] = xs[ev].std(axis=0).tolist()
    cb = res["chunk_bounds"]
    res["chunk_share_mean"] = [xs[(ts > a) & (ts <= b)].mean(axis=0).tolist() if ((ts > a) & (ts <= b)).any() else None
                               for a, b in cb]
    res["names"] = names
    if trace:
        res["trace_t"] = ts
        res["trace_x"] = xs
        res["trace_prb"] = np.array(prb_log)
        res["trace_served"] = np.array([e[0] for e in extra_log])
        res["trace_offered"] = np.array([e[1] for e in extra_log])
        res["trace_video_level_mbps"] = np.array([e[2] for e in extra_log])
        res["trace_game_rate_mbps"] = np.array([e[3] for e in extra_log])
        res["trace_game_qdelay_ms"] = np.array([e[4] for e in extra_log])
        res["trace_video_buf"] = np.array([e[5] for e in extra_log])
        res["state"] = S
    return res


def _video_piece(S, i, a, b, end, sc, p1203):
    """P.1203 (or proxy) for flow i over wall-clock [a, b); `end` is when the
    session stopped or the run ended (for a stall still running at the end)."""
    n = S.seg_idx[i]
    td = S.seg_tdone[i, :n]
    sel = (td >= a) & (td < b)
    lv = S.seg_level[i, :n][sel]
    ns = S.n_stall[i]
    sw, sd, sm = S.st_wall[i, :ns], S.st_dur[i, :ns], S.st_media[i, :ns]
    m = (sw >= a) & (sw < b)
    first = int(np.argmax(sel)) if sel.any() else 0
    m0 = first * sc.seg_dur
    stalls = [(max(0.0, sm[j] - m0), min(sd[j], b - sw[j])) for j in np.where(m)[0]]
    if S.playing[i] == 0 and S.started[i] == 1 and a <= S.stall_t0[i] < b:
        stalls.append((max(0.0, S.stall_media[i] - m0), min(b, end) - S.stall_t0[i]))
    stime = float(sum(d for _, d in stalls))
    W = b - a
    if p1203:
        mos = qoe.p1203_session(list(lv), sc.seg_dur, stalls, sc.device)
    else:
        mos = qoe.video_proxy(lv, stime, len(stalls), W, sc.device)
    sw_pm = (np.diff(lv) != 0).sum() / (W / 60.0) if len(lv) > 1 else 0.0
    br = qoe.LADDER_KBPS[lv].mean() / 1e3 if len(lv) else 0.0
    return mos, stime / W, sw_pm, br


def metrics(S, names, sc, p1203=True, abandoned=None):
    """Per-flow and per-slice QoE over the evaluation window, scored in
    windows of sc.chunk_s seconds (each flow only over its active time)."""
    t0, t1 = sc.t_eval0, sc.T
    nC = S.evc_time.shape[1]
    bounds = [(t0 + c * sc.chunk_s, min(t1, t0 + (c + 1) * sc.chunk_s)) for c in range(nC)]
    N = S.ftype.shape[0]
    cm = np.full((N, nC), np.nan)       # per-flow, per-window MOS
    cw = np.zeros((N, nC))              # weight = active seconds in the window
    ex = {k: np.full((N, nC), np.nan) for k in ("stall_ratio", "switches_pm", "bitrate_mbps", "game_rate",
                                                 "game_late", "game_rtt_ms", "bulk_mbps")}
    for i in range(N):
        ft = S.ftype[i]
        end = min(t1, S.t_stop[i])
        for c, (a, b) in enumerate(bounds):
            aa, bb = max(a, S.t_start[i]), min(b, end)
            if bb - aa < sc.min_eval_s:
                continue
            cw[i, c] = bb - aa
            if ft == K.VIDEO:
                mos, sr, swpm, br = _video_piece(S, i, aa, bb, end, sc, p1203)
                cm[i, c] = mos
                ex["stall_ratio"][i, c], ex["switches_pm"][i, c], ex["bitrate_mbps"][i, c] = sr, swpm, br
            else:
                et = max(S.evc_time[i, c], 1e-9)
                if ft == K.GAME:
                    rate = S.evc_rate[i, c] / et
                    qd = S.evc_qd[i, c] / et
                    late = S.evc_late[i, c] / et
                    rtt = S.base_rtt[i] + 2 * qd
                    cm[i, c] = float(qoe.game_mos(rate, rtt, late, sc.rt_kind))
                    ex["game_rate"][i, c], ex["game_late"][i, c], ex["game_rtt_ms"][i, c] = rate / 1e6, late, rtt * 1e3
                else:
                    tp = S.evc_srv[i, c] / et
                    cm[i, c] = float(qoe.bulk_mos(tp))
                    ex["bulk_mbps"][i, c] = tp / 1e6
    for i, (ta, tplan) in (abandoned or {}).items():
        # a user who left after a long stall is scored at MOS 1 for the rest of the session it planned
        for c, (a, b) in enumerate(bounds):
            extra = max(0.0, min(b, tplan, t1) - max(a, ta))
            if extra <= 0:
                continue
            if cw[i, c] > 0 and np.isfinite(cm[i, c]):
                cm[i, c] = (cm[i, c] * cw[i, c] + 1.0 * extra) / (cw[i, c] + extra)
            else:
                cm[i, c] = 1.0
            cw[i, c] += extra
    wsum = cw.sum(axis=1)
    ok = wsum > 0
    mos = np.full(N, np.nan)
    mos[ok] = np.nansum(np.nan_to_num(cm[ok]) * cw[ok], axis=1) / wsum[ok]
    per_slice = {}
    for k, nm in enumerate(names):
        m = (S.fslice == k) & ok
        per_slice[nm] = float(np.mean(mos[m])) if m.any() else float("nan")
    chunk_slice = []
    chunk_user = []
    for c in range(nC):
        d = {}
        for k, nm in enumerate(names):
            m = (S.fslice == k) & (cw[:, c] > 0)
            d[nm] = float(np.mean(cm[m, c])) if m.any() else None
        chunk_slice.append(d)
        m = cw[:, c] > 0
        chunk_user.append(float(np.mean(cm[m, c])) if m.any() else None)
    vals = [v for v in per_slice.values() if np.isfinite(v)]
    res = dict(mos_user=float(np.mean(mos[ok])) if ok.any() else float("nan"), mos_slice=per_slice,
               mos_slice_avg=float(np.mean(vals)) if vals else float("nan"), flow_mos=mos,
               chunk_bounds=bounds, chunk_slice_mos=chunk_slice, chunk_mos_user=chunk_user,
               n_flows_scored={nm: int(((S.fslice == k) & ok).sum()) for k, nm in enumerate(names)},
               chunk_flow_mos=[[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in cm],
               flow_slice=S.fslice.tolist())
    for kk, v in ex.items():
        w = np.where(np.isfinite(v), cw, 0.0)
        res[kk] = float(np.nansum(np.nan_to_num(v) * w) / w.sum()) if w.sum() > 0 else float("nan")
    res["cell_tput_mbps"] = float(S.ev_srv.sum() / (t1 - t0) / 1e6)
    lf = (S.l4s == 1) & (S.ev_time > 0)
    if lf.any():
        res["l4s_qdelay_ms"] = float((S.ev_qd[lf] / S.ev_time[lf]).mean() * 1e3)
        res["l4s_mark_frac"] = float((S.ev_mark[lf] / S.ev_time[lf]).mean())
    tq = S.ev_time > 0
    res["flow_qdelay_ms"] = (np.where(tq, S.ev_qd / np.maximum(S.ev_time, 1e-9), np.nan) * 1e3).tolist()
    res["flow_type"] = S.ftype.tolist()
    res["flow_tput_mbps"] = (S.ev_srv / np.maximum(S.ev_time, 1e-9) / 1e6).tolist()
    return res
