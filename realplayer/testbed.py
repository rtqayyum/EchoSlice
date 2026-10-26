"""Real-player check of the feedback loop: real dash.js players (headless Chromium) and greedy TCP bulk
downloads share one paced bottleneck that is split into a video slice and a bulk slice (strict mode).
A slicer sets the two shares every second from what it measures, as an xApp would.

  python testbed.py --slicer echoslice --seed 1 --out runs.jsonl [--T 240 --C 16e6 --players 4 --bulk 2]

Slicers: static (with --x), usage, forecast (with --h), prior, echoslice.
Nothing here is simulated: the players run dash.js 4.7.4 with its default ABR (DYNAMIC), segments are real
H.264 files, and every byte goes through the pacing scheduler over loopback TCP.
"""
import argparse
import asyncio
import json
import math
import os
import random
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(HERE, "www")
sys.path.insert(0, os.path.dirname(HERE))
from sim import qoe  # noqa: E402

LADDER_BPS = [300e3, 750e3, 1200e3, 2000e3, 3000e3, 4500e3]
LADDER_RES = ["320x180", "480x270", "640x360", "640x360", "854x480", "854x480"]
SIM_LEVEL = [1, 2, 3, 4, 5, 6]          # nearest rung of the simulator's ladder (for the online MOS table)
TICK = 0.005
CHUNK = 16384
XMIN, XMAX = 0.05, 0.95


# ------------------------------------------------------------------------------------------ bottleneck
class Conn:
    def __init__(self, sl, who):
        self.sl, self.who = sl, who
        self.allow = 0.0
        self.pending = 0
        self.ev = asyncio.Event()


class Bottleneck:
    """Strict two-slice scheduler: each slice gets x_k * C, split equally over its backlogged connections.
    Capacity a slice does not use stays idle (strict mode)."""

    QCAP = 65536      # the RAN sees only what TCP has sent: at most this much waits per connection

    def queued(self, sl):
        return sum(min(c.pending, self.QCAP) for c in self.conns if c.sl == sl)

    def __init__(self, C):
        self.C = C
        self.q_prev = {"video": 0.0, "bulk": 0.0}
        self.x = {"video": 0.5, "bulk": 0.5}
        self.conns = set()
        self.served = {"video": 0.0, "bulk": 0.0}       # bytes in the current slicer period
        self.offered = {"video": 0.0, "bulk": 0.0}      # bytes requested in the current slicer period

    async def run(self):
        last = time.monotonic()
        while True:
            await asyncio.sleep(TICK)
            now = time.monotonic()
            dt, last = now - last, now
            for sl in ("video", "bulk"):
                act = [c for c in self.conns if c.sl == sl and c.pending > 0]
                if not act:
                    continue
                share = self.x[sl] * self.C / 8.0 * dt / len(act)
                for c in act:
                    c.allow = min(c.allow + share, 4 * share + CHUNK)
                    c.ev.set()

    async def send(self, conn, writer, data_len, data_src):
        conn.pending = data_len
        sent = 0
        while sent < data_len:
            if conn.allow < 1:
                conn.ev.clear()
                await conn.ev.wait()
            n = int(min(conn.allow, CHUNK, data_len - sent))
            if n <= 0:
                continue
            writer.write(data_src(sent, n))
            await writer.drain()
            conn.allow -= n
            sent += n
            conn.pending = data_len - sent
            self.served[conn.sl] += n
        conn.pending = 0
        conn.allow = 0.0


ZERO = bytes(CHUNK)


