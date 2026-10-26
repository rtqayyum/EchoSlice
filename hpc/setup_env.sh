#!/bin/bash
# Create or refresh the project-local Python environment for EchoSlice.
#
#   bash /home/USER/echoslice/hpc/setup_env.sh
#
# Run it once on a login node (pip needs internet). Batch calls it again at the
# start of every job; it returns at once when the environment is already built.
# Everything goes under the project root. The shared Conda at
# /cm/shared/apps/anaconda3 is only used to provide a base python; nothing is
# installed into it.
set -Eeuo pipefail

ROOT="${ES_ROOT:-/home/USER/echoslice}"
VENV="$ROOT/.venv"
STAMP="$VENV/.echoslice_ready"
LOCK="$ROOT/.env_lock"

export PIP_CACHE_DIR="$ROOT/.cache/pip"
export XDG_CACHE_HOME="$ROOT/.cache/xdg"
export TMPDIR="$ROOT/tmp"
export PYTHONNOUSERSITE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" "$TMPDIR" "$ROOT/results" "$ROOT/logs"

want=$(cat "$ROOT/requirements.txt" "$ROOT"/vendor/*.whl | sha256sum | cut -c1-16)
ready() { [[ -x "$VENV/bin/python" && -f "$STAMP" && "$(cat "$STAMP")" == "$want" ]]; }
if ready; then
  echo "[env] ready: $VENV ($("$VENV/bin/python" --version 2>&1))"
  exit 0
fi

# one builder at a time (mkdir is atomic on NFS)
for _ in $(seq 1 180); do
  if mkdir "$LOCK" 2>/dev/null; then break; fi
  echo "[env] another job is building the environment, waiting..."
  sleep 10
done
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
if ready; then echo "[env] ready: $VENV"; exit 0; fi

# base python from the cluster module (read-only use)
if ! command -v module >/dev/null 2>&1; then
  for f in /etc/profile.d/modules.sh /etc/profile.d/lmod.sh /usr/share/lmod/lmod/init/bash /etc/profile.d/z00_lmod.sh; do
    if [[ -f "$f" ]]; then set +u; source "$f"; set -u; break; fi
  done
fi
if command -v module >/dev/null 2>&1; then
  set +u; module load anaconda3 || echo "[env] warning: 'module load anaconda3' failed, using python3 on PATH"; set -u
fi
BASE_PY="${ES_BASE_PYTHON:-$(command -v python3)}"
echo "[env] base python: $BASE_PY ($("$BASE_PY" --version 2>&1))"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$BASE_PY" -m venv "$VENV"
fi
VPY="$VENV/bin/python"
case "$("$VPY" -c 'import sys; print(sys.prefix)')" in
  "$ROOT"/*) ;;
  *) echo "[env] ERROR: venv prefix is outside $ROOT"; exit 1 ;;
esac

"$VPY" -m pip install --upgrade pip setuptools wheel
"$VPY" -m pip install -r "$ROOT/requirements.txt"
"$VPY" -m pip install --no-deps "$ROOT"/vendor/itu_p1203-*.whl
if ! "$VPY" -m pip install "polars-lts-cpu>=1.0,<2"; then
  echo "[env] polars-lts-cpu unavailable, installing polars"
  "$VPY" -m pip install "polars>=1.0"
fi

"$VPY" - <<'PY'
import numpy, scipy, pandas, numba, matplotlib, pyarrow, polars, sklearn, tabulate, itu_p1203
print("[env] imports ok:", "numpy", numpy.__version__, "| numba", numba.__version__, "| pandas", pandas.__version__,
      "| polars", polars.__version__, "| matplotlib", matplotlib.__version__)
PY
"$VPY" -m pip freeze > "$ROOT/results/env_freeze.txt"
echo "$want" > "$STAMP"
echo "[env] built: $VENV"
