"""Slicer xApps. Each one sees only near-RT KPMs (and, for QoE-aware ones,
an idealised QoE monitor) and returns per-slice PRB shares every period.

Shares act as O-RAN rRMPolicyMinRatio: prioritised but shareable. Unused
and unassigned PRBs go to a cell-wide PF pool unless Scenario.strict.
"""
import numpy as np
from . import qoe
from . import kernel as Kk

XMIN = 0.05
XMAX = 0.95
# per-slice QoE targets used by the SLA term and the SLA metric (MOS)
SLA_TARGET = {"video": 4.0, "game": 4.0, "bulk": 3.0}


def project(x, xmin=XMIN, xmax=XMAX, total=1.0):
    """Euclidean projection onto {sum x = total, xmin <= x <= xmax}."""
    x = np.asarray(x, dtype=float)
    lo, hi = x.min() - xmax - 1.0, x.max() - xmin + 1.0
    for _ in range(60):
        mu = 0.5 * (lo + hi)
        s = np.clip(x - mu, xmin, xmax).sum()
        if s > total:
            lo = mu
        else:
            hi = mu
    return np.clip(x - 0.5 * (lo + hi), xmin, xmax)


class Base:
    name = "base"

    def reset(self, sc, names, S, mon, rng):
        self.sc, self.names, self.S, self.mon, self.rng = sc, names, S, mon, rng
        self.K = len(names)
        self.x = np.full(self.K, 1.0 / self.K)

    def initial(self):
        return self.x

    def decide(self, t, kpm):
        return self.x


class Static(Base):
    def __init__(self, x=None):
        self.x0 = x
        self.name = "static" if x is None else "static" + "-".join(f"{v:.2f}" for v in x)

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        if self.x0 is not None:
            self.x = np.asarray(self.x0, dtype=float)


class Shared(Base):
    """No slicing: every PRB goes through the cell-wide PF pool."""
    name = "shared"

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.x = np.zeros(self.K)


class UsageProp(Base):
    """Share proportional to measured PRB usage (EWMA)."""
    name = "usage-prop"

    def __init__(self, alpha=0.5):
        self.alpha = alpha

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.u = None

    def decide(self, t, kpm):
        u = kpm["prb"] + 1e-6
        self.u = u if self.u is None else (1 - self.alpha) * self.u + self.alpha * u
        self.x = project(self.u / self.u.sum())
        return self.x


class ForecastHeadroom(Base):
    """DeepCog-style provisioning: each priority slice gets its forecast
    offered load plus headroom h; the best-effort (bulk) slice gets the rest.
    The forecaster is an EWMA here (an LSTM twin in the full paper)."""

    def __init__(self, h=0.2, alpha=0.3):
        self.h, self.alpha = h, alpha
        self.name = f"forecast+{h * 100:g}%"

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.f = None
        self.be = names.index("bulk") if "bulk" in names else None

    def decide(self, t, kpm):
        o = kpm["offered"]
        self.f = o if self.f is None else (1 - self.alpha) * self.f + self.alpha * o
        cap = kpm["eff"] * self.sc.B
        need = self.f * (1 + self.h) / cap
        x = need.copy()
        if self.be is not None:
            pri = [k for k in range(self.K) if k != self.be]
            s = x[pri].sum()
            if s > 1 - XMIN:
                x[pri] *= (1 - XMIN) / s
            x[self.be] = 1 - x[pri].sum()
        self.x = project(x)
        return self.x


