"""Dashboard rendering and scheduling."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from .assets import weather_code_to_description, weather_code_to_icon
from .settings import AppSettings
from .system import get_wifi_ssid
from .weather import DashboardWeather, LocationLabel, OpenMeteoClient

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
    current_conditions_cache: tuple[object, ...] | None = None
    _location_label_cache: LocationLabel | None = None
    _font_cache: dict[tuple[object, ...], ImageFont.FreeTypeFont | ImageFont.ImageFont] = field(
        default_factory=dict
    )

    ZONES = {
        "main": (12, 0, 776, 268),
        "hourly_forecast": (12, 276, 776, 84),
        "daily_forecast": (12, 368, 776, 104),
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
        """Status bar removed; Wi-Fi is rendered in the main panel."""
        return True

    def _request_weather(self) -> DashboardWeather | None:
        """Fetch current weather data, returning None when the request fails."""
        try:
            return self.weather_client.request_dashboard()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Weather update failed: %s", exc)
            return None

    @staticmethod
    def _tz_to_location_label(tz_name: str, suburb: str = "", city: str = "") -> str:
        """Convert timezone text into a readable location label."""
        resolved_city = city.strip() or tz_name.split("/")[-1].replace("_", " ")
        suburb = suburb.strip()
        if suburb:
            return f"{suburb}, {resolved_city}"
        return resolved_city

    def _location_label(self) -> str:
        """Return display location text using manual settings or reverse geocoding."""
        if self.settings.display_suburb.strip():
            return self._tz_to_location_label(
                self.settings.timezone,
                self.settings.display_suburb,
            )

        if self._location_label_cache is None:
            self._location_label_cache = self.weather_client.request_location_label()

        if self._location_label_cache is not None:
            return self._tz_to_location_label(
                self.settings.timezone,
                self._location_label_cache.suburb,
                self._location_label_cache.city,
            )

        return self._tz_to_location_label(self.settings.timezone)

    def _draw_metric(self, x: int, y: int, label: str, value: str):
        """Draw a compact key/value metric block in the right-side column."""
        self.draw.text((x, y), label.upper(), font=self.get_font(14, bold=True), fill=0)
        self.draw.text((x, y + 16), value, font=self.get_font(25), fill=0)

    def _draw_hourly_strip(self, weather: DashboardWeather):
        """Draw compact next-hours forecast cards."""
        x, y, w, h = self.ZONES["hourly_forecast"]
        self.draw.rectangle([x, y, x + w, y + h], fill=255)

        cards = weather.hourly
        if not cards:
            self.draw.text((x + 12, y + 22), "No hourly data", font=self.get_font(20), fill=0)
            return

        inner_x = x + 4
        inner_y = y + 4
        inner_w = w - 8
        inner_h = h - 8
        card_gap = 6
        card_w = (inner_w - (card_gap * (len(cards) - 1))) // len(cards)

        for index, row in enumerate(cards):
            card_x1 = inner_x + (index * (card_w + card_gap))
            card_x2 = card_x1 + card_w - 1
            self.draw.rounded_rectangle(
                [card_x1, inner_y, card_x2, inner_y + inner_h],
                radius=10,
                outline=0,
                width=1,
                fill=255,
            )

            hour_text = row.observed_at.strftime("%H:%M")
            self.draw.text((card_x1 + 6, inner_y + 3), hour_text, font=self.get_font(14, bold=True), fill=0)

            self.draw.text(
                (card_x1 + (card_w // 2), inner_y + 38),
                weather_code_to_icon(row.weather_code),
                font=self.get_weather_icon_font(30),
                fill=0,
                anchor="mm",
            )

            temp_text = f"{round(row.temperature_2m):.0f}°"
            self.draw.text(
                (card_x1 + (card_w // 2), inner_y + inner_h - 10),
                temp_text,
                font=self.get_font(16),
                fill=0,
                anchor="mm",
            )

    def _draw_forecast_strip(self, weather: DashboardWeather):
        """Draw a row of compact daily forecast cards."""
        x, y, w, h = self.ZONES["daily_forecast"]
        self.draw.rectangle([x, y, x + w, y + h], fill=255)

        cards = weather.daily[:5]
        if not cards:
            self.draw.text((x + 14, y + 16), "No forecast data", font=self.get_font(24), fill=0)
            return

        inner_x = x + 4
        inner_y = y + 4
        inner_w = w - 8
        inner_h = h - 8
        card_gap = 8
        card_w = (inner_w - (card_gap * (len(cards) - 1))) // len(cards)

        for index, row in enumerate(cards):
            card_x1 = inner_x + (index * (card_w + card_gap))
            card_x2 = card_x1 + card_w - 1
            self.draw.rounded_rectangle(
                [card_x1, inner_y, card_x2, inner_y + inner_h],
                radius=10,
                outline=0,
                width=1,
                fill=255,
            )

            weekday = row.day.strftime("%a")
            self.draw.text((card_x1 + 7, inner_y + 4), weekday, font=self.get_font(14, bold=True), fill=0)

            icon = weather_code_to_icon(row.weather_code)
            self.draw.text(
                (card_x1 + (card_w // 2), inner_y + 44),
                icon,
                font=self.get_weather_icon_font(36),
                fill=0,
                anchor="mm",
            )

            high_low = f"{round(row.temp_max):.0f}/{round(row.temp_min):.0f}"
            self.draw.text(
                (card_x1 + (card_w // 2), inner_y + inner_h - 10),
                high_low,
                font=self.get_font(16),
                fill=0,
                anchor="mm",
            )

    def draw_current_conditions(  # pylint: disable=too-many-locals
        self,
        weather: DashboardWeather | None = None,
    ):
        """Draw the current conditions panel when data changed since last render."""
        x, y, w, h = self.ZONES["main"]
        weather = weather or self._request_weather()
        if weather is None:
            return False
        fingerprint = weather.fingerprint()

        if self.current_conditions_cache == fingerprint:
            logger.debug("Current conditions unchanged; skipping redraw")
            return False

        self.current_conditions_cache = fingerprint
        self.draw.rectangle([x, y, x + w, y + h], fill=255)

        current = weather.current
        updated_at_label = f"Updated At: {current.observed_at.strftime('%H:%M')}"
        self.draw.text((x + 4, y + 2), updated_at_label, font=self.get_font(16), fill=0)

        wifi_name = get_wifi_ssid(emulate=self.settings.emulate, test_wifi=self.settings.test_wifi) or "No WiFi"
        wifi_font = self.get_font(16)
        wifi_bbox = self.draw.textbbox((0, 0), wifi_name, font=wifi_font)
        wifi_width = wifi_bbox[2] - wifi_bbox[0]
        self.draw.text((x + w - wifi_width - 6, y + 2), wifi_name, font=wifi_font, fill=0)

        location_label = self._location_label()
        location_font = self.get_font(44, bold=True)
        location_bbox = self.draw.textbbox((0, 0), location_label, font=location_font)
        location_width = location_bbox[2] - location_bbox[0]
        location_x = x + ((w - location_width) // 2)
        self.draw.text((location_x, y - 2), location_label, font=location_font, fill=0)

        observed_text = current.observed_at.strftime("%A, %B %d")
        observed_font = self.get_font(18)
        observed_bbox = self.draw.textbbox((0, 0), observed_text, font=observed_font)
        observed_width = observed_bbox[2] - observed_bbox[0]
        observed_x = x + ((w - observed_width) // 2)
        self.draw.text((observed_x, y + 44), observed_text, font=observed_font, fill=0)

        icon_center_x = x + 102
        icon_center_y = y + 148
        icon = weather_code_to_icon(current.weather_code)
        self.draw.text(
            (icon_center_x, icon_center_y),
            icon,
            font=self.get_weather_icon_font(120),
            fill=0,
            anchor="mm",
        )

        temp = round(current.temperature_2m, 1)
        temp_text = f"{temp:.1f}°"
        temp_x = x + 180
        temp_y = y + 78
        temp_font = self.get_font(68, bold=True)
        self.draw.text((temp_x, icon_center_y - 60), temp_text, font=temp_font, fill=0)

        condition_text = weather_code_to_description(current.weather_code)
        self.draw.text(
            (icon_center_x, icon_center_y + 70),
            condition_text,
            font=self.get_font(20),
            fill=0,
            anchor="mm",
        )

        feels_like_text = f"Feels like {round(current.apparent_temperature, 1):.1f}°"
        self.draw.text(
            (temp_x, icon_center_y + 70),
            feels_like_text,
            font=self.get_font(20),
            fill=0,
            anchor="lm",
        )

        metrics_x = x + 544
        self._draw_metric(metrics_x, y + 35, "Wind", f"{round(current.wind_speed_10m, 1):.1f} km/h")
        self._draw_metric(metrics_x, y + 95, "Humidity", f"{round(current.relative_humidity):.0f}%")
        self._draw_metric(metrics_x, y + 155, "Updated", current.observed_at.strftime("%H:%M"))

        self._draw_hourly_strip(weather)
        self._draw_forecast_strip(weather)
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
                        self.fast_refresh()

                if not self.settings.emulate and not is_sleeping:
                    self.epd.sleep()
                    is_sleeping = True

                self._idle_wait()
        finally:
            if not self.settings.emulate and not is_sleeping:
                self.epd.sleep()