class Server:
    def __init__(self, bn, log):
        self.bn, self.log = bn, log
        self.stats = {}            # player -> list of stat dicts
        self.segs = {}             # player -> list of (t_done, stream, idx)
        self.cache = {}
        self.t0 = time.monotonic()

    def now(self):
        return time.monotonic() - self.t0

    def file(self, path):
        if path not in self.cache:
            with open(path, "rb") as f:
                self.cache[path] = f.read()
        return self.cache[path]

    async def handle(self, reader, writer):
        try:
            while True:
                head = await reader.readuntil(b"\r\n\r\n")
                lines = head.decode("latin1").split("\r\n")
                method, path, _ = lines[0].split(" ", 2)
                hdr = {k.lower(): v for k, v in (l.split(": ", 1) for l in lines[1:] if ": " in l)}
                body = b""
                if "content-length" in hdr:
                    body = await reader.readexactly(int(hdr["content-length"]))
                await self.route(method, path, body, writer)
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def respond(self, writer, code, ctype, data=b"", length=None, paced=None):
        n = len(data) if length is None else length
        writer.write((f"HTTP/1.1 {code} OK\r\nContent-Type: {ctype}\r\nContent-Length: {n}\r\n"
                      "Access-Control-Allow-Origin: *\r\nCache-Control: no-store\r\nConnection: keep-alive\r\n\r\n").encode())
        if paced is None:
            writer.write(data)
            await writer.drain()
            return
        sl, who = paced
        c = Conn(sl, who)
        self.bn.conns.add(c)
        try:
            src = (lambda a, k: data[a:a + k]) if data else (lambda a, k: ZERO[:k])
            await self.bn.send(c, writer, n, src)
        finally:
            self.bn.conns.discard(c)

    async def route(self, method, path, body, writer):
        if method == "POST" and path.startswith("/stats"):
            p = int(re.search(r"p=(\d+)", path).group(1))
            d = json.loads(body or b"{}")
            d["t"] = self.now()
            self.stats.setdefault(p, []).append(d)
            await self.respond(writer, 200, "text/plain", b"ok")
            return
        if path.startswith("/bulk"):
            await self.respond(writer, 200, "application/octet-stream", length=10 ** 11, paced=("bulk", path))
            return
        m = re.match(r"/p(\d+)/video/(.*)", path)
        if m:
            p, name = int(m.group(1)), m.group(2).split("?")[0]
            fp = os.path.join(WWW, "video", name)
            data = self.file(fp)
            if name.endswith(".mpd"):
                await self.respond(writer, 200, "application/dash+xml", data)
                return
            mm = re.match(r"chunk-stream(\d+)-(\d+)\.m4s", name)
            if mm:
                await self.respond(writer, 200, "video/mp4", data, paced=("video", p))
                self.segs.setdefault(p, []).append((self.now(), int(mm.group(1)), int(mm.group(2))))
                return
            await self.respond(writer, 200, "video/mp4", data)
            return
        fp = os.path.join(WWW, path.lstrip("/").split("?")[0])
        if os.path.isfile(fp):
            ct = "text/html" if fp.endswith(".html") else "application/javascript"
            await self.respond(writer, 200, ct, self.file(fp))
            return
        await self.respond(writer, 404, "text/plain", b"no")


# ------------------------------------------------------------------------------------------ QoE estimates
def video_mos_window(srv, p, t0, t1):
    segs = [s for s in srv.segs.get(p, []) if t0 <= s[0] < t1]
    lv = [SIM_LEVEL[s[1]] for s in segs]
    st = srv.stats.get(p, [])
    w = [d for d in st if t0 <= d["t"] < t1]
    stall_time = sum(1.0 for d in w if d.get("stalled"))       # stats arrive once per second
    n_stalls = sum(1 for a, b in zip(w, w[1:]) if b.get("stalled") and not a.get("stalled"))
    return qoe.video_proxy(lv, stall_time, n_stalls, t1 - t0, "pc")


class BulkMeter:
    def __init__(self):
        self.bytes = {}
        self.hist = []      # (t, {id: bytes})

    def snap(self, t):
        self.hist.append((t, dict(self.bytes)))

    def rate(self, i, t0, t1):
        a = [h for h in self.hist if h[0] <= t0]
        b = [h for h in self.hist if h[0] <= t1]
        if not a or not b:
            return 0.0
        return 8.0 * (b[-1][1].get(i, 0) - a[-1][1].get(i, 0)) / max(b[-1][0] - a[-1][0], 1e-6)


def utility(srv, meter, n_play, n_bulk, t0, t1):
    m = [video_mos_window(srv, p, t0, t1) for p in range(n_play)]
    m += [float(qoe.bulk_mos(meter.rate(i, t0, t1))) for i in range(n_bulk)]
    return float(np.mean(m))


# ------------------------------------------------------------------------------------------ slicers
def project2(xv):
    xv = min(max(xv, XMIN), XMAX)
    return {"video": xv, "bulk": 1.0 - xv}


