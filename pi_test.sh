#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f .venv/bin/python ]]; then
  echo "Missing virtual environment at .venv." >&2
  echo "Run ./pi_setup.sh first, then rerun ./pi_test.sh." >&2
  exit 1
fi

EXAMPLE_SCRIPT="third_party/e-Paper/RaspberryPi_JetsonNano/python/examples/epd_7in5_V2_test.py"
if [[ ! -f "$EXAMPLE_SCRIPT" ]]; then
  echo "Missing Waveshare example: $EXAMPLE_SCRIPT" >&2
  echo "Run: git submodule update --init --recursive" >&2
  exit 1
fi

source .venv/bin/activate
python "$EXAMPLE_SCRIPT"