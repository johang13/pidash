"""Dashboard rendering and scheduling."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from .assets import weather_code_to_icon
from .settings import AppSettings
from .system import get_wifi_ssid
from .weather import CurrentWeather, OpenMeteoClient

logger = logging.getLogger(__name__)


class EPDProtocol(Protocol):
    """Interface for the display (used by the real hardware and emulator)."""

    width: int
    height: int

    def init(self) -> int:
        """Initialize the display."""

    def init_fast(self) -> int:
        """Initialize the display in fast mode."""

    def getbuffer(self, image: Image.Image):
        """Return a display buffer for the supplied image."""

    def display(self, image) -> None:
        """Render a full-frame display update."""

    def display_Partial(  # pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments
        self,
        image,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Render a partial display update (Waveshare-compatible API name/signature)."""

    def sleep(self) -> None:
        """Put the display into sleep mode."""


@dataclass(slots=True)
class Dashboard:  # pylint: disable=too-many-instance-attributes
    """Draw dashboard widgets and schedule full/partial display refreshes."""

    epd: EPDProtocol
    settings: AppSettings
    weather_client: OpenMeteoClient
    width: int = field(init=False)
    height: int = field(init=False)
    canvas: Image.Image = field(init=False)
    draw: ImageDraw.ImageDraw = field(init=False)
    last_updates: dict[str, float] = field(default_factory=lambda: {
        "current_conditions": 0.0,
        "full_refresh": 0.0,
    })
    current_conditions_cache: tuple[int, float, float, float, float] | None = None
    _font_cache: dict[tuple[object, ...], ImageFont.FreeTypeFont | ImageFont.ImageFont] = field(
        default_factory=dict
    )

    ZONES = {
        "status_bar": (0, 0, 800, 30),
        "current_conditions": (0, 30, 400, 150),
    }

    def __post_init__(self):
        """Initialize drawing surfaces using the attached display dimensions."""
        self.width = self.epd.width
        self.height = self.epd.height
        logger.info("EPD dimensions: %sx%s", self.width, self.height)
        self.canvas = Image.new("1", (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)

    def get_font(self, size: int, *, bold: bool = False):
        """Load and cache an Open Sans font for the requested size and weight."""
        cache_key = ("open_sans", size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = None
        for path in self.settings.open_sans_paths(bold=bold):
            try:
                font = ImageFont.truetype(path, size)
                break
            except (OSError, FileNotFoundError):
                continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    def get_weather_icon_font(self, size: int):
        """Load and cache the weather icon font at the requested size."""
        cache_key = ("weather_icons", size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = None
        for path in self.settings.weather_icon_paths():
            try:
                font = ImageFont.truetype(path, size)
                break
            except (OSError, FileNotFoundError):
                continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    def draw_status_bar(self):
        """Draw the top status bar with Wi-Fi state and refresh timestamps."""
        x, y, w, h = self.ZONES["status_bar"]
        wifi_name = get_wifi_ssid(emulate=self.settings.emulate, test_wifi=self.settings.test_wifi)

        self.draw.rectangle([x, y, x + w, y + h], fill=255)
        wifi_name = wifi_name or "No WiFi"

        wifi_font = self.get_font(18)
        bbox = self.draw.textbbox((0, 0), wifi_name, font=wifi_font)
        wifi_width = bbox[2] - bbox[0]
        self.draw.text((self.width - wifi_width - 10, y + 3), wifi_name, font=wifi_font, fill=0)

        center_x = self.width - wifi_width - 23
        center_y = y + 20
        radius = 1

        self.draw.ellipse((center_x - radius,
             center_y - radius,
             center_x + radius,
             center_y + radius), fill=0)

        self.draw.arc((self.width - wifi_width - 28,
             y + 12,
             self.width - wifi_width - 18,
             y + 17), 180, 0, fill=0, width=1)

        self.draw.arc((self.width - wifi_width - 30,
             y + 7,
             self.width - wifi_width - 16,
             y + 12), 180, 0, fill=0, width=1)

        if wifi_name == "No WiFi":
            self.draw.line((self.width - wifi_width - 31,
                 y + 6,
                 self.width - wifi_width - 16,
                 y + 20), fill=0, width=1)
            self.draw.line((self.width - wifi_width - 30,
                 y + 20,
                 self.width - wifi_width - 15,
                 y + 6), fill=0, width=1)

        last_full_refresh = time.strftime(
            "%d/%m/%y %H:%M:%S",
            time.localtime(self.last_updates["full_refresh"])
        )

        last_conditions_refresh = time.strftime(
            "%d/%m/%y %H:%M:%S",
            time.localtime(self.last_updates["current_conditions"])
        )
        self.draw.text(
            (x + 10, y + 3),
            f"Full: {last_full_refresh} | Conditions: {last_conditions_refresh}",
            font=wifi_font,
            fill=0,
        )
        return True

    def _request_weather(self) -> CurrentWeather | None:
        """Fetch current weather data, returning None when the request fails."""
        try:
            return self.weather_client.request_current()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Weather update failed: %s", exc)
            return None

    def draw_current_conditions(  # pylint: disable=too-many-locals
        self,
        weather: CurrentWeather | None = None,
    ):
        """Draw the current conditions panel when data changed since last render."""
        x, y, w, h = self.ZONES["current_conditions"]
        weather = weather or self._request_weather()
        if weather is None:
            return False
        fingerprint = weather.fingerprint()

        if self.current_conditions_cache == fingerprint:
            logger.debug("Current conditions unchanged; skipping redraw")
            return False

        self.current_conditions_cache = fingerprint
        self.draw.rectangle([x, y, x + w, y + h], fill=255)

        icon_center_x = x + 80
        icon_center_y = y + h // 2
        icon = weather_code_to_icon(weather.weather_code)
        icon_font = self.get_weather_icon_font(120)
        self.draw.text((icon_center_x, icon_center_y), icon, font=icon_font, fill=0, anchor="mm")

        temp = round(weather.temperature_2m, 1)
        temp_y = y
        temp_x = icon_center_x + 100
        temp_font = self.get_font(90, bold=True)
        bbox = self.draw.textbbox((temp_x, temp_y), f"{temp}°", font=temp_font)
        temp_center_x = (bbox[0] + bbox[2]) / 2
        self.draw.text((temp_x, temp_y), f"{temp}°", font=temp_font, fill=0)

        feels_like_text = f"Feels like {round(weather.apparent_temperature, 1)}°"
        feels_like_bbox = self.draw.textbbox((0, 0), feels_like_text, font=self.get_font(24))
        feels_like_width = feels_like_bbox[2] - feels_like_bbox[0]
        feels_like_x = temp_center_x - (feels_like_width / 2)
        self.draw.text((feels_like_x, bbox[3] + 5), feels_like_text, font=self.get_font(24), fill=0)
        return True

    def full_refresh(self):
        """Perform a full-frame refresh on the attached display."""
        logger.info("Performing full refresh")
        self.epd.display(self.epd.getbuffer(self.canvas))

    def _idle_wait(self):
        """Keep emulator UI responsive while waiting between refresh cycles."""
        if not self.settings.emulate:
            time.sleep(self.settings.loop_sleep_seconds)
            return

        deadline = time.monotonic() + self.settings.loop_sleep_seconds
        while time.monotonic() < deadline:
            if hasattr(self.epd, "update"):
                self.epd.update()
            time.sleep(0.05)

    def fast_refresh(self):
        """Perform a partial refresh when supported, otherwise fallback to full refresh."""
        if hasattr(self.epd, "display_Partial"):
            self.epd.display_Partial(self.epd.getbuffer(self.canvas), 0, 0, self.width, self.height)
        else:
            self.full_refresh()

    def run_forever(self):  # pylint: disable=too-many-branches
        """Run the dashboard refresh loop until interrupted."""
        now = time.time()
        for key in self.last_updates:
            self.last_updates[key] = now

        self.epd.init()
        self.draw_status_bar()
        self.draw_current_conditions()
        self.full_refresh()
        if self.settings.emulate:
            is_sleeping = False
        else:
            self.epd.sleep()
            is_sleeping = True

        try:
            while True:
                now = time.time()

                if now - self.last_updates["full_refresh"] >= self.settings.full_refresh_interval:
                    weather = self._request_weather()
                    self.epd.init()
                    is_sleeping = False
                    self.draw_current_conditions(weather)
                    for key in self.last_updates:
                        self.last_updates[key] = now
                    self.draw_status_bar()
                    self.full_refresh()
                elif (
                    now - self.last_updates["current_conditions"]
                    >= self.settings.current_conditions_interval
                ):
                    weather = self._request_weather()
                    self.last_updates["current_conditions"] = now
                    if self.draw_current_conditions(weather):
                        if hasattr(self.epd, "init_fast"):
                            self.epd.init_fast()
                        else:
                            self.epd.init()
                        is_sleeping = False
                        self.draw_status_bar()
                        self.fast_refresh()

                if not self.settings.emulate and not is_sleeping:
                    self.epd.sleep()
                    is_sleeping = True

                self._idle_wait()
        finally:
            if not self.settings.emulate and not is_sleeping:
                self.epd.sleep()
