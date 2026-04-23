"""System integration helpers."""

from __future__ import annotations

import subprocess


def get_wifi_ssid(*, emulate: bool, test_wifi: bool = False) -> str | None:
    """Return current Wi-Fi SSID on Linux hardware.

    Emulation mode intentionally reports no Wi-Fi so the dashboard keeps its
    current placeholder behaviour unless `--test-wifi` is supplied.
    """
    if emulate:
        return "TestNetwork" if test_wifi else None

    try:
        process = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "TestNetwork" if test_wifi else None

    ssid = process.stdout.strip()
    return ssid if ssid else ("TestNetwork" if test_wifi else None)
