"""Longer real-player runs (600 s) to test EchoSlice with a longer hold and a longer scoring window."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results600"); os.makedirs(OUT, exist_ok=True)
CFG = [("static-0.7", ["--slicer", "static", "--x", "0.7"]), ("static-0.8", ["--slicer", "static", "--x", "0.8"]),
       ("static-0.9", ["--slicer", "static", "--x", "0.9"]), ("prior", ["--slicer", "prior"]),
       ("echoslice-h36", ["--slicer", "echoslice", "--hold", "36", "--settle", "12"]),
       ("prior-rho0.5", ["--slicer", "prior", "--rho", "1.5e6"]),
       ("echoslice-h36-rho0.5", ["--slicer", "echoslice", "--hold", "36", "--settle", "12", "--rho", "1.5e6"])]
SEEDS = [1, 2]
done = set()
for f in os.listdir(OUT):
    if f.endswith(".jsonl"):
        for l in open(os.path.join(OUT, f)):
            r = json.loads(l); done.add((r["tag"], r["seed"]))
for s in SEEDS:
    for t, a in CFG:
        if (t, s) in done:
            continue
        cmd = [sys.executable, os.path.join(HERE, "testbed.py"), *a, "--tag", t, "--seed", str(s), "--T", "600",
               "--t_eval0", "60", "--port", "8095", "--out", os.path.join(OUT, "runs.jsonl")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
        print(t, s, (p.stdout.strip().splitlines() or ["?"])[-1][:160], p.stderr[-300:] if p.returncode else "", flush=True)
