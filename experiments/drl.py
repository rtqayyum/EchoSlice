"""DRL slicing baseline: PPO (Schulman et al. 2017) in plain numpy.

Two training regimes, same agent, same reward:
  loop  trained in the simulator with the adaptive apps in the loop (ABR, GCC, TCP react to the
        shares). The strongest a DRL slicer can be, but it needs a simulator that models the
        reactions, and thousands of episodes of trial and error.
  twin  trained the way DRL slicers are usually trained: on replayed demand. Each training episode
        first records every flow's offered rate under the equal split in the real (adaptive) cell,
        then replays it as fixed-rate traffic (the open-loop twin), with QoE inferred from the
        served rate. The policy never sees an app react.
  prior trained like loop, but the action is a log-multiplier of EchoSlice's per-session template
        rates (shares then follow EchoSlice's count prior), so the agent has the same information and
        the same starting point as EchoSlice (review round 4: an equally informed learned baseline).
Both are evaluated in the adaptive simulator.

Agent: Gaussian policy over 3 slice logits (shares = softmax, then the same bounds as all slicers),
acting every 4 s; state = per-slice KPMs (share, PRB use, offered and served load over capacity,
queue delay, active sessions, slice QoE and SLA shortfall) plus strict / lambda flags. Reward =
the same closed-loop utility EchoSlice optimises (mean user MOS - lambda * slice shortfall).

  python -m experiments.drl train --regime loop --out policies/drl_loop.json --workers 32 --iters 150
  python -m experiments.drl smoke                      # gradient check + a 2-iteration run
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from sim import kernel as K                      # noqa: E402
from sim import slicers as SL                    # noqa: E402
from sim.engine import Scenario, simulate        # noqa: E402

NAMES3 = ["video", "game", "bulk"]
PRIOR_THETA_MAX = 1.5            # same box as EchoSlice's learned log-rates
OBS_PER_SLICE = 8
OBS_DIM = OBS_PER_SLICE * 3 + 4
ACT_DIM = 3
ACT_EVERY = 4.0
R_CENTER, R_SCALE = 4.0, 1.0


# ======================================================================= small numpy MLP + Adam
class MLP:
    def __init__(self, sizes, rng, out_scale=1.0):
        self.p = {}
        for i, (a, b) in enumerate(zip(sizes[:-1], sizes[1:])):
            sc = math.sqrt(2.0 / a) if i < len(sizes) - 2 else out_scale / math.sqrt(a)
            self.p[f"W{i}"] = rng.normal(0, sc, (a, b))
            self.p[f"b{i}"] = np.zeros(b)
        self.n = len(sizes) - 1

    def forward(self, x):
        cache = [x]
        h = x
        for i in range(self.n):
            z = h @ self.p[f"W{i}"] + self.p[f"b{i}"]
            h = np.tanh(z) if i < self.n - 1 else z
            cache.append(h)
        self._cache = cache
        return h

    def backward(self, gout):
        g = {}
        cache = self._cache
        d = gout
        for i in reversed(range(self.n)):
            hin = cache[i]
            g[f"W{i}"] = hin.T @ d
            g[f"b{i}"] = d.sum(0)
            if i > 0:
                d = (d @ self.p[f"W{i}"].T) * (1.0 - cache[i] ** 2)
        return g


class Adam:
    def __init__(self, params, lr=3e-4, b1=0.9, b2=0.999, eps=1e-8):
        self.lr, self.b1, self.b2, self.eps = lr, b1, b2, eps
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}
        self.t = 0

    def step(self, params, grads):
        self.t += 1
        for k in params:
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * grads[k]
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * grads[k] ** 2
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            params[k] -= self.lr * mh / (np.sqrt(vh) + self.eps)


class RunningNorm:
    def __init__(self, dim):
        self.n, self.mean, self.m2 = 1e-4, np.zeros(dim), np.ones(dim)

    def update(self, X):
        for x in X:
            self.n += 1
            d = x - self.mean
            self.mean += d / self.n
            self.m2 += d * (x - self.mean)

    @property
    def std(self):
        return np.sqrt(np.maximum(self.m2 / self.n, 1e-6))

    def __call__(self, x):
        return np.clip((x - self.mean) / self.std, -5.0, 5.0)


# ======================================================================= policy (shared by training and evaluation)
def softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def policy_to_json(pi, logstd, norm, meta):
    return dict(pi={k: v.tolist() for k, v in pi.p.items()}, logstd=logstd.tolist(),
                norm_mean=norm.mean.tolist(), norm_std=norm.std.tolist(), sizes=meta["sizes"], meta=meta)


class _Frozen:
    """Numpy-only forward pass of a saved policy (what workers and evaluation runs use)."""

    def __init__(self, d):
        self.W = [(np.array(d["pi"][f"W{i}"]), np.array(d["pi"][f"b{i}"])) for i in range(len(d["sizes"]) - 1)]
        self.logstd = np.array(d["logstd"])
        self.mu_n, self.sd_n = np.array(d["norm_mean"]), np.array(d["norm_std"])

    def mean(self, obs):
        h = np.clip((obs - self.mu_n) / self.sd_n, -5.0, 5.0)
        for i, (W, b) in enumerate(self.W):
            h = h @ W + b
            if i < len(self.W) - 1:
                h = np.tanh(h)
        return h


class PolicySlicer(SL.Base):
    """Runs a DRL policy as a slicer. In training mode it samples actions and records transitions."""

    def __init__(self, policy, lam=0.0, name=None, train=False, rng_seed=0):
        if isinstance(policy, str):
            path = policy if os.path.isabs(policy) else os.path.join(os.environ.get("ES_ROOT", HERE), policy)
            with open(path) as f:
                policy = json.load(f)
        self.pol = _Frozen(policy)
        # regime 'prior': the action is a log-multiplier of EchoSlice's per-session template rates (same
        # counts and templates as EchoSlice), instead of three share logits
        self.mode = "prior" if policy.get("meta", {}).get("regime") == "prior" else "shares"
        self.lam = lam
        self.train = train
        self.arng = np.random.default_rng(rng_seed)
        self.name = name or ("drl" + (f"-l{lam:g}" if lam > 0 else ""))

    def reset(self, sc, names, S, mon, rng):
        super().reset(sc, names, S, mon, rng)
        assert names == NAMES3, "the DRL baseline is defined for video/game/bulk cells"
        self.t_next = 0.0
        self.traj = []          # (obs, act, logp, reward-of-this-action)
        self.pending = None
        self.x = np.full(3, 1.0 / 3)
        if self.mode == "prior":
            self.es = SL.EchoSlice3()
            self.es.reset(sc, names, S, mon, rng)

    def _obs(self, t, kpm):
        S, sc = self.S, self.sc
        cap = np.maximum(kpm["eff"] * sc.B, 1.0)
        a = kpm["flow_active"]
        m = self.mon.qoe(t, ACT_EVERY)
        _, dfc = SL.sla_utility(m, S.fslice, self.names, self.lam)
        f = []
        for k in range(3):
            sel = (kpm["flow_slice"] == k) & a
            mk = m[(S.fslice == k) & np.isfinite(m)]
            qd = kpm["flow_qdelay"][sel].mean() if sel.any() else 0.0
            f += [self.x[k], kpm["prb"][k] / sc.B, min(3.0, kpm["offered"][k] / cap[k]),
                  min(3.0, kpm["served"][k] / cap[k]), min(3.0, 10.0 * qd), sel.sum() / 30.0,
                  (mk.mean() / 5.0) if len(mk) else 0.0, dfc[k] / 2.0]
        f += [float(sc.strict), self.lam / 2.0, float(sc.rt_kind == "xr"), float(sc.bulk_cc == "prague")]
        return np.array(f, dtype=float)

    def decide(self, t, kpm):
        if t + 1e-9 < self.t_next:
            return self.x
        self.t_next = t + ACT_EVERY
        obs = self._obs(t, kpm)
        if self.train and self.pending is not None:
            u, _ = SL.sla_utility(self.mon.qoe(t, ACT_EVERY), self.S.fslice, self.names, self.lam)
            o, a_, lp = self.pending
            self.traj.append((o, a_, lp, R_SCALE * (u - R_CENTER)))
        mu = self.pol.mean(obs)
        if self.train:
            sd = np.exp(self.pol.logstd)
            act = mu + sd * self.arng.normal(size=ACT_DIM)
            lp = float(-0.5 * (((act - mu) / sd) ** 2).sum() - self.pol.logstd.sum() - 0.5 * ACT_DIM * math.log(2 * math.pi))
            self.pending = (obs, act, lp)
        else:
            act = mu
        if self.mode == "prior":
            th = PRIOR_THETA_MAX * np.tanh(act) * self.es.bounded
            a = kpm["flow_active"]
            n = np.array([float(((kpm["flow_slice"] == k) & a).sum()) for k in range(3)])
            self.x = self.es._prior(kpm, n, th)
        else:
            self.x = SL.project(softmax(act))
        return self.x


# ======================================================================= training scenarios
E6_MAX = dict(n_video=32, n_game=12, n_bulk=8)


def sample_scenario(rng):
    strict = bool(rng.random() < 0.5)
    lam = float(rng.choice([0.0, 0.5, 1.0, 2.0]))
    u = rng.random()
    if u < 0.5:
        sc = dict(n_video=int(rng.integers(8, 57)), n_game=int(rng.integers(2, 25)), n_bulk=int(rng.integers(2, 17)),
                  abr=str(rng.choice(["dyn", "tput", "bola"])), T=600.0, t_eval0=300.0)
    elif u < 0.8:
        pat = str(rng.choice(["game_surge", "bulk_wave", "video_peak", "churn"]))
        sc = {k: max(2, int(round(v * rng.uniform(0.7, 1.3)))) for k, v in E6_MAX.items()}
        sc.update(abr="dyn", pattern=pat, T=1200.0, t_eval0=200.0)
    else:
        from experiments.campaign_jobs import E7_DAY, E7_FLASH
        base = dict(E7_DAY) if rng.random() < 0.5 else dict(E7_FLASH)
        for k in ("n_video", "n_game", "n_bulk"):
            base[k] = max(2, int(round(base[k] * rng.uniform(0.8, 1.2))))
        sc = base
    sc["strict"] = strict
    return sc, lam


def replay_rates(sc_kw, seed):
    """Per-flow offered rate under the equal split in the adaptive cell (the 'historic trace')."""
    class Rec(SL.Static):
        def reset(self, *a):
            super().reset(*a)
            self.acc = None
            self.cnt = None

        def decide(self, t, kpm):
            fo, act = kpm["flow_offered"], kpm["flow_active"]
            if self.acc is None:
                self.acc, self.cnt = np.zeros_like(fo), np.zeros_like(fo)
            self.acc += np.where(act, fo, 0.0)
            self.cnt += act
            return self.x
    rec = Rec()
    simulate(Scenario(**sc_kw), rec, seed, score=False)
    return (rec.acc / np.maximum(rec.cnt, 1)).tolist()


def rollout(args):
    pol_json, sc_kw, lam, seed, regime = args
    kw = dict(sc_kw)
    if regime == "twin":
        kw["cbr"] = replay_rates(sc_kw, seed)
    sl = PolicySlicer(pol_json, lam=lam, train=True, rng_seed=seed + 17)
    simulate(Scenario(**kw), sl, seed, score=False)
    if not sl.traj:
        return None
    o, a, lp, r = zip(*sl.traj)
    return dict(obs=np.array(o), act=np.array(a), logp=np.array(lp), rew=np.array(r))


def evaluate(args):
    """Deterministic policy on one scenario; returns the mean step utility."""
    pol_json, sc_kw, lam, seed, regime = args
    kw = dict(sc_kw)
    if regime == "twin":
        kw["cbr"] = replay_rates(sc_kw, seed)
    sl = PolicySlicer(pol_json, lam=lam, train=True, rng_seed=seed)
    sl.pol.logstd = np.full(ACT_DIM, -20.0)       # deterministic
    simulate(Scenario(**kw), sl, seed, score=False)
    return float(np.mean([t[3] for t in sl.traj])) if sl.traj else float("nan")


# ======================================================================= PPO
class PPO:
    def __init__(self, seed=0, lr=3e-4, hidden=64):
        rng = np.random.default_rng(seed)
        self.sizes = [OBS_DIM, hidden, hidden, ACT_DIM]
        self.pi = MLP(self.sizes, rng, out_scale=0.01)
        self.vf = MLP([OBS_DIM, hidden, hidden, 1], rng, out_scale=1.0)
        self.logstd = np.full(ACT_DIM, -0.5)
        self.norm = RunningNorm(OBS_DIM)
        self.ret_mu, self.ret_sd = 0.0, 1.0           # value net predicts normalised returns
        self.opt_pi = Adam({**self.pi.p, "logstd": self.logstd}, lr)
        self.opt_vf = Adam(self.vf.p, lr)

    def policy_json(self, meta=None):
        m = dict(meta or {}, sizes=self.sizes)
        return policy_to_json(self.pi, self.logstd, self.norm, m)

    def losses_and_grads(self, X, A, LP, ADV, RET, clip=0.2, ent=1e-3, vcoef=0.5):
        n = X.shape[0]
        mu = self.pi.forward(X)
        sd = np.exp(self.logstd)
        z = (A - mu) / sd
        logp = -0.5 * (z ** 2).sum(1) - self.logstd.sum() - 0.5 * ACT_DIM * math.log(2 * math.pi)
        ratio = np.exp(logp - LP)
        s1, s2 = ratio * ADV, np.clip(ratio, 1 - clip, 1 + clip) * ADV
        lpi = -np.minimum(s1, s2).mean() - ent * self.logstd.sum()
        active = (s1 <= s2).astype(float)            # gradient flows where the unclipped term is the min
        dlogp = -(active * ratio * ADV) / n
        gmu = dlogp[:, None] * (z / sd)
        gls = (dlogp[:, None] * (z ** 2 - 1.0)).sum(0) - ent
        gpi = self.pi.backward(gmu)
        gpi["logstd"] = gls
        V = self.vf.forward(X)[:, 0]
        RETn = (RET - self.ret_mu) / self.ret_sd
        lv = vcoef * 0.5 * ((V - RETn) ** 2).mean()
        gv = self.vf.backward((vcoef * (V - RETn) / n)[:, None])
        return lpi, lv, gpi, gv, float((np.abs(ratio - 1) > clip).mean())

    def update(self, X, A, LP, ADV, RET, epochs=10, mb=512, rng=None, max_norm=0.5):
        ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
        # slowly tracked return statistics for the value target
        if not getattr(self, "ret_init", False):
            self.ret_mu, self.ret_sd, self.ret_init = float(RET.mean()), max(1e-3, float(RET.std())), True
        else:
            self.ret_mu = 0.9 * self.ret_mu + 0.1 * float(RET.mean())
            self.ret_sd = max(1e-3, 0.9 * self.ret_sd + 0.1 * float(RET.std()))
        n = X.shape[0]
        stats = []
        for _ in range(epochs):
            idx = rng.permutation(n)
            for s in range(0, n, mb):
                b = idx[s:s + mb]
                lpi, lv, gpi, gv, cf = self.losses_and_grads(X[b], A[b], LP[b], ADV[b], RET[b])
                for g in (gpi, gv):
                    nrm = math.sqrt(sum(float((v ** 2).sum()) for v in g.values()))
                    if nrm > max_norm:
                        for k in g:
                            g[k] *= max_norm / nrm
                params = {**self.pi.p, "logstd": self.logstd}
                self.opt_pi.step(params, gpi)
                self.logstd = np.clip(params["logstd"], -3.0, 1.0)
                self.opt_vf.step(self.vf.p, gv)
                stats.append((lpi, lv, cf))
        return np.mean(stats, axis=0)

    def values(self, X):
        return self.ret_mu + self.ret_sd * self.vf.forward(X)[:, 0]


def gae(rew, val, last_val, gamma=0.95, lam=0.95):
    T = len(rew)
    adv = np.zeros(T)
    g = 0.0
    for t in reversed(range(T)):
        nv = last_val if t == T - 1 else val[t + 1]
        d = rew[t] + gamma * nv - val[t]
        g = d + gamma * lam * g
        adv[t] = g
    return adv, adv + val


def train(a):
    from multiprocessing import Pool
    rng = np.random.default_rng(a.seed)
    agent = PPO(seed=a.seed, lr=a.lr)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    log_path = a.out.replace(".json", "_log.jsonl")
    val_specs = [sample_scenario(np.random.default_rng(9000 + i)) for i in range(a.n_val)]
    best = -1e9
    t0 = time.time()
    with Pool(a.workers) as pool, open(log_path, "a") as flog:
        for it in range(a.iters):
            pj = agent.policy_json(dict(regime=a.regime, iter=it))
            jobs = []
            for e in range(a.episodes):
                sc, lam = sample_scenario(rng)
                jobs.append((pj, sc, lam, int(100000 + it * 1000 + e), a.regime))
            res = [r for r in pool.map(rollout, jobs, chunksize=1) if r is not None]
            # observation normaliser from raw observations of this batch, then normalise
            raw = np.concatenate([r["obs"] for r in res])
            agent.norm.update(raw[rng.choice(len(raw), min(len(raw), 4000), replace=False)])
            Xs, As, LPs, ADVs, RETs, epr = [], [], [], [], [], []
            for r in res:
                X = agent.norm(r["obs"])
                V = agent.values(X)
                adv, ret = gae(r["rew"], V, V[-1], a.gamma, a.gae)
                Xs.append(X); As.append(r["act"]); LPs.append(r["logp"]); ADVs.append(adv); RETs.append(ret)
                epr.append(r["rew"].mean())
            # Workers sampled with the previous input normaliser. PPO's ratio needs pi_old(a|s) under the
            # normaliser used in this update, so pi_old is re-evaluated here with the pre-update weights.
            X = np.concatenate(Xs); A = np.concatenate(As)
            sd_old = np.exp(agent.logstd)
            mu_old = agent.pi.forward(X)
            LP_old = -0.5 * (((A - mu_old) / sd_old) ** 2).sum(1) - agent.logstd.sum() - 0.5 * ACT_DIM * math.log(2 * math.pi)
            st = agent.update(X, A, LP_old, np.concatenate(ADVs), np.concatenate(RETs), epochs=a.epochs,
                              mb=a.minibatch, rng=rng)
            rec = dict(iter=it, episodes=len(res), steps=int(len(X)), mean_reward=float(np.mean(epr)),
                       mean_utility=float(np.mean(epr) / R_SCALE + R_CENTER), loss_pi=float(st[0]),
                       loss_v=float(st[1]), clipfrac=float(st[2]), std=np.exp(agent.logstd).round(3).tolist(),
                       elapsed_min=round((time.time() - t0) / 60, 2))
            if (it + 1) % a.val_every == 0 or it == a.iters - 1:
                pj2 = agent.policy_json(dict(regime=a.regime, iter=it))
                vals = pool.map(evaluate, [(pj2, sc, lam, 9000 + i, a.regime) for i, (sc, lam) in enumerate(val_specs)])
                v = float(np.nanmean(vals))
                rec["val_utility"] = v / R_SCALE + R_CENTER
                if v > best:
                    best = v
                    with open(a.out, "w") as f:
                        json.dump(agent.policy_json(dict(regime=a.regime, iter=it, val_utility=rec["val_utility"],
                                                         episodes_seen=(it + 1) * a.episodes)), f)
                    rec["saved"] = True
            with open(a.out.replace(".json", "_last.json"), "w") as f:
                json.dump(agent.policy_json(dict(regime=a.regime, iter=it)), f)
            flog.write(json.dumps(rec) + "\n"); flog.flush()
            print(json.dumps(rec), flush=True)
    print(f"[drl] done: best validation utility {best / R_SCALE + R_CENTER:.4f}; policy {a.out}", flush=True)


# ======================================================================= checks
def grad_check():
    rng = np.random.default_rng(1)
    ag = PPO(seed=3, hidden=8)
    ag.logstd = rng.normal(-0.3, 0.1, ACT_DIM)
    n = 12
    X = rng.normal(size=(n, OBS_DIM)); A = rng.normal(size=(n, ACT_DIM))
    LP = rng.normal(-3, 0.5, n); ADV = rng.normal(size=n); RET = rng.normal(size=n)
    lpi, lv, gpi, gv, _ = ag.losses_and_grads(X, A, LP, ADV, RET, clip=10.0)   # no clipping: smooth
    worst = 0.0
    for key in ("W0", "b1", "W2"):
        P = ag.pi.p[key]
        for _ in range(5):
            idx = tuple(rng.integers(0, s) for s in P.shape)
            old = P[idx]
            P[idx] = old + 1e-6; l1 = ag.losses_and_grads(X, A, LP, ADV, RET, clip=10.0)[0]
            P[idx] = old - 1e-6; l2 = ag.losses_and_grads(X, A, LP, ADV, RET, clip=10.0)[0]
            P[idx] = old
            num = (l1 - l2) / 2e-6
            worst = max(worst, abs(num - gpi[key][idx]) / max(1e-8, abs(num) + abs(gpi[key][idx])))
    for j in range(ACT_DIM):
        old = ag.logstd[j]
        ag.logstd[j] = old + 1e-6; l1 = ag.losses_and_grads(X, A, LP, ADV, RET, clip=10.0)[0]
        ag.logstd[j] = old - 1e-6; l2 = ag.losses_and_grads(X, A, LP, ADV, RET, clip=10.0)[0]
        ag.logstd[j] = old
        num = (l1 - l2) / 2e-6
        worst = max(worst, abs(num - gpi["logstd"][j]) / max(1e-8, abs(num) + abs(gpi["logstd"][j])))
    for key in ("W0", "W2"):
        P = ag.vf.p[key]
        for _ in range(5):
            idx = tuple(rng.integers(0, s) for s in P.shape)
            old = P[idx]
            P[idx] = old + 1e-6; l1 = ag.losses_and_grads(X, A, LP, ADV, RET)[1]
            P[idx] = old - 1e-6; l2 = ag.losses_and_grads(X, A, LP, ADV, RET)[1]
            P[idx] = old
            num = (l1 - l2) / 2e-6
            worst = max(worst, abs(num - gv[key][idx]) / max(1e-8, abs(num) + abs(gv[key][idx])))
    print(f"[drl] gradient check: worst relative error {worst:.2e}")
    return worst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--regime", choices=["loop", "twin", "prior"], required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=os.cpu_count())
    p.add_argument("--iters", type=int, default=150)
    p.add_argument("--episodes", type=int, default=40, help="episodes per iteration")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--minibatch", type=int, default=512)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--gamma", type=float, default=0.95)
    p.add_argument("--gae", type=float, default=0.95)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-val", type=int, default=16)
    p.add_argument("--val-every", type=int, default=10)
    sub.add_parser("smoke")
    a = ap.parse_args()
    if a.cmd == "train":
        train(a)
    else:
        assert grad_check() < 1e-4
        class A_:
            pass
        aa = A_()
        aa.regime, aa.out, aa.workers, aa.iters, aa.episodes = "twin", "/tmp/drl_smoke.json", 2, 2, 2
        aa.epochs, aa.minibatch, aa.lr, aa.gamma, aa.gae, aa.seed, aa.n_val, aa.val_every = 2, 128, 3e-4, 0.95, 0.95, 0, 2, 1
        train(aa)


if __name__ == "__main__":
    main()
