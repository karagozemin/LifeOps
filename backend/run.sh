#!/usr/bin/env bash
# LifeOps backend launcher (resilient version)
set -e

cd "$(dirname "$0")"

# --- 1) Pick a stable Python interpreter -------------------------------------
# Python 3.14 fails during venv/ensurepip. Prefer stable releases.
PYBIN=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")"
    case "$ver" in
      3.14|3.15) continue ;;   # skip these versions
      3.*) PYBIN="$cand"; break ;;
    esac
  fi
done

if [ -z "$PYBIN" ]; then
  echo "No stable Python 3.10-3.13 found."
  echo "  Install:  brew install python@3.12"
  exit 1
fi
echo "-> using Python: $($PYBIN --version) ($PYBIN)"

# --- 2) Clean a broken/half .venv --------------------------------------------
if [ -d ".venv" ] && [ ! -x ".venv/bin/python" ]; then
  echo "-> cleaning broken .venv..."
  rm -rf .venv
fi

# --- 3) Create venv (manual bootstrap if ensurepip fails) --------------------
if [ ! -d ".venv" ]; then
  echo "-> creating virtual environment..."
  if ! "$PYBIN" -m venv .venv 2>/dev/null; then
    echo "-> ensurepip failed, creating pip-less venv + manual bootstrap..."
    rm -rf .venv
    "$PYBIN" -m venv --without-pip .venv
    source .venv/bin/activate
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python /tmp/get-pip.py
  else
    source .venv/bin/activate
  fi
else
  source .venv/bin/activate
fi

# --- 4) Dependencies ---------------------------------------------------------
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

# --- 4b) Load .env into the shell too (belt-and-suspenders) ------------------
# app/__init__.py also loads it via python-dotenv, but exporting here guarantees
# the vars are present even if the dotenv import is skipped for any reason.
if [ -f .env ]; then
  echo "-> loading backend/.env"
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# --- 5) Launch ---------------------------------------------------------------
echo "-> LifeOps backend on http://localhost:8000"
echo "  (without OPENAI_API_KEY the deterministic fallback is active - demo still works)"
exec uvicorn app.main:app --reload --port 8000
