"""Location label resolution from coordinates."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, cast

from requests import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocationLabel:
    """Human-readable location resolved from coordinates."""

    city: str
    state: str = ""
    suburb: str = ""


def format_location_label(
    tz_name: str,
    suburb: str = "",
    state: str = "",
    city: str = "",
) -> str:
    """Build a display label as 'Suburb, State' with sensible fallbacks."""
    resolved_region = state.strip() or city.strip() or tz_name.split("/")[-1].replace("_", " ")
    suburb = suburb.strip()
    if suburb:
        return f"{suburb}, {resolved_region}"
    return resolved_region


@dataclass(slots=True)
class NominatimLocationResolver:
    """Resolve suburb/city labels using OpenStreetMap Nominatim."""

    session: Session
    latitude: float
    longitude: float
    timezone_name: str
    _user_agent: str = field(init=False, default="pidash/1.0")

    def __post_init__(self):
        """Build a policy-compliant user agent string."""
        contact = os.getenv("NOMINATIM_CONTACT", "").strip()
        self._user_agent = "pidash/1.0"
        if contact:
            self._user_agent = f"pidash/1.0 ({contact})"

    def request_location_label(self) -> LocationLabel | None:
        """Reverse geocode coordinates into suburb and city."""
        try:
            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": self.latitude,
                    "lon": self.longitude,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "accept-language": "en",
                },
                headers={"User-Agent": self._user_agent},
                timeout=3,
            )
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            address = cast(dict[str, Any], payload.get("address", {}))

            city = str(
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or address.get("county")
                or ""
            ).strip()
            state = str(
                address.get("state")
                or address.get("province")
                or address.get("state_district")
                or ""
            ).strip()
            suburb = str(
                address.get("suburb")
                or address.get("neighbourhood")
                or address.get("city_district")
                or address.get("quarter")
                or address.get("hamlet")
                or ""
            ).strip()

            if not city:
                city = format_location_label(self.timezone_name)
            if not state:
                state = city
            if suburb.lower() == city.lower():
                suburb = ""

            return LocationLabel(city=city, state=state, suburb=suburb)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Location reverse geocoding failed: %s", exc)
            return None
