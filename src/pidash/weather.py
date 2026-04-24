"""Open-Meteo integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import logging
from typing import Any, cast
from zoneinfo import ZoneInfo
import openmeteo_requests
import requests_cache
from requests import Session
from retry_requests import retry
from .location import LocationLabel, NominatimLocationResolver
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


@dataclass(frozen=True)
class DailyForecast:
    """Daily forecast row for compact strip rendering."""
    day: date
    weather_code: int
    temp_max: float
    temp_min: float


@dataclass(frozen=True)
class HourlyForecast:
    """Hourly forecast row for compact near-term rendering."""
    observed_at: datetime
    weather_code: int
    temperature_2m: float


@dataclass(frozen=True)
class DashboardWeather:
    """Current weather plus short daily forecast for the dashboard."""
    current: CurrentWeather
    hourly: tuple[HourlyForecast, ...]
    daily: tuple[DailyForecast, ...]

    def fingerprint(self) -> tuple[object, ...]:
        """Return a redraw fingerprint spanning current + daily weather."""
        daily_fingerprint: tuple[object, ...] = tuple(
            (
                row.day.isoformat(),
                row.weather_code,
                round(row.temp_max, 1),
                round(row.temp_min, 1),
            )
            for row in self.daily
        )
        hourly_fingerprint: tuple[object, ...] = tuple(
            (
                row.observed_at.isoformat(),
                row.weather_code,
                round(row.temperature_2m, 1),
            )
            for row in self.hourly
        )
        return (
            *self.current.fingerprint(),
            *hourly_fingerprint,
            *daily_fingerprint,
        )
class OpenMeteoClient:
    """Open-Meteo client."""
    def __init__(
            self,
            *,
            location_settings: LocationSettings,
            cache_name: str = 'openmeteo_cache',
            expire_after: int = 60,
            hourly_forecast_hours: int = 8,
    ):
        self.latitude = location_settings.latitude
        self.longitude = location_settings.longitude
        self.timezone_name = location_settings.timezone
        self.hourly_forecast_hours = hourly_forecast_hours
        cache_path = os.path.join(PROJECT_ROOT, cache_name)
        cache_session = requests_cache.CachedSession(str(cache_path),
                                                     expire_after=expire_after)
        retry_session = cast(Session, retry(cast(Any, cache_session),
                                            retries=1,
                                            backoff_factor=0.2))
        self._session = retry_session
        self._location_resolver = NominatimLocationResolver(
            session=retry_session,
            latitude=self.latitude,
            longitude=self.longitude,
            timezone_name=self.timezone_name,
        )
        self._client = openmeteo_requests.Client(session=retry_session)

    @classmethod
    def from_settings(cls, settings: AppSettings) -> OpenMeteoClient:
        """Create client from settings."""
        return cls(
            location_settings=settings.location,
            expire_after=settings.weather_cache_seconds,
            hourly_forecast_hours=settings.hourly_forecast_hours,
        )

    def request_dashboard(self) -> DashboardWeather:
        """Request data needed to draw the full dashboard."""
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
                "daily": [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                ],
                "hourly": [
                    "temperature_2m",
                    "weather_code",
                ],
                "timezone": self.timezone_name,
                "forecast_days": 5,
            },
            timeout=3,
        )[0]

        current = response.Current()
        utc_time = datetime.fromtimestamp(current.Time(), tz=timezone.utc)
        local_time = utc_time.astimezone(ZoneInfo(self.timezone_name))

        current_weather = CurrentWeather(
            observed_at=local_time,
            temperature_2m=float(current.Variables(0).Value()),
            weather_code=int(current.Variables(1).Value()),
            wind_speed_10m=float(current.Variables(2).Value()),
            apparent_temperature=float(current.Variables(3).Value()),
            relative_humidity=float(current.Variables(4).Value()),
        )

        hourly = response.Hourly()
        hourly_temp = [float(temp) for temp in list(hourly.Variables(0).ValuesAsNumpy())]
        hourly_codes = [int(code) for code in list(hourly.Variables(1).ValuesAsNumpy())]
        hourly_start = datetime.fromtimestamp(hourly.Time(), tz=ZoneInfo(self.timezone_name))
        hourly_step = timedelta(seconds=hourly.Interval())

        next_hour = local_time.replace(minute=0, second=0, microsecond=0)
        if local_time.minute > 0 or local_time.second > 0:
            next_hour += timedelta(hours=1)

        hourly_weather = tuple(
            HourlyForecast(
                observed_at=observed_at,
                weather_code=code,
                temperature_2m=temp,
            )
            for observed_at, code, temp in (
                (
                    hourly_start + (hourly_step * index),
                    code,
                    temp,
                )
                for index, (code, temp) in enumerate(
                    zip(hourly_codes, hourly_temp, strict=False)
                )
            )
            if observed_at >= next_hour
        )[:self.hourly_forecast_hours]

        daily = response.Daily()
        daily_weather_codes = [int(code) for code in list(daily.Variables(0).ValuesAsNumpy())]
        daily_temp_max = [float(temp) for temp in list(daily.Variables(1).ValuesAsNumpy())]
        daily_temp_min = [float(temp) for temp in list(daily.Variables(2).ValuesAsNumpy())]
        forecast_start = datetime.fromtimestamp(
            daily.Time(),
            tz=ZoneInfo(self.timezone_name),
        ).date()
        daily_days = [
            forecast_start + timedelta(days=offset)
            for offset in range(len(daily_weather_codes))
        ]

        daily_weather = tuple(
            DailyForecast(
                day=day,
                weather_code=code,
                temp_max=temp_max,
                temp_min=temp_min,
            )
            for day, code, temp_max, temp_min in zip(
                daily_days,
                daily_weather_codes,
                daily_temp_max,
                daily_temp_min,
                strict=False,
            )
        )

        weather = DashboardWeather(
            current=current_weather,
            hourly=hourly_weather,
            daily=daily_weather,
        )
        logger.debug("Fetched weather update: %s", weather)
        return weather

    def request_current(self) -> CurrentWeather:
        """Request current weather only."""
        return self.request_dashboard().current

    def request_location_label(self) -> LocationLabel | None:
        """Reverse geocode coordinates into suburb and city."""
        return self._location_resolver.request_location_label()

@lru_cache(maxsize=1)
def default_weather_client() -> OpenMeteoClient:
    """Default weather client."""
    return OpenMeteoClient.from_settings(AppSettings(emulate=False))
