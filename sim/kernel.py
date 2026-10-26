"""Numba kernel for the EchoSlice gate pilot.

One NR cell, K slices, N flows (one flow per UE). Time-stepped fluid model
with dt = 10 ms. Everything that changes inside a slicer period lives here:
channel, per-flow gNB queues, two-stage slice scheduler, TCP Cubic senders,
dash.js-style ABR clients (throughput rule, BOLA, dynamic), and a GCC
(delay-based) real-time video sender (cloud gaming or XR, per-flow rate bounds
and frame budget). TCP flows run Cubic or, with L4S, TCP Prague against
ECN marks set when the per-UE queue delay passes about 1 ms. Flows with
cbr > 0 send at a fixed rate and do not adapt (the open-loop twin).

The Python side (engine.py) calls run_ticks() once per slicer period,
reads the per-period counters, and asks the slicer for the next shares.
"""
import math
import numpy as np
from numba import njit

# flow types
VIDEO, BULK, GAME = 0, 1, 2
# video states
V_IDLE, V_REQ, V_DL = 0, 1, 2
# ABR rules
ABR_TPUT, ABR_BOLA, ABR_DYN = 0, 1, 2
# GCC rate-control states
G_HOLD, G_INC, G_DEC = 0, 1, 2

MSS = 1448.0                 # bytes
IW = 10.0 * MSS              # initial window
CUBIC_C = 0.4                # MSS / s^3
CUBIC_BETA = 0.7
RTO_MIN = 0.2
RWND = 16e6                  # bytes, receive window cap
RE_PER_PRB_S = 12 * 14 * 2000.0   # REs per PRB per second at 30 kHz SCS
DL_FRAC = 0.74               # DDDSU-like TDD downlink fraction
OVERHEAD = 0.14              # DMRS, PDCCH, CSI-RS ...
ETA_MAX = 7.4                # bits per RE (256QAM, high code rate)
SHANNON_ATT = 0.75           # attenuated Shannon factor
EWMA_FAST_HL = 3.0           # dash.js throughput half-lives (s)
EWMA_SLOW_HL = 8.0
ABR_SAFETY = 0.9             # dash.js bandwidthSafetyFactor
STABLE_BUF = 12.0            # dash.js stableBufferTime
TOP_BUF = 30.0               # dash.js bufferTimeAtTopQuality
GCC_FB = 0.05                # feedback interval (s)
GCC_WIN = 20                 # trendline window (samples)
GCC_MIN = 1.0e6
GCC_MAX = 20.0e6
GAME_LATE_S = 0.100          # one-way delay budget for a frame (cloud gaming default)
CC_CUBIC, CC_PRAGUE = 0, 1
L4S_LO = 0.0005              # L4S marking ramp on per-UE queue delay (s), DualPI2-like ~1 ms step
L4S_HI = 0.0015
PRAGUE_G = 1.0 / 16.0        # Prague/DCTCP alpha gain


@njit(cache=True)
def _seed(s):
    np.random.seed(s)


def seed_kernel(s):
    _seed(s)


@njit(cache=True)
def _waterfill(need, cap, out):
    """Max-min fair split of `cap` over needs (equal share, capped by need)."""
    m = need.shape[0]
    if m == 0:
        return 0.0
    order = np.argsort(need)
    rem = cap
    used = 0.0
    for j in range(m):
        i = order[j]
        share = rem / (m - j)
        if need[i] <= share:
            out[i] = need[i]
        else:
            out[i] = share
        rem -= out[i]
        used += out[i]
    return used


@njit(cache=True)
def _abr_tput_level(S, i, ladder):
    est = _tput_estimate(S, i)
    lev = 0
    for l in range(ladder.shape[0]):
        if ladder[l] <= ABR_SAFETY * est:
            lev = l
    return lev


@njit(cache=True)
def _tput_estimate(S, i):
    if S.ewf_w[i] <= 0.0:
        return S.p_init_tput[0]
    f = S.ewf[i] / S.ewf_w[i]
    s = S.ews[i] / S.ews_w[i]
    return min(f, s)


