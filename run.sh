#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Missing virtual environment at .venv." >&2
  echo "Run ./setup.sh first, then rerun ./run.sh." >&2
  exit 1
fi

source .venv/bin/activate
pidash
