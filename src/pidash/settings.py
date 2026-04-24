"""Application settings"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent
THIRD_PARTY_DIR = PROJECT_ROOT / "third_party"
FONTS_DIR = PACKAGE_ROOT / "assets" / "fonts"
WAVESHARE_LIB_DIR = (
    THIRD_PARTY_DIR / "e-Paper" / "RaspberryPi_JetsonNano" / "python" / "lib"
)

@dataclass(frozen=True)
class LocationSettings:
    """Geographic and timezone settings"""
    latitude: float = -36.7724098
    longitude: float = 174.7637373
    timezone: str = "Pacific/Auckland"
    suburb: str = ""


@dataclass(frozen=True)
class AppSettings:
    """Application settings"""
    emulate: bool
    test_wifi: bool = False
    suburb: str = ""
    location: LocationSettings = LocationSettings()
    current_conditions_interval: int = 900
    full_refresh_interval: int = 3600
    loop_sleep_seconds: int = 10
    weather_cache_seconds: int = 60
    hourly_forecast_hours: int = 9

    @property
    def latitude(self) -> float:
        """Latitude"""
        return self.location.latitude

    @property
    def longitude(self) -> float:
        """Longitude"""
        return self.location.longitude

    @property
    def timezone(self) -> str:
        """Timezone"""
        return self.location.timezone

    @property
    def display_suburb(self) -> str:
        """Suburb label to use for display."""
        if self.suburb.strip():
            return self.suburb
        return self.location.suburb

    @property
    def open_sans_dir(self) -> Path:
        """OpenSans directory"""
        return FONTS_DIR / "open-sans"

    @property
    def weather_dir(self) -> Path:
        """Weather icons directory"""
        return FONTS_DIR / "weather"

    @property
    def weather_icons_dir(self) -> Path:
        """Weather icon directory"""
        return FONTS_DIR / "weather-icons"

    @property
    def waveshare_lib_dir(self) -> Path:
        """Waveshare library directory"""
        return WAVESHARE_LIB_DIR

    def open_sans_paths(self, bold: bool) -> list[str]:
        """OpenSans paths"""
        font_name = "OpenSans-Bold.ttf" if bold else "OpenSans-Regular.ttf"
        windows_name = font_name
        return [
            str(self.open_sans_dir / font_name),
            f"/usr/share/fonts/truetype/open-sans/{font_name}",
            f"C:\\Windows\\Fonts\\{windows_name}",
            str(Path.home() /
                "AppData" /
                "Local" /
                "Microsoft" /
                "Windows" /
                "Fonts" /
                windows_name
            ),
        ]

    def weather_icon_paths(self) -> list[str]:
        """Weather icon paths"""
        font_name = "weathericons-regular-webfont.ttf"
        return [
            str(self.weather_icons_dir / font_name),
            f"/usr/share/fonts/truetype/weather-icons/{font_name}",
            f"C:\\Windows\\Fonts\\{font_name}",
            str(Path.home() /
                "AppData" /
                "Local" /
                "Microsoft" /
                "Windows" /
                "Fonts" /
                font_name
            ),
        ]
