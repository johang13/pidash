#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Missing virtual environment at .venv." >&2
  echo "Run ./pi_setup.sh first, then rerun ./pi_run.sh." >&2
  exit 1
fi

source .venv/bin/activate
python main.py