@njit(cache=True)
def _bola_level(S, i, ladder, util, Vp, gp):
    buf = S.buf[i]
    best = 0
    score = -1e18
    for l in range(ladder.shape[0]):
        sc = (Vp * (util[l] + gp) - buf) / ladder[l]
        if sc >= score:
            score = sc
            best = l
    # BOLA-O (dash.js): do not climb above a throughput-sustainable level
    lt = _abr_tput_level(S, i, ladder)
    if best > S.level[i] and best > lt:
        best = max(lt, S.level[i])
    return best


@njit(cache=True)
def run_ticks(S, x, n_ticks, ladder, util, Vp, gp):
    dt = S.p_dt[0]
    B = S.p_B[0]
    strict = S.p_strict[0]
    K = x.shape[0]
    N = S.ftype.shape[0]
    rho = S.p_rho[0]
    sig_sh = S.p_sig_shadow[0]
    sig_ff = S.p_sig_fast[0]
    layers = S.p_layers[0]
    t_eval0 = S.p_t_eval0[0]

    need = np.zeros(N)
    alloc = np.zeros(N)
    serve = np.zeros(N)
    used_k = np.zeros(K)
    nlev = ladder.shape[0]

    n_chunk = S.evc_time.shape[1]
    chunk = S.p_chunk[0]
    for step in range(n_ticks):
        t = S.t[0]
        in_eval = t >= t_eval0
        ci = 0
        if in_eval:
            ci = int((t - t_eval0) / chunk)
            if ci >= n_chunk:
                ci = n_chunk - 1

        # ---------------- 1. channel ----------------
        for i in range(N):
            S.shadow[i] = rho * S.shadow[i] + math.sqrt(1.0 - rho * rho) * sig_sh * np.random.randn()
            sdb = S.sinr_mean[i] + S.shadow[i] + sig_ff * np.random.randn()
            eta = SHANNON_ATT * math.log2(1.0 + 10.0 ** (sdb / 10.0))
            if eta > ETA_MAX:
                eta = ETA_MAX
            if eta < 0.05:
                eta = 0.05
            S.rprb[i] = RE_PER_PRB_S * eta * layers * (1.0 - OVERHEAD) * DL_FRAC  # bit/s per PRB

        # ---------------- 1b. sessions that end now ----------------
        for i in range(N):
            if S.stopped[i] == 0 and t >= S.t_stop[i]:
                S.stopped[i] = 1
                S.q[i] = 0.0
                S.unsent[i] = 0.0
                S.undeliv[i] = 0.0
                S.vstate[i] = V_IDLE
                S.enc_rate[i] = 0.0

        # ---------------- 2. senders -> gNB queues ----------------
        for i in range(N):
            if t < S.t_start[i] or t >= S.t_stop[i]:
                continue
            ft = S.ftype[i]
            a = 0.0
            if S.cbr[i] > 0.0:
                a = S.cbr[i] / 8.0 * dt
                if ft == GAME:
                    S.g_sent[i] += a
            elif ft == BULK or (ft == VIDEO and S.vstate[i] == V_DL):
                sr = S.srate[i]
                if sr < 1e5:
                    sr = 1e5
                rtt = S.base_rtt[i] + S.q[i] * 8.0 / sr
                S.srtt[i] = 0.875 * S.srtt[i] + 0.125 * rtt
                a = S.cwnd[i] / rtt * dt
                if ft == VIDEO:
                    if a > S.unsent[i]:
                        a = S.unsent[i]
                    S.unsent[i] -= a
            elif ft == GAME:
                a = S.enc_rate[i] / 8.0 * dt * math.exp(0.2 * np.random.randn() - 0.02)
                S.g_sent[i] += a
            S.q[i] += a
            S.acc_arr[i] += a * 8.0
            S.acc_arr_k[S.fslice[i]] += a * 8.0

        # ---------------- 3. two-stage slice scheduler ----------------
        for i in range(N):
            serve[i] = 0.0
        tot_used = 0.0
        for k in range(K):
            Pk = x[k] * B
            used_k[k] = 0.0
            if Pk <= 0.0:
                continue
            # collect backlogged flows of slice k
            m = 0
            for i in range(N):
                if S.fslice[i] == k and S.q[i] > 0.0:
                    m += 1
            if m == 0:
                continue
            nd = np.empty(m)
            ids = np.empty(m, dtype=np.int64)
            j = 0
            for i in range(N):
                if S.fslice[i] == k and S.q[i] > 0.0:
                    nd[j] = S.q[i] * 8.0 / (S.rprb[i] * Pk * dt)
                    ids[j] = i
                    j += 1
            al = np.zeros(m)
            u = _waterfill(nd, 1.0, al)
            for j in range(m):
                i = ids[j]
                serve[i] = al[j] * Pk * S.rprb[i] * dt / 8.0
                S.acc_prb_k[k] += al[j] * Pk * dt
            used_k[k] = u * Pk
            tot_used += u * Pk
        # stage 2: unused + unassigned PRBs shared by cell-wide PF among still-backlogged flows
        if strict == 0:
            pool = B - tot_used
            if pool > 1e-9:
                m = 0
                for i in range(N):
                    if S.q[i] - serve[i] > 1e-9:
                        m += 1
                if m > 0:
                    nd = np.empty(m)
                    ids = np.empty(m, dtype=np.int64)
                    j = 0
                    for i in range(N):
                        if S.q[i] - serve[i] > 1e-9:
                            nd[j] = (S.q[i] - serve[i]) * 8.0 / (S.rprb[i] * pool * dt)
                            ids[j] = i
                            j += 1
                    al = np.zeros(m)
                    _waterfill(nd, 1.0, al)
                    for j in range(m):
                        i = ids[j]
                        serve[i] += al[j] * pool * S.rprb[i] * dt / 8.0
                        S.acc_prb_k[S.fslice[i]] += al[j] * pool * dt

        # ---------------- 4. apply service, rates, overflow ----------------
        for i in range(N):
            s = serve[i]
            if s > S.q[i]:
                s = S.q[i]
            backlogged = S.q[i] > 0.0
            S.q[i] -= s
            if backlogged:
                inst = s * 8.0 / dt
                S.srate[i] = 0.9 * S.srate[i] + 0.1 * inst
            S.acc_srv[i] += s * 8.0
            S.acc_srv_k[S.fslice[i]] += s * 8.0
            if in_eval:
                S.ev_srv[i] += s * 8.0
                S.evc_srv[i, ci] += s * 8.0
            ft = S.ftype[i]
            if ft == VIDEO:
                S.undeliv[i] -= s
            elif ft == GAME:
                S.g_recv_acc[i] += s * 8.0
            # overflow (drop tail)
            if S.q[i] > S.qmax[i]:
                drop = S.q[i] - S.qmax[i]
                S.q[i] = S.qmax[i]
                if ft == GAME or S.cbr[i] > 0.0:
                    S.g_lost[i] += drop
                    if in_eval:
                        S.ev_lost[i] += drop
                else:
                    if ft == VIDEO:
                        S.unsent[i] += drop   # retransmitted later
                    if t - S.last_loss[i] > S.srtt[i]:
                        S.last_loss[i] = t
                        S.wmax[i] = S.cwnd[i]
                        bt = 0.5 if S.cc[i] == CC_PRAGUE else CUBIC_BETA
                        S.cwnd[i] = max(S.cwnd[i] * bt, 2.0 * MSS)
                        S.ssthresh[i] = S.cwnd[i]
                        S.in_ss[i] = 0
                        S.epoch[i] = t
            # queueing delay stats
            sr = S.srate[i]
            if sr < 1e5:
                sr = 1e5
            qd = S.q[i] * 8.0 / sr
            S.acc_qd[i] += qd * dt
            if S.l4s[i] == 1:
                pm = (qd - L4S_LO) / (L4S_HI - L4S_LO)
                if pm < 0.0:
                    pm = 0.0
                if pm > 1.0:
                    pm = 1.0
                S.mark[i] = pm
                if in_eval:
                    S.ev_mark[i] += pm * dt
            if in_eval and t >= S.t_start[i] and t < S.t_stop[i]:
                S.ev_time[i] += dt
                S.ev_qd[i] += qd * dt
                S.evc_time[i, ci] += dt
                S.evc_qd[i, ci] += qd * dt
                if ft == GAME:
                    S.ev_rate[i] += S.enc_rate[i] * dt
                    S.evc_rate[i, ci] += S.enc_rate[i] * dt
                    if S.base_rtt[i] * 0.5 + qd > S.late_s[i]:
                        S.ev_late[i] += dt
                        S.evc_late[i, ci] += dt

        # ---------------- 5. TCP window growth ----------------
        for i in range(N):
            ft = S.ftype[i]
            if t < S.t_start[i] or t >= S.t_stop[i]:
                continue
            if S.cbr[i] > 0.0 or not (ft == BULK or (ft == VIDEO and S.vstate[i] == V_DL)):
                continue
            rtt = S.srtt[i]
            if S.cc[i] == CC_PRAGUE:
                # TCP Prague: alpha = EWMA of the marked fraction; cut cwnd by alpha/2 per RTT
                # while marks arrive, else Reno additive increase (slow start until the first mark)
                pm = S.mark[i]
                S.pr_alpha[i] += min(1.0, dt / rtt) * PRAGUE_G * (pm - S.pr_alpha[i])
                if pm > 0.0:
                    S.in_ss[i] = 0
                    S.cwnd[i] *= 1.0 - 0.5 * S.pr_alpha[i] * min(1.0, dt / rtt)
                elif S.in_ss[i] == 1:
                    S.cwnd[i] *= 2.0 ** (dt / rtt)
                else:
                    S.cwnd[i] += MSS * dt / rtt
                if S.cwnd[i] < 2.0 * MSS:
                    S.cwnd[i] = 2.0 * MSS
            elif S.in_ss[i] == 1:
                S.cwnd[i] *= 2.0 ** (dt / rtt)          # doubling per RTT
                if S.cwnd[i] >= S.ssthresh[i]:
                    S.in_ss[i] = 0
                    S.epoch[i] = t
                    S.wmax[i] = S.cwnd[i]
            else:
                tt = t - S.epoch[i]
                wmax_pk = S.wmax[i] / MSS
                Kc = (wmax_pk * (1.0 - CUBIC_BETA) / CUBIC_C) ** (1.0 / 3.0)
                w_cub = (CUBIC_C * (tt - Kc) ** 3 + wmax_pk) * MSS
                w_est = (wmax_pk * CUBIC_BETA + 3.0 * (1.0 - CUBIC_BETA) / (1.0 + CUBIC_BETA) * tt / rtt) * MSS
                target = max(w_cub, w_est)
                if target > S.cwnd[i]:
                    inc = target - S.cwnd[i]
                    lim = 0.5 * S.cwnd[i] * dt / rtt
                    if inc > lim:
                        inc = lim
                    S.cwnd[i] += inc
            if S.cwnd[i] > RWND:
                S.cwnd[i] = RWND

        # ---------------- 6. video clients ----------------
        for i in range(N):
            if S.ftype[i] != VIDEO or S.cbr[i] > 0.0 or t < S.t_start[i] or t >= S.t_stop[i]:
                continue
            L = S.seg_dur[i]
            # segment completion
            if S.vstate[i] == V_DL and S.undeliv[i] <= 1e-6:
                dur = t + dt - S.t_first[i]
                if dur < dt:
                    dur = dt
                tp = S.seg_bytes[i] * 8.0 / dur
                af = 0.5 ** (dur / EWMA_FAST_HL)
                aS = 0.5 ** (dur / EWMA_SLOW_HL)
                S.ewf[i] = af * S.ewf[i] + (1 - af) * tp
                S.ewf_w[i] = af * S.ewf_w[i] + (1 - af)
                S.ews[i] = aS * S.ews[i] + (1 - aS) * tp
                S.ews_w[i] = aS * S.ews_w[i] + (1 - aS)
                k = S.seg_idx[i]
                if k < S.seg_level.shape[1]:
                    S.seg_level[i, k] = S.level[i]
                    S.seg_tdone[i, k] = t + dt
                    S.seg_tput[i, k] = tp
                S.seg_idx[i] = k + 1
                S.buf[i] += L
                S.vstate[i] = V_IDLE
                S.q[i] = 0.0          # leftover bytes are duplicate retransmissions
                S.unsent[i] = 0.0
                S.last_active[i] = t + dt
            # playback
            if S.playing[i] == 1:
                S.buf[i] -= dt
                S.played[i] += dt
                if S.buf[i] <= 0.0:
                    S.buf[i] = 0.0
                    S.playing[i] = 0
                    S.stall_t0[i] = t
                    S.stall_media[i] = S.played[i]
            else:
                if S.buf[i] >= L - 1e-9:
                    if S.started[i] == 1:
                        ns = S.n_stall[i]
                        if ns < S.st_wall.shape[1]:
                            S.st_wall[i, ns] = S.stall_t0[i]
                            S.st_dur[i, ns] = t - S.stall_t0[i]
                            S.st_media[i, ns] = S.stall_media[i]
                            S.n_stall[i] = ns + 1
                    else:
                        S.started[i] = 1
                        S.t_play0[i] = t
                    S.playing[i] = 1
            # request scheduling
            if S.vstate[i] == V_IDLE:
                rule = S.abr[i]
                if rule == ABR_DYN:
                    if S.use_bola[i] == 0 and S.buf[i] >= STABLE_BUF:
                        S.use_bola[i] = 1
                    elif S.use_bola[i] == 1 and S.buf[i] < 0.5 * STABLE_BUF:
                        S.use_bola[i] = 0
                    rule = ABR_BOLA if S.use_bola[i] == 1 else ABR_TPUT
                if rule == ABR_BOLA and S.buf[i] >= 2.0 * L:
                    # BOLA-BASIC: quality from the score on the real buffer; keep downloading
                    # while some quality has a positive score, i.e. buffer < Vp (u_max + gp),
                    # BOLA-O limits climbs to what the
                    # throughput supports. (dash.js adds a placeholder buffer instead.)
                    lev = _bola_level(S, i, ladder, util, Vp, gp)
                    max_buf = Vp * (util[nlev - 1] + gp)     # 32.5 s with the dash.js parameters
                    go = S.buf[i] <= max_buf - L
                else:
                    lev = _abr_tput_level(S, i, ladder)
                    tgt = TOP_BUF if lev == nlev - 1 else STABLE_BUF
                    go = S.buf[i] < tgt
                if go:
                    S.level[i] = lev
                    S.seg_bytes[i] = ladder[lev] * L / 8.0 * math.exp(0.15 * np.random.randn() - 0.011)
                    S.vstate[i] = V_REQ
                    S.t_req[i] = t
                    idle = t - S.last_active[i]
                    rto = max(RTO_MIN, S.srtt[i] * 2.0)
                    if idle > rto:
                        w = S.cwnd[i] * 0.5 ** (idle / rto)
                        S.cwnd[i] = max(IW, w)
                        S.ssthresh[i] = max(S.ssthresh[i], S.cwnd[i])
                        S.in_ss[i] = 1
            if S.vstate[i] == V_REQ and t >= S.t_req[i] + S.base_rtt[i]:
                S.vstate[i] = V_DL
                S.unsent[i] = S.seg_bytes[i]
                S.undeliv[i] = S.seg_bytes[i]
                S.t_first[i] = t

        # ---------------- 7. GCC senders ----------------
        for i in range(N):
            if S.ftype[i] != GAME or S.cbr[i] > 0.0 or t < S.t_start[i] or t >= S.t_stop[i]:
                continue
            if t + 1e-9 < S.g_tnext[i]:
                continue
            S.g_tnext[i] = t + GCC_FB
            sr = S.srate[i]
            if sr < 1e5:
                sr = 1e5
            d_ms = S.q[i] * 8.0 / sr * 1000.0
            S.g_smooth[i] = 0.9 * S.g_smooth[i] + 0.1 * d_ms
            p = S.g_ptr[i]
            S.g_dly[i, p] = S.g_smooth[i]
            S.g_tim[i, p] = t * 1000.0
            S.g_ptr[i] = (p + 1) % GCC_WIN
            if S.g_n[i] < GCC_WIN:
                S.g_n[i] += 1
            n = S.g_n[i]
            # receive rate (EWMA, ~500 ms)
            rr = S.g_recv_acc[i] / GCC_FB
            S.g_recv_acc[i] = 0.0
            S.g_recv[i] = 0.9 * S.g_recv[i] + 0.1 * rr
            # --- trendline over-use detector (libwebrtc TrendlineEstimator) ---
            if n >= 5:
                mt = 0.0
                md = 0.0
                for j in range(n):
                    mt += S.g_tim[i, j]
                    md += S.g_dly[i, j]
                mt /= n
                md /= n
                num = 0.0
                den = 0.0
                for j in range(n):
                    num += (S.g_tim[i, j] - mt) * (S.g_dly[i, j] - md)
                    den += (S.g_tim[i, j] - mt) ** 2
                slope = num / den if den > 0 else 0.0
                mtr = slope * 60.0 * 4.0
                gam = S.g_gamma[i]
                if abs(mtr) <= gam + 15.0:
                    kk = 0.039 if abs(mtr) < gam else 0.0087
                    gam += kk * (abs(mtr) - gam) * GCC_FB * 1000.0
                    if gam < 6.0:
                        gam = 6.0
                    if gam > 600.0:
                        gam = 600.0
                    S.g_gamma[i] = gam
                if mtr > gam:
                    if S.g_over_t[i] < 0:
                        S.g_over_t[i] = GCC_FB / 2.0
                    else:
                        S.g_over_t[i] += GCC_FB
                    S.g_ocount[i] += 1
                    if S.g_over_t[i] > 0.01 and S.g_ocount[i] > 1 and slope >= S.g_prev_slope[i]:
                        S.g_over_t[i] = 0.0
                        S.g_ocount[i] = 0
                        S.g_hyp[i] = 1
                elif mtr < -gam:
                    S.g_over_t[i] = -1.0
                    S.g_ocount[i] = 0
                    S.g_hyp[i] = -1
                else:
                    S.g_over_t[i] = -1.0
                    S.g_ocount[i] = 0
                    S.g_hyp[i] = 0
                S.g_prev_slope[i] = slope
            sig = S.g_hyp[i]
            # --- AIMD rate control (libwebrtc AimdRateControl) ---
            A = S.g_A[i]
            A_prev = A
            R = S.g_recv[i]
            if sig == 1:
                red_int = S.base_rtt[i]
                if red_int < 0.01:
                    red_int = 0.01
                if red_int > 0.2:
                    red_int = 0.2
                if t - S.g_tdec[i] >= red_int or R < 0.5 * A:
                    Anew = 0.85 * R
                    if Anew < A:
                        A = Anew
                    rm = R / 1e6       # link-capacity estimate (Mb/s)
                    if S.g_avgmax[i] < 0:
                        S.g_avgmax[i] = rm
                    else:
                        S.g_avgmax[i] = 0.95 * S.g_avgmax[i] + 0.05 * rm
                    S.g_tdec[i] = t
                S.g_state[i] = G_HOLD
            elif sig == -1:
                S.g_state[i] = G_HOLD
            else:
                if S.g_state[i] == G_HOLD or S.g_state[i] == G_DEC:
                    S.g_state[i] = G_INC
                if S.g_state[i] == G_INC:
                    am = S.g_avgmax[i]
                    near = am > 0 and abs(A / 1e6 - am) < 3.0 * 0.4 * am ** 0.5
                    if am > 0 and A / 1e6 > am + 3.0 * 0.4 * am ** 0.5:
                        S.g_avgmax[i] = -1.0
                        near = False
                    if near:
                        fs = A / 60.0
                        npk = math.ceil(fs / (1200 * 8.0))
                        pkt = fs / max(npk, 1.0)
                        resp = S.base_rtt[i] + 0.1
                        A += max(4000.0, pkt / resp) * GCC_FB
                    else:
                        A *= 1.08 ** GCC_FB
            cap = 1.5 * R + 1e4
            if A > A_prev and A > cap and t - S.t_start[i] > 2.0:
                A = max(A_prev, cap)
            # loss-based controller, once per second
            S.g_loss_t[i] += GCC_FB
            if S.g_loss_t[i] >= 1.0:
                sent = S.g_sent[i]
                pl = S.g_lost[i] / sent if sent > 0 else 0.0
                if pl > 0.1:
                    S.g_Aloss[i] = S.g_Aloss[i] * (1.0 - 0.5 * pl)
                elif pl < 0.02:
                    S.g_Aloss[i] = min(S.g_Aloss[i] * 1.05, S.g_max[i])
                S.g_sent[i] = 0.0
                S.g_lost[i] = 0.0
                S.g_loss_t[i] = 0.0
            if A > S.g_Aloss[i]:
                A = S.g_Aloss[i]
            if A < S.g_min[i]:
                A = S.g_min[i]
            if A > S.g_max[i]:
                A = S.g_max[i]
            S.g_A[i] = A
        for i in range(N):
            if S.ftype[i] == GAME and S.cbr[i] <= 0.0 and t >= S.t_start[i] and t < S.t_stop[i]:
                S.enc_rate[i] += (S.g_A[i] - S.enc_rate[i]) * min(1.0, dt / 0.1)

        S.t[0] = t + dt
