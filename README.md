# PiDash

Minimal Python scaffold for a Waveshare e-Paper app.

## Quick start (macOS/dev)

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python main.py
```

## Raspberry Pi install

You must have enabled SPI on the Pi:

```bash
sudo raspi-config
# Choose Interfacing Options -> SPI -> Yes Enable SPI interface
```

Then reboot.

The `pi_run.sh` script is a convenience for installing and running on the Pi:

```bash
chmod +x pi_run.sh
./pi_run.sh
```

`pi_run.sh` installs system prerequisites, initializes submodules, creates `.venv`, installs `.[rpi]`, and runs `main.py`.

## Notes

- The Waveshare repo is expected at `third_party/e-Paper`.
- For your panel, use `waveshare_epd.epd7in5_V2` in hardware mode.
- Raspberry Pi extras come from `pyproject.toml` via `.[rpi]`.