class OpenLoopQoE(Base):
    """QoE-aware optimiser that treats measured demand as exogenous: it
    maximises sum of per-user MOS assuming each flow wants d_i(1+h) and gains
    nothing above it (the standard 'forecast demand, then optimise' view)."""

    def __init__(self, h=0.1, every=1.0, W=10.0, lam=0.0):
        self.h, self.every, self.W, self.lam = h, every, W, lam
        self.name = f"ol-qoe+{int(h * 100)}%" + (f"-sla{lam:g}" if lam > 0 else "")

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.t_next = 0.0
        step = 0.01 if self.K <= 2 else 0.025
        g = np.arange(XMIN, XMAX + 1e-9, step)
        if self.K == 1:
            self.grid = np.ones((1, 1))
        elif self.K == 2:
            self.grid = np.stack([g, 1 - g], 1)
        else:
            pts = [(a, b, 1 - a - b) for a in g for b in g if XMIN - 1e-9 <= 1 - a - b <= XMAX + 1e-9]
            self.grid = np.array(pts)

    def _slice_curve(self, caps_d, ftypes, rtts, cgrid, tau=None):
        """Sum of MOS in a slice as a function of slice capacity (water-filling).
        With tau, also returns the summed shortfall below the slice target, sum_i max(0, tau - m_i)."""
        n = len(caps_d)
        if n == 0:
            return (np.zeros(len(cgrid)), np.zeros(len(cgrid))) if tau is not None else np.zeros(len(cgrid))
        order = np.argsort(caps_d)
        d = caps_d[order]
        ft = ftypes[order]
        rt = rtts[order]
        # water level lambda(c): sum_j min(d_j, lambda) = c
        cs = np.concatenate([[0.0], np.cumsum(d)])
        Cj = cs[:-1] + (n - np.arange(n)) * d          # capacity at which lambda reaches d_j
        j = np.searchsorted(Cj, cgrid, side="right")
        j = np.minimum(j, n)
        lam = np.where(j < n, (cgrid - cs[j]) / np.maximum(n - j, 1), np.inf)
        r = np.minimum(d[None, :], lam[:, None])        # (grid, n)
        m = np.zeros(len(cgrid))
        dsum = np.zeros(len(cgrid))
        for typ in (Kk.VIDEO, Kk.GAME, Kk.BULK):
            sel = ft == typ
            if not sel.any():
                continue
            rs = r[:, sel]
            if typ == Kk.VIDEO:
                mm = qoe.video_rate_mos(rs, self.sc.device)
            elif typ == Kk.GAME:
                mm = qoe.game_mos(rs, rt[sel][None, :], 0.0, self.sc.rt_kind)
            else:
                mm = qoe.bulk_mos(rs)
            m += mm.sum(1)
            if tau is not None:
                dsum += np.maximum(0.0, tau - mm).sum(1)
        return (m, dsum) if tau is not None else m

    def decide(self, t, kpm):
        if t < self.t_next:
            return self.x
        self.t_next = t + self.every
        fm = self.mon.flow_means(t, self.W)
        if fm is None:
            return self.x
        srv, off, qd, enc, late = fm
        act = kpm["flow_active"]
        cap_tot = kpm["eff"] * self.sc.B
        cg = np.linspace(0, 1, 101)
        curves = []
        n_tot = max(int(act.sum()), 1)
        for k in range(self.K):
            m = (kpm["flow_slice"] == k) & act
            dem = off[m] * (1 + self.h)
            if self.lam > 0:
                # same objective as EchoSlice: mean MOS - lam * sum_k mean shortfall of slice k (scaled by N)
                ms, ds = self._slice_curve(dem, kpm["flow_type"][m], self.S.base_rtt[m], cg * cap_tot[k],
                                           tau=SLA_TARGET.get(self.names[k], 4.0))
                curves.append(ms - self.lam * n_tot * ds / max(int(m.sum()), 1))
            else:
                curves.append(self._slice_curve(dem, kpm["flow_type"][m], self.S.base_rtt[m], cg * cap_tot[k]))
        val = np.zeros(len(self.grid))
        for k in range(self.K):
            val += np.interp(self.grid[:, k], cg, curves[k])
        # tie-break toward demand-proportional shares
        dk = np.array([off[(kpm["flow_slice"] == k) & act].sum() / cap_tot[k] for k in range(self.K)])
        prop = dk / max(dk.sum(), 1e-9)
        val -= 1e-3 * ((self.grid - prop) ** 2).sum(1)
        self.x = project(self.grid[np.argmax(val)])
        return self.x