class Slicer:
    def __init__(self, kind, args, n_play, n_bulk, rng):
        self.kind, self.a, self.n_play, self.n_bulk, self.rng = kind, args, n_play, n_bulk, rng
        self.u = None
        self.f = None
        self.theta = 0.0
        self.k = 0
        self.phase, self.t_phase, self.Up, self.delta = 0, 0.0, 0.0, 1.0
        self.hist = []

    def prior(self, theta):
        return project2(self.n_play * self.a.rho * math.exp(theta) / self.a.C)

    def decide(self, t, bn, srv, meter, per):
        k = self.kind
        if k == "static":
            return project2(self.a.x)
        if k == "usage":
            u = np.array([bn.served["video"], bn.served["bulk"]]) / max(per, 1e-6) + 1.0
            self.u = u if self.u is None else 0.5 * self.u + 0.5 * u
            return project2(self.u[0] / self.u.sum())
        if k == "forecast":
            o = bn.offered["video"] * 8.0 / max(per, 1e-6)
            self.f = o if self.f is None else 0.7 * self.f + 0.3 * o
            return project2(self.f * (1 + self.a.h) / self.a.C)
        if k == "prior":
            return self.prior(0.0)
        if k == "echoslice":
            c = 0.15 / (self.k + 1) ** 0.101
            if t < 30.0:
                self.t_phase = t
                self.cur = self.prior(0.0)
                return self.cur
            if not getattr(self, "started", False):
                self.started = True
                self.t_phase = t
                self.cur = self.prior(self.theta + c * self.delta)
                return self.cur
            if t - self.t_phase < self.a.hold:
                return self.cur
            U = utility(srv, meter, self.n_play, self.n_bulk, t - (self.a.hold - self.a.settle), t) \
                + self.rng.gauss(0, 0.02)
            self.t_phase = t
            if self.phase == 0:
                self.Up, self.phase = U, 1
                self.cur = self.prior(self.theta - c * self.delta)
                return self.cur
            g = (self.Up - U) / (2 * c) * self.delta
            a = 0.6 / (self.k + 6) ** 0.602
            step = float(np.clip(a * g, -0.3, 0.3))
            self.theta = float(np.clip(self.theta + step, -1.5, 1.5))
            self.k += 1
            self.hist.append((round(t, 1), round(self.theta, 4), round(self.Up, 3), round(U, 3)))
            self.delta = self.rng.choice([-1.0, 1.0])
            self.phase = 0
            self.cur = self.prior(self.theta + c * self.delta)
            return self.cur
        raise ValueError(k)


# ------------------------------------------------------------------------------------------ run
PAGE = """<!doctype html><html><body><video id="v" muted autoplay playsinline width="320"></video>
<script src="/dashjs/dash.all.min.js"></script><script>
const P = {P}; const v = document.getElementById('v');
const pl = dashjs.MediaPlayer().create();
pl.updateSettings({streaming: {buffer: {fastSwitchEnabled: false}}});
pl.initialize(v, '/p' + P + '/video/manifest.mpd', true);
let stalled = true, started = false;
pl.on(dashjs.MediaPlayer.events.PLAYBACK_WAITING, () => { stalled = true; });
pl.on(dashjs.MediaPlayer.events.PLAYBACK_PLAYING, () => { stalled = false; started = true; });
pl.on(dashjs.MediaPlayer.events.PLAYBACK_STALLED, () => { stalled = true; });
setInterval(() => {
  let q = -1, b = 0; try { q = pl.getQualityFor('video'); b = pl.getBufferLength('video'); } catch (e) {}
  fetch('/stats?p=' + P, {method: 'POST', body: JSON.stringify({q: q, buf: b, stalled: stalled, started: started,
        media: v.currentTime})}).catch(() => {});
}, 1000);
</script></body></html>"""


