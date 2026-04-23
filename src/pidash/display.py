"""Display backend loading"""

import importlib
import sys
from typing import Any

from .emulator import MockEPD7in5V2
from .settings import AppSettings

class DisplayLoadError(RuntimeError):
    """Raised when the requested display backend cannot be loaded."""

EPD = Any


def load_display(settings: AppSettings) -> EPD:
    """Load the display backed.
    Automatically returns the appropriate display backend, either emulated or real."""
    if settings.emulate:
        return MockEPD7in5V2()

    lib_dir = str(settings.waveshare_lib_dir)
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)

    try:
        module = importlib.import_module("waveshare_epd.epd7in5_V2")
    except ModuleNotFoundError as exc:
        raise DisplayLoadError(
            "Waveshare library not found. Ensure `third_party/e-Paper` is initialized."
        ) from exc

    return module.EPD()