class EchoSliceLite(Base):
    """Reaction-aware, model-free: two-point (SPSA) probes of the slice shares,
    each held longer than the apps' adaptation time, scored by the closed-loop
    QoE measured after the apps have reacted. No app model, no app hints."""

    def __init__(self, delta=0.05, hold=12.0, settle=6.0, step=0.6, max_step=0.05, noise=0.02):
        self.delta, self.hold, self.settle = delta, hold, settle
        self.step, self.max_step, self.noise = step, max_step, noise
        self.name = "echoslice-lite"

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.c = np.full(self.K, 1.0 / self.K)
        self.phase = 0
        self.t_phase = 0.0
        self.dir = self._newdir()
        self.Up = None
        self.x = project(self.c + self.delta * self.dir)
        self.hist = []

    def _newdir(self):
        if self.K == 2:
            return np.array([1.0, -1.0])
        while True:
            s = self.rng.choice([-1.0, 1.0], self.K)
            s = s - s.mean()
            if np.abs(s).sum() > 0:
                return s / np.abs(s).max()

    def _utility(self, t):
        W = self.hold - self.settle
        m = self.mon.qoe(t, W)
        u = np.nanmean(m) if np.isfinite(m).any() else 0.0
        return u + self.rng.normal(0, self.noise)

    def decide(self, t, kpm):
        if t - self.t_phase < self.hold:
            return self.x
        U = self._utility(t)
        self.t_phase = t
        if self.phase == 0:
            self.Up = U
            self.phase = 1
            self.x = project(self.c - self.delta * self.dir)
        else:
            g = (self.Up - U) / (2 * self.delta) * self.dir
            stp = np.clip(self.step * g * self.delta, -self.max_step, self.max_step)
            self.c = project(self.c + stp)
            self.hist.append((t, self.c.copy(), self.Up, U))
            self.dir = self._newdir()
            self.phase = 0
            self.x = project(self.c + self.delta * self.dir)
        return self.x




class EchoSlice(EchoSliceLite):
    """EchoSlice (v2): EchoSlice-lite plus a split between exogenous and endogenous demand.

    The number of active sessions per slice (a standard per-slice KPM) does not depend
    on the share, so it is used directly. When it changes by at least max(2, 25%), the
    centre jumps by the count ratio, x_k <- x_k (n_new / n_old)^alpha. A slice that gained
    sessions only gets more share if its measured QoE is below `mos_ok` (a slice whose QoE
    is already saturated can absorb the new sessions). After a jump the probing runs with a
    larger step and probe for `boost_cycles` probe pairs. The rate each session sends does
    depend on the share, so it is only learned through probes held longer than the apps'
    reaction time, exactly as in EchoSlice-lite. With a steady load the two are identical.
    """

    def __init__(self, alpha=1.0, mos_ok=4.4, boost_cycles=4, boost_step=3.0, boost_delta=1.4,
                 t_warm=30.0, **kw):
        super().__init__(**kw)
        self.alpha, self.mos_ok, self.boost_cycles = alpha, mos_ok, boost_cycles
        self.boost_step, self.boost_delta, self.t_warm = boost_step, boost_delta, t_warm
        self.name = "echoslice"

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.n_ref = None
        self.boost = 0
        self.d_pair = self.delta
        self.jumps = []

    def _slice_mos(self, t, W=10.0):
        m = self.mon.qoe(t, W)
        out = np.full(self.K, np.nan)
        for k in range(self.K):
            sel = (self.S.fslice == k) & np.isfinite(m)
            if sel.any():
                out[k] = m[sel].mean()
        return out

    def decide(self, t, kpm):
        a = kpm["flow_active"]
        n_act = np.array([float(((kpm["flow_slice"] == k) & a).sum()) for k in range(self.K)])
        if self.n_ref is None or t < self.t_warm:
            self.n_ref = n_act
        elif np.any(np.abs(n_act - self.n_ref) >= np.maximum(2.0, 0.25 * self.n_ref)):
            ratio = np.maximum(n_act, 0.5) / np.maximum(self.n_ref, 0.5)
            mos = self._slice_mos(t)
            for k in range(self.K):
                if ratio[k] > 1 and np.isfinite(mos[k]) and mos[k] >= self.mos_ok:
                    ratio[k] = 1.0                       # saturated slice: no extra share needed
            self.n_ref = n_act
            if np.any(np.abs(ratio - 1.0) > 1e-9):
                w = self.c * ratio ** self.alpha
                self.c = project(w / w.sum())
                self.boost = self.boost_cycles
                self.jumps.append((t, ratio.tolist(), self.c.copy()))
                # restart the probe pair around the new centre
                self.d_pair = self.delta * self.boost_delta
                self.dir = self._newdir()
                self.phase = 0
                self.t_phase = t
                self.x = project(self.c + self.d_pair * self.dir)
                return self.x
        if t - self.t_phase < self.hold:
            return self.x
        U = self._utility(t)
        self.t_phase = t
        if self.phase == 0:
            self.Up = U
            self.phase = 1
            self.x = project(self.c - self.d_pair * self.dir)
        else:
            g = (self.Up - U) / (2 * self.d_pair) * self.dir
            k = self.boost_step if self.boost else 1.0
            stp = np.clip(self.step * k * g * self.d_pair, -self.max_step * k, self.max_step * k)
            self.c = project(self.c + stp)
            self.hist.append((t, self.c.copy(), self.Up, U))
            self.boost = max(0, self.boost - 1)
            self.d_pair = self.delta * (self.boost_delta if self.boost else 1.0)
            self.dir = self._newdir()
            self.phase = 0
            self.x = project(self.c + self.d_pair * self.dir)
        return self.x


