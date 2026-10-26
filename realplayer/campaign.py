"""Run the real-player campaign: every configuration x seeds, three testbeds in parallel (separate ports)."""
import itertools, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import threading
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results"); os.makedirs(OUT, exist_ok=True)
CFG = [("static-0.%d" % i, ["--slicer", "static", "--x", "0.%d" % i]) for i in range(5, 10)]
CFG += [("usage", ["--slicer", "usage"]), ("forecast+10%", ["--slicer", "forecast", "--h", "0.1"]),
        ("forecast+30%", ["--slicer", "forecast", "--h", "0.3"]),
        ("prior", ["--slicer", "prior"]), ("echoslice", ["--slicer", "echoslice"]),
        ("prior-rho0.5", ["--slicer", "prior", "--rho", "1.5e6"]), ("echoslice-rho0.5", ["--slicer", "echoslice", "--rho", "1.5e6"])]
SEEDS = [int(s) for s in (sys.argv[1] if len(sys.argv) > 1 else "1,2,3").split(",")]
done = set()
for f in os.listdir(OUT):
    if f.endswith(".jsonl"):
        for l in open(os.path.join(OUT, f)):
            r = json.loads(l); done.add((r["tag"], r["seed"]))
todo = [(t, a, s) for s in SEEDS for t, a in CFG if (t, s) not in done]
ports = iter(range(8091, 8200))
lock = threading.Lock()
slots = [8091]
free = list(slots)
def run(item):
    t, a, s = item
    with lock:
        port = free.pop()
    try:
        cmd = [sys.executable, os.path.join(HERE, "testbed.py"), *a, "--tag", t, "--seed", str(s), "--T", "240",
               "--t_eval0", "60", "--port", str(port), "--out", os.path.join(OUT, f"runs_{port}.jsonl")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        print(t, s, (p.stdout.strip().splitlines() or ["?"])[-1][:200], p.stderr[-300:] if p.returncode else "", flush=True)
    finally:
        with lock:
            free.append(port)
print(len(todo), "runs to do", flush=True)
with ThreadPoolExecutor(1) as ex:
    list(ex.map(run, todo))
