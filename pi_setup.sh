#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -c /dev/spidev0.0 && ! -c /dev/spidev0.1 ]]; then
  echo "SPI appears to be disabled (no /dev/spidev0.* device found)." >&2
  echo "Enable SPI in raspi-config, reboot, then run this script again." >&2
  echo "Example: sudo raspi-config nonint do_spi 0 && sudo reboot" >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# If this repo uses submodules (you do for Waveshare), ensure they are present
git submodule update --init --recursive

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[rpi]"