# Per-session reference rates from the slice template (non-cooperative prior), bit/s: a 1080p video rung
# and a typical cloud-gaming stream. Calibrated once on held-out seeds 101-104 (diagnostics/round3/tune.py);
# the XR value is deliberately left as an uncalibrated template guess.
REF_RATE = {"video": 6.0e6, "game": 12.0e6, "xr": 30.0e6}
# What a cooperative app would report: the rate at which its QoE saturates (video: top 1080p rung over the
# ABR safety factor; gaming/XR: coding impairment below ~5 R points), and its adaptation time (s).
HINT_RATE = {"video": 6.5e6, "game": 15.0e6, "xr": 50.0e6}
HINT_TAU = {"video": None, "game": 2.0, "xr": 2.0, "bulk": 1.0}   # video: its segment duration


def sla_utility(m, fslice, names, lam):
    """Mean user MOS minus lam * sum over slices of the mean shortfall below the slice target."""
    ok = np.isfinite(m)
    if not ok.any():
        return 0.0, np.zeros(len(names))
    u = float(m[ok].mean())
    dfc = np.zeros(len(names))
    for k, nm in enumerate(names):
        sel = (fslice == k) & ok
        if sel.any():
            dfc[k] = float(np.maximum(0.0, SLA_TARGET.get(nm, 4.0) - m[sel]).mean())
    return u - lam * dfc.sum(), dfc


