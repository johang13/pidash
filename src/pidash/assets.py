"""Weather code metadata and icon mappings."""

from __future__ import annotations

WEATHER_DESCRIPTIONS = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Heavy Drizzle",
    61: "Light Rain",
    63: "Rain",
    65: "Heavy Rain",
    71: "Light Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Light Showers",
    81: "Showers",
    82: "Heavy Showers",
    85: "Light Snow Showers",
    86: "Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm & Hail",
    99: "Thunderstorm & Hail",
}

WEATHER_ICONS = {
    0: "\uf00d",  # wi-day-sunny
    1: "\uf00c",  # wi-day-cloudy
    2: "\uf002",  # wi-day-cloudy
    3: "\uf041",  # wi-cloudy
    45: "\uf014",  # wi-fog
    48: "\uf014",  # wi-fog
    51: "\uf01c",  # wi-sprinkle
    53: "\uf01c",  # wi-sprinkle
    55: "\uf019",  # wi-rain
    61: "\uf019",  # wi-rain
    63: "\uf019",  # wi-rain
    65: "\uf019",  # wi-rain
    71: "\uf01b",  # wi-snow
    73: "\uf01b",  # wi-snow
    75: "\uf01b",  # wi-snow
    77: "\uf01b",  # wi-snow
    80: "\uf01a",  # wi-showers
    81: "\uf01a",  # wi-showers
    82: "\uf01a",  # wi-showers
    85: "\uf01b",  # wi-snow
    86: "\uf01b",  # wi-snow
    95: "\uf01e",  # wi-thunderstorm
    96: "\uf01e",  # wi-thunderstorm
    99: "\uf01e",  # wi-thunderstorm
}


def weather_code_to_description(code: int | float) -> str:
    """Map weather code to description."""
    return WEATHER_DESCRIPTIONS.get(int(code), "Unknown")


def weather_code_to_icon(code: int | float) -> str:
    """Map weather code to weather icon."""
    return WEATHER_ICONS.get(int(code), "\uf00d")
