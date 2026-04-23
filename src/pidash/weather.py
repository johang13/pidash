"""Open-Meteo integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import logging
from typing import Any, cast
from zoneinfo import ZoneInfo
import openmeteo_requests
import requests_cache
from requests import Session
from retry_requests import retry
from .settings import AppSettings, LocationSettings, PROJECT_ROOT

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class CurrentWeather:
    """Current weather data."""
    observed_at: datetime
    temperature_2m: float
    weather_code: int
    wind_speed_10m: float
    apparent_temperature: float
    relative_humidity: float

    def fingerprint(self) -> tuple[
        int,
        float,
        float,
        float,
        float
    ]:
        """Return a fingerprint of the weather data for change detection."""
        return (
            self.weather_code,
            round(self.temperature_2m, 1),
            round(self.apparent_temperature, 1),
            round(self.wind_speed_10m, 1),
            round(self.relative_humidity, 1)
        )

class OpenMeteoClient:
    """Open-Meteo client."""
    def __init__(
            self,
            *,
            location_settings: LocationSettings,
            cache_name: str = 'openmeteo_cache',
            expire_after: int = 60
    ):
        self.latitude = location_settings.latitude
        self.longitude = location_settings.longitude
        self.timezone_name = location_settings.timezone
        cache_path = os.path.join(PROJECT_ROOT, cache_name)
        cache_session = requests_cache.CachedSession(str(cache_path),
                                                     expire_after=expire_after)
        retry_session = cast(Session, retry(cast(Any, cache_session),
                                            retries=1,
                                            backoff_factor=0.2))
        self._client = openmeteo_requests.Client(session=retry_session)

    @classmethod
    def from_settings(cls, settings: AppSettings) -> OpenMeteoClient:
        """Create client from settings."""
        return cls(
            location_settings=settings.location,
            expire_after=settings.weather_cache_seconds,
        )

    def request_current(self) -> CurrentWeather:
        """Request current weather."""
        response = self._client.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": [
                    "temperature_2m",
                    "weather_code",
                    "wind_speed_10m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                ],
                "timezone": self.timezone_name,
                "forecast_days": 1,
            },
            timeout=3,
        )[0]

        current = response.Current()
        utc_time = datetime.fromtimestamp(current.Time(), tz=timezone.utc)
        local_time = utc_time.astimezone(ZoneInfo(self.timezone_name))

        weather = CurrentWeather(
            observed_at=local_time,
            temperature_2m=float(current.Variables(0).Value()),
            weather_code=int(current.Variables(1).Value()),
            wind_speed_10m=float(current.Variables(2).Value()),
            apparent_temperature=float(current.Variables(3).Value()),
            relative_humidity=float(current.Variables(4).Value()),
        )
        logger.debug("Fetched weather update: %s", weather)
        return weather

@lru_cache(maxsize=1)
def default_weather_client() -> OpenMeteoClient:
    """Default weather client."""
    return OpenMeteoClient.from_settings(AppSettings(emulate=False))