class EchoSlice3(Base):
    """EchoSlice (v3): reaction-aware slicing that keeps exogenous and endogenous demand apart.

    Exogenous part (read, never probed): the number of active sessions per slice, a standard per-slice
    KPM that does not depend on the share. The split is computed from it as
        x_k = n_k * r_k * exp(theta_k) / C_k   for rate-bounded slices (video, real-time),
    with C_k the slice's cell capacity at its UEs' current spectral efficiency; the best-effort (bulk)
    slice gets the rest. r_k is a per-session reference rate from the slice template (or an app hint).
    It ignores measured demand, so it cannot be dragged down by polite apps or up by greedy ones.
    Endogenous part (learned closed loop): theta, a log-multiplier of the per-session rates, learned by
    SPSA probes held longer than the apps' adaptation time (hold 12 s, scored on the last 6 s) on the
    measured closed-loop utility, mean user MOS - lam * sum over slices of the mean shortfall below the
    slice target. Gains follow Spall's sequences and restart when a rate-bounded slice's session count
    changes by >= max(2, 25%); theta carries over, because per-session rates do not depend on counts.
    Bulk session changes move nothing (more TCP sessions do not mean more demand per share).
    Other optimisers ('pair' sign descent, SPSA in share space) are kept for the ablations.
    """

    def __init__(self, lam=0.0, hold=12.0, settle=6.0, step0=0.08, step_min=0.01, step_max=0.2,
                 grow=1.6, shrink=0.5, delta_min=0.03, delta_max=0.08, noise=0.02, prior=True,
                 count_moves=True, optimizer="spsa", adapt_step=True, hint=False, liar=None,
                 liar_factor=3.0, rate_scale=1.0, freeze_after=None, name=None, rates=None,
                 t_warm=30.0, a0=0.6, A=5.0, c0=0.15, gain_decay=True, max_step=0.3, space="rate",
                 theta_max=1.5, hold_last=False, rand_order=False, count_src="session", linger=10.0,
                 gate=False, gate_m=4, gate_tol=0.04, gate_delta=0.12, gate_win=30.0, gate_every=6.0):
        self.lam, self.hold, self.settle = lam, hold, settle
        # where the session counts come from: 'session' = true session counter (default); 'activity' = UEs with
        # data in the last slicer period (an activity KPM, falls while a player idles); 'linger' = a UE stays
        # counted for `linger` s after its last data (a persistent estimator, like an RRC inactivity timer)
        self.count_src, self.linger = count_src, linger
        # gated trials: stop the trials once the search has settled (gate_m SPSA steps in a row with every
        # component below gate_tol), keep the learned rates, and reopen the trials only when the measured utility
        # over gate_win s falls gate_delta below its reference twice in a row (checked every gate_every s)
        self.gate, self.gate_m, self.gate_tol = gate, gate_m, gate_tol
        self.gate_delta, self.gate_win, self.gate_every = gate_delta, gate_win, gate_every
        self.rand_order = rand_order          # draw which of the +/- trials comes first (carry-over test)
        self.step0, self.step_min, self.step_max = step0, step_min, step_max
        self.grow, self.shrink, self.delta_min, self.delta_max = grow, shrink, delta_min, delta_max
        self.noise, self.use_prior, self.count_moves = noise, prior, count_moves
        self.optimizer, self.adapt_step = optimizer, adapt_step
        self.hint, self.liar, self.liar_factor, self.rate_scale = hint, liar, liar_factor, rate_scale
        self.freeze_after = freeze_after
        self.rates_override = rates
        self.t_warm, self.a0, self.A, self.c0 = t_warm, a0, A, c0
        self.gain_decay, self.max_step_spsa = gain_decay, max_step
        self.space, self.theta_max = space, theta_max
        self.hold_last = hold_last
        self.name = name or (f"echoslice3-l{lam:g}" if lam > 0 else "echoslice3")

    # ------------------------------------------------------------ set-up
    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.be = names.index("bulk") if "bulk" in names else None
        self.bounded = np.array([k != self.be for k in range(self.K)])
        rates, taus = [], []
        for nm in names:
            cls = sc.rt_kind if nm == "game" else nm
            if nm == "bulk":
                rates.append(0.0)
                taus.append(HINT_TAU["bulk"])
                continue
            table = dict(HINT_RATE if self.hint else REF_RATE)
            if self.rates_override:
                table.update(self.rates_override)
            r = table[cls] * self.rate_scale
            if self.hint and self.liar == nm:
                r *= self.liar_factor
            rates.append(r)
            taus.append(sc.seg_dur if nm == "video" else HINT_TAU[cls])
        self.r = np.array(rates)
        self.tau = np.array(taus)
        self.pairs = [(i, j) for i in range(self.K) for j in range(i + 1, self.K)]
        self.step = np.full(len(self.pairs), self.step0)
        self.prev = np.zeros(len(self.pairs))
        self.pi = 0
        self.phase = 0
        self.t_phase = 0.0
        self.D = np.zeros(self.K)
        self.p0 = None
        self.n_ref = None
        self.c = np.full(self.K, 1.0 / self.K)
        self.hist = []
        self.moves = []
        self.spsa_dir = None
        self.k_upd = 0
        self.theta = np.zeros(self.K)          # log-multiplier of the per-session reference rates (space='rate')
        self.n_now = None
        self.kpm_now = None
        self.first = 1.0
        self._last_busy = None
        self.frozen, self.small, self.Uref, self.t_frozen, self.bad, self.t_gchk = False, 0, None, 0.0, 0, 0.0
        self.t_frozen_total, self.n_reopen, self.t_last = 0.0, 0, 0.0
        self.cnt_err, self.n_moves = [], 0

    def _prior(self, kpm, n, theta=None):
        if not self.use_prior:
            return np.full(self.K, 1.0 / self.K)
        cap = np.maximum(kpm["eff"] * self.sc.B, 1.0)
        r = self.r if theta is None else self.r * np.exp(theta)
        x = n * r / cap
        if self.be is not None:
            pri = self.bounded
            s = x[pri].sum()
            if s > 1 - XMIN:
                x[pri] *= (1 - XMIN) / s
            x[self.be] = 1 - x[pri].sum()
        else:
            x = x / max(x.sum(), 1e-9)
        return project(x)

    def _set_centre(self):
        self.c = project(self.p0 + self.D)
        self.D = self.c - self.p0

    def _hold_for(self, pair):
        if not self.hint:
            return self.hold, self.settle
        h = max(4.0, 2.0 * max(self.tau[pair[0]], self.tau[pair[1]]))
        return h, h / 2.0

    def _utility(self, t, W):
        m = self.mon.qoe(t, W, hold_last=self.hold_last)
        u, _ = sla_utility(m, self.S.fslice, self.names, self.lam)
        return u + self.rng.normal(0, self.noise)

    def _ck(self):
        return self.c0 / (self.k_upd + 1) ** 0.101 if self.gain_decay else self.c0

    def _ak(self):
        return self.a0 / (self.k_upd + 1 + self.A) ** 0.602 if self.gain_decay else self.a0 / (1 + self.A) ** 0.602

    def _probe(self, sign):
        if self.space == "rate":
            th = np.clip(self.theta + sign * self._ck() * self.spsa_dir * self.bounded, -self.theta_max, self.theta_max)
            return self._prior(self.kpm_now, self.n_now, th)
        if self.optimizer == "spsa":
            d = self.spsa_dir * self._ck()
        else:
            i, j = self.pairs[self.pi]
            dl = float(np.clip(0.5 * self.step[self.pi], self.delta_min, self.delta_max))
            d = np.zeros(self.K)
            d[i], d[j] = dl, -dl
        return project(self.c + sign * d)

    def _new_spsa_dir(self):
        if self.space == "rate":
            return self.rng.choice([-1.0, 1.0], self.K)
        if self.K == 2:
            return np.array([1.0, -1.0])
        while True:
            s = self.rng.choice([-1.0, 1.0], self.K)
            s = s - s.mean()
            if np.abs(s).sum() > 0:
                return s / np.abs(s).max()

    def _restart(self, t):
        self.phase = 0
        self.t_phase = t
        if self.optimizer == "spsa" or self.space == "rate":
            self.spsa_dir = self._new_spsa_dir()
        self.first = (1.0 if self.rng.random() < 0.5 else -1.0) if self.rand_order else 1.0
        self.x = self._probe(self.first)

    # ------------------------------------------------------------ loop
    def _count_mask(self, t, kpm):
        if self.count_src == "session":
            return kpm["flow_active"]
        busy = (kpm["flow_offered"] > 0) | (kpm["flow_served"] > 0)
        if self.count_src == "activity":
            return busy
        if getattr(self, "_last_busy", None) is None or len(self._last_busy) != len(busy):
            self._last_busy = np.full(len(busy), -1e9)
        self._last_busy[busy] = t
        return (t - self._last_busy) <= self.linger

    def diag(self):
        e = np.array(self.cnt_err) if self.cnt_err else np.zeros((0, self.K))
        out = dict(n_moves=int(self.n_moves), frozen_frac=float(self.t_frozen_total / max(self.t_last, 1e-9)),
                   n_reopen=int(self.n_reopen))
        if len(e):
            out["count_rel_err_mean"] = np.nanmean(e, axis=0).round(4).tolist()
            out["count_rel_err_abs"] = np.nanmean(np.abs(e), axis=0).round(4).tolist()
            out["count_rel_err_p10"] = np.nanpercentile(e, 10, axis=0).round(4).tolist()
        return out

    def _gated(self, t):
        """Frozen state of the gated variant: hold the learned shares and watch the measured utility."""
        self.x = self.c.copy()
        if t - self.t_gchk < self.gate_every or t - self.t_frozen < self.gate_win:
            return self.x
        self.t_gchk = t
        U = self._utility(t, self.gate_win)
        if self.Uref is None:
            self.Uref = U
            return self.x
        self.bad = self.bad + 1 if U < self.Uref - self.gate_delta else 0
        if self.bad >= 2:                      # quality fell: reopen the trials around the current rates
            self.frozen, self.small, self.bad, self.Uref = False, 0, 0, None
            self.n_reopen += 1
            self.k_upd = 0
            self._restart(t)
        return self.x

    def decide(self, t, kpm):
        if self.K < 2:
            return self.x
        if self.frozen:
            self.t_frozen_total += t - self.t_last
        self.t_last = t
        a = self._count_mask(t, kpm)
        n = np.array([float(((kpm["flow_slice"] == k) & a).sum()) for k in range(self.K)])
        if self.count_src != "session":
            tr = kpm["flow_active"]
            nt = np.array([float(((kpm["flow_slice"] == k) & tr).sum()) for k in range(self.K)])
            self.cnt_err.append(np.where(nt > 0, (n - nt) / np.maximum(nt, 1.0), np.nan))
        moves_on = self.count_moves or t < self.t_warm          # 'no moves' ablation: counts frozen after warm-up
        if self.space == "rate" and (self.kpm_now is None or self.p0 is None or
                                     (moves_on and np.any((np.abs(n - self.n_ref) >= np.maximum(2.0, 0.25 * self.n_ref))
                                                          & self.bounded))):
            self.kpm_now, self.n_now = kpm, n          # capacity and counts the rate-space prior is evaluated at
        if self.p0 is None:
            self.p0 = self._prior(kpm, n)
            self.n_ref = n
            self._set_centre()
            self._restart(t)
            return self.x
        if moves_on and np.any((np.abs(n - self.n_ref) >= np.maximum(2.0, 0.25 * self.n_ref)) & self.bounded):
            p1 = self._prior(kpm, n)
            self.p0 = p1
            self.n_ref = n
            if self.space == "rate":
                self.c = self._prior(kpm, n, self.theta)     # learned per-session rates carry over
                self.D = self.c - self.p0
            else:
                self._set_centre()
            self.step[:] = self.step0          # re-open the search after a load change
            self.prev[:] = 0.0
            self.k_upd = 0
            self.moves.append((float(t), p1.round(3).tolist()))
            self.n_moves += 1
            if self.gate and self.frozen:      # gated and settled: follow the counts, keep the rates, no trials
                self.x = self.c.copy()
                self.t_frozen, self.Uref, self.bad = t, None, 0
                return self.x
            self._restart(t)
            return self.x
        if (self.freeze_after is not None and t >= self.freeze_after) or t < self.t_warm:
            self.x = self.c.copy()
            self.t_phase = t
            return self.x
        if self.gate and self.frozen:
            return self._gated(t)
        hold, settle = self._hold_for(self.pairs[self.pi])
        if t - self.t_phase < hold:
            return self.x
        U = self._utility(t, hold - settle)
        self.t_phase = t
        if self.phase == 0:
            self.Up = U                       # utility of the first trial of the pair
            self.phase = 1
            self.x = self._probe(-self.first)
            return self.x
        dU = self.first * (self.Up - U)       # = U(+) - U(-) whichever trial came first
        if self.space == "rate":
            g = dU / (2 * self._ck()) * self.spsa_dir * self.bounded
            stp = np.clip(self._ak() * g, -self.max_step_spsa, self.max_step_spsa)
            self.theta = np.clip(self.theta + stp, -self.theta_max, self.theta_max)
            self.k_upd += 1
            self.c = self._prior(self.kpm_now, self.n_now, self.theta)
            self.D = self.c - self.p0
            self.hist.append((float(t), self.c.round(4).tolist(), float(self.Up), float(U)))
            if self.gate:
                self.small = self.small + 1 if np.max(np.abs(stp)) < self.gate_tol else 0
                if self.small >= self.gate_m:
                    self.frozen, self.t_frozen, self.t_gchk, self.Uref, self.bad = True, t, t, None, 0
                    self.x = self.c.copy()
                    return self.x
            self._restart(t)
            return self.x
        if self.optimizer == "spsa":
            # SPSA with Spall's gain sequences a_k = a0/(k+1+A)^0.602, c_k = c0/(k+1)^0.101 (restarted
            # after each load move); the step is capped at max_step per update
            g = dU / (2 * self._ck()) * self.spsa_dir
            stp = np.clip(self._ak() * g, -self.max_step_spsa, self.max_step_spsa)
            self.D = self.D + stp
            self.k_upd += 1
        else:
            i, j = self.pairs[self.pi]
            sgn = float(np.sign(dU))
            if self.adapt_step:
                if sgn != 0 and sgn == self.prev[self.pi]:
                    self.step[self.pi] = min(self.step_max, self.step[self.pi] * self.grow)
                elif sgn != 0 and sgn == -self.prev[self.pi]:
                    self.step[self.pi] = max(self.step_min, self.step[self.pi] * self.shrink)
            mv = np.zeros(self.K)
            mv[i], mv[j] = self.step[self.pi], -self.step[self.pi]
            self.D = self.D + sgn * mv
            if sgn != 0:
                self.prev[self.pi] = sgn
            self.pi = (self.pi + 1) % len(self.pairs)
        self._set_centre()
        self.hist.append((float(t), self.c.round(4).tolist(), float(self.Up), float(U)))
        self._restart(t)
        return self.x


