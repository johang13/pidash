"""Application bootstrap"""

from __future__ import annotations
import argparse
import logging
import platform
import sys

from .dashboard import Dashboard
from .display import DisplayLoadError, load_display
from .settings import AppSettings
from .weather import OpenMeteoClient

logger = logging.getLogger(__name__)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PiDash - A weather dashboard for Raspberry Pi")
    parser.add_argument(
        "--emulate",
        action="store_true",
        help="Force desktop emulation mode, even on Linux hardware."
    )

    parser.add_argument(
        "--test-wifi",
        action="store_true",
        help="Show a dummy Wi-Fi network name, even when hardware Wi-Fi is available."
    )

    return parser.parse_args(argv)

def build_settings(args: argparse.Namespace) -> AppSettings:
    """Build app settings object from command line arguments."""
    # no way to reliably determine if running on a Pi
    # We'll just assume that if it's not Darwin or Windows, it's a Pi
    emulate = args.emulate or platform.system() != "Linux"

    # Wi-Fi SSID retrieval is a bit buggy sometimes so force test_wifi for emulated environments
    test_wifi = args.test_wifi or emulate
    return AppSettings(emulate=emulate, test_wifi=test_wifi)

def main(argv: list[str] | None = None) -> int:
    """Main entry point for PiDash."""
    logging.basicConfig(level=logging.DEBUG)

    args = parse_args(argv)
    settings = build_settings(args)

    try:
        epd = load_display(settings)
    except DisplayLoadError as exc:
        logger.error("%s", exc)
        return 1

    weather_client = OpenMeteoClient.from_settings(settings)
    dashboard = Dashboard(epd=epd, settings=settings, weather_client=weather_client)

    try:
        dashboard.run_forever()
    except IOError as exc:
        logger.info(exc)
        return 1
    except KeyboardInterrupt:
        logger.info("keyboard interrupt, exiting")
        return 0
    finally:
        logger.info("exiting")
        if hasattr(epd, "epdconfig"):
            epd.epdconfig.module_exit(cleanup=True)

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
