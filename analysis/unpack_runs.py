"""Unpack the released runs into the folder layout the campaign code expects.

  python analysis/unpack_runs.py <work dir>

For each results/final/runs/<EXP>.jsonl.gz this writes
  <work dir>/results/<EXP>/parts/released.jsonl   (the runs, one JSON record per line)
  <work dir>/results/<EXP>/jobs.json              (the job list, rebuilt from the records)
and copies the PPO policies to <work dir>/policies,
so that `python -m experiments.campaign status|report --root <work dir>` works on the released data.
"""
import glob
import gzip
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    work = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "work"))
    groups = {}
    for f in sorted(glob.glob(os.path.join(HERE, "results", "final", "runs", "*.jsonl.gz"))):
        exp = os.path.basename(f).split(".")[0].split("_part")[0]   # large experiments are split into parts
        groups.setdefault(exp, []).append(f)
    for exp, files in groups.items():
        d = os.path.join(work, "results", exp)
        os.makedirs(os.path.join(d, "parts"), exist_ok=True)
        jobs = []
        with open(os.path.join(d, "parts", "released.jsonl"), "w") as dst:
            for f in files:
                with gzip.open(f, "rt") as src:
                    for line in src:
                        dst.write(line)
                        jobs.append(json.loads(line)["job"])
        json.dump(jobs, open(os.path.join(d, "jobs.json"), "w"))
        print(f"{exp}: {len(jobs)} runs")
    pol = os.path.join(HERE, "results", "final", "policies")
    if os.path.isdir(pol):                      # PPO policies and training logs, for the learning-curve figure
        shutil.copytree(pol, os.path.join(work, "policies"), dirs_exist_ok=True)
    print("unpacked into", work)


if __name__ == "__main__":
    main()