class QoEFeedback(EchoSlice3):
    """Equally informed QoE/SLA feedback baseline. Same counts, templates, prior, bounds, count moves and
    QoE estimate as EchoSlice. Every hold it reads each bounded slice's mean QoE estimate over the scored part
    of the hold and moves that slice's log-rate multiplier up by `fb_step` if the slice is below its target,
    down by `fb_step` if it is above target + `fb_band`, inside the same theta box. No trials."""

    def __init__(self, fb_step=0.1, fb_band=0.5, **kw):
        kw.setdefault("name", "qoe-feedback")
        super().__init__(**kw)
        self.fb_step, self.fb_band = fb_step, fb_band

    def decide(self, t, kpm):
        if self.K < 2:
            return self.x
        a = self._count_mask(t, kpm)
        n = np.array([float(((kpm["flow_slice"] == k) & a).sum()) for k in range(self.K)])
        if self.p0 is None or np.any((np.abs(n - self.n_ref) >= np.maximum(2.0, 0.25 * self.n_ref)) & self.bounded):
            self.kpm_now, self.n_now = kpm, n
            self.n_ref = n
            self.p0 = self._prior(kpm, n)
            self.c = self._prior(kpm, n, self.theta)
            self.x = self.c.copy()
            self.t_phase = t
            return self.x
        if t < self.t_warm or t - self.t_phase < self.hold:
            return self.x
        self.t_phase = t
        m = self.mon.qoe(t, self.hold - self.settle)
        fs = self.S.fslice
        for k in range(self.K):
            if not self.bounded[k]:
                continue
            v = m[(fs == k) & np.isfinite(m)]
            if not len(v):
                continue
            q = float(v.mean()) + self.rng.normal(0, self.noise)
            tgt = SLA_TARGET.get(self.names[k], 4.0)
            if q < tgt:
                self.theta[k] += self.fb_step
            elif q > tgt + self.fb_band:
                self.theta[k] -= self.fb_step
        self.theta = np.clip(self.theta, -self.theta_max, self.theta_max)
        self.c = self._prior(self.kpm_now, self.n_now, self.theta)
        self.x = self.c.copy()
        return self.x


class RandomSteps(Base):
    """Randomised interventions for system identification (theory checks): the share of slice k is
    held at a random level in [lo, hi] for a random 2-30 s, the other slices split the rest equally."""

    def __init__(self, k=0, lo=0.1, hi=0.6, tmin=2.0, tmax=30.0):
        self.k, self.lo, self.hi, self.tmin, self.tmax = k, lo, hi, tmin, tmax
        self.name = f"steps-k{k}"

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        self.t_next = 0.0
        self.levels = []

    def decide(self, t, kpm):
        if t + 1e-9 >= self.t_next:
            lv = float(self.rng.uniform(self.lo, self.hi))
            self.t_next = t + float(self.rng.uniform(self.tmin, self.tmax))
            x = np.full(self.K, (1.0 - lv) / max(self.K - 1, 1))
            x[self.k] = lv
            self.x = project(x)
            self.levels.append((float(t), lv))
        return self.x