async def bulk_client(port, i, meter, stop):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(f"GET /bulk?i={i} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
    await w.drain()
    await r.readuntil(b"\r\n\r\n")
    meter.bytes[i] = 0
    while not stop.is_set():
        d = await r.read(65536)
        if not d:
            break
        meter.bytes[i] += len(d)
    w.close()


def p1203_player(srv, p, t0, t1):
    from itu_p1203 import P1203Standalone
    qoe._quiet()
    segs = sorted(srv.segs.get(p, []), key=lambda s: s[2])
    st = srv.stats.get(p, [])
    # play order: segment index; keep the segments whose media time falls in the scoring window
    w = [d for d in st if t0 <= d["t"] < t1]
    if not w:
        return 1.0, {}
    m0, m1 = w[0].get("media", 0.0), w[-1].get("media", 0.0)
    play = [s for s in segs if m0 <= (s[2] - 1) * 4.0 < m1]
    if not play:
        return 1.0, {}
    sg, t = [], 0.0
    for s in play:
        sg.append({"bitrate": LADDER_BPS[s[1]] / 1e3, "codec": "h264", "duration": 4.0, "fps": 25.0,
                   "resolution": LADDER_RES[s[1]], "start": t})
        t += 4.0
    stalls = [[0.0, 0.0]]
    run = 0
    for a, b in zip(w, w[1:]):
        if b.get("stalled") and b.get("started"):
            run += 1
        elif run:
            stalls.append([max(0.0, b["media"] - m0), float(run)])
            run = 0
    inp = {"I11": {"segments": [{"bitrate": 128, "codec": "aaclc", "duration": t, "start": 0}], "streamId": 1},
           "I13": {"segments": sg, "streamId": 1}, "I23": {"stalling": stalls, "streamId": 1},
           "IGen": {"device": "pc", "displaySize": "1920x1080", "viewingDistance": "150cm"}}
    mos = float(P1203Standalone(inp).calculate_complete()["O46"])
    stall_s = sum(s[1] for s in stalls)
    br = float(np.mean([LADDER_BPS[s[1]] for s in play])) / 1e6
    return mos, dict(stall_s=stall_s, n_stalls=len(stalls) - 1, mean_mbps=br, n_segs=len(play))


async def main(a):
    from playwright.async_api import async_playwright
    rng = random.Random(a.seed)
    np.random.seed(a.seed)
    bn = Bottleneck(a.C)
    srv = Server(bn, None)
    meter = BulkMeter()
    os.makedirs(os.path.join(WWW, "pages"), exist_ok=True)
    for p in range(a.players):
        with open(os.path.join(WWW, "pages", f"p{p}.html"), "w") as f:
            f.write(PAGE.replace("{P}", str(p)))
    server = await asyncio.start_server(srv.handle, "127.0.0.1", a.port)
    sched = asyncio.create_task(bn.run())
    stop = asyncio.Event()
    sl = Slicer(a.slicer, a, a.players, a.bulk, rng)
    sl.cur = sl.prior(0.0)
    trace = []
    async with async_playwright() as pw:
        br = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--disable-gpu",
                                            "--mute-audio", "--disable-background-timer-throttling", "--disk-cache-size=1",
                                            "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"])
        pages = []
        srv.t0 = time.monotonic()
        bulks = [asyncio.create_task(bulk_client(a.port, i, meter, stop)) for i in range(a.bulk)]
        for p in range(a.players):
            ctx = await br.new_context()
            pg = await ctx.new_page()
            await pg.goto(f"http://127.0.0.1:{a.port}/pages/p{p}.html")
            pages.append(pg)
            await asyncio.sleep(rng.uniform(0.2, 1.0))
        t_last = srv.now()
        while srv.now() < a.T:
            await asyncio.sleep(1.0)
            t = srv.now()
            per = t - t_last
            t_last = t
            meter.snap(t)
            for k in ("video", "bulk"):           # offered = served + growth of the (capped) per-flow queue
                qn = bn.queued(k)
                bn.offered[k] = bn.served[k] + qn - bn.q_prev[k]
                bn.q_prev[k] = qn
            x = sl.decide(t, bn, srv, meter, per)
            trace.append([round(t, 2), round(x["video"], 4), round(bn.served["video"] * 8 / per / 1e6, 3),
                          round(bn.served["bulk"] * 8 / per / 1e6, 3), round(bn.offered["video"] * 8 / per / 1e6, 3)])
            bn.x = x
            bn.served = {"video": 0.0, "bulk": 0.0}
            bn.offered = {"video": 0.0, "bulk": 0.0}
        stop.set()
        res_v = [p1203_player(srv, p, a.t_eval0, a.T) for p in range(a.players)]
        res_b = [float(qoe.bulk_mos(meter.rate(i, a.t_eval0, a.T))) for i in range(a.bulk)]
        rb = [meter.rate(i, a.t_eval0, a.T) / 1e6 for i in range(a.bulk)]
        await br.close()
    for b in bulks:
        b.cancel()
    sched.cancel()
    server.close()
    ev = [r for r in trace if r[0] >= a.t_eval0]
    out = dict(slicer=a.slicer, tag=a.tag or a.slicer, seed=a.seed, x=a.x, h=a.h, C=a.C, T=a.T, t_eval0=a.t_eval0,
               players=a.players, bulk=a.bulk, rho=a.rho,
               mos_video=[r[0] for r in res_v], video_detail=[r[1] for r in res_v], mos_bulk=res_b, bulk_mbps=rb,
               mos_user=float(np.mean([r[0] for r in res_v] + res_b)),
               share_video_mean=float(np.mean([r[1] for r in ev])), served_video_mbps=float(np.mean([r[2] for r in ev])),
               served_bulk_mbps=float(np.mean([r[3] for r in ev])), trace=trace, spsa=sl.hist,
               loadavg=list(os.getloadavg()))
    with open(a.out, "a") as f:
        f.write(json.dumps(out) + "\n")
    print(json.dumps({k: out[k] for k in ("tag", "seed", "mos_user", "mos_video", "mos_bulk", "share_video_mean",
                                          "served_video_mbps", "served_bulk_mbps")}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slicer", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--x", type=float, default=0.5)
    ap.add_argument("--h", type=float, default=0.2)
    ap.add_argument("--rho", type=float, default=3.0e6)
    ap.add_argument("--hold", type=float, default=12.0)
    ap.add_argument("--settle", type=float, default=6.0)
    ap.add_argument("--C", type=float, default=16e6)
    ap.add_argument("--T", type=float, default=240.0)
    ap.add_argument("--t_eval0", type=float, default=60.0)
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--bulk", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--out", default=os.path.join(HERE, "runs.jsonl"))
    asyncio.run(main(ap.parse_args()))
