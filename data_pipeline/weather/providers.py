"""Weather data provider interface.

Supports multiple weather data sources:
- Open-Meteo API (free, no API key required)
- ERA5-compatible datasets
- Local CSV/JSON files

All providers normalize data to a standard schema:
    timestamp, latitude, longitude, temperature, humidity,
    cloud_cover, wind_speed, pressure, precipitation

Network providers have graceful offline fallback.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data_pipeline.config import WEATHER_COLUMN_MAP

logger = logging.getLogger(__name__)

# Maximum response size from external APIs (10 MB).
_MAX_API_RESPONSE_SIZE = 10 * 1024 * 1024


class WeatherProvider(ABC):
    """Abstract base class for weather data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @abstractmethod
    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch weather data for a location and date range.

        Args:
            latitude: WGS84 latitude.
            longitude: WGS84 longitude.
            start_date: ISO date string (YYYY-MM-DD).
            end_date: ISO date string (YYYY-MM-DD).

        Returns:
            DataFrame with normalized weather columns.
        """
        ...

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard column name normalization."""
        df.columns = [
            WEATHER_COLUMN_MAP.get(c.strip().lower().replace(" ", "_"), c)
            for c in df.columns
        ]
        return df


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo weather API provider.

    Free tier, no API key required.
    https://open-meteo.com/
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @property
    def name(self) -> str:
        return "open-meteo"

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch hourly weather data from Open-Meteo."""
        params = (
            f"latitude={latitude}"
            f"&longitude={longitude}"
            f"&start_date={start_date}"
            f"&end_date={end_date}"
            f"&hourly=temperature_2m,relative_humidity_2m,"
            f"cloud_cover,wind_speed_10m,precipitation,"
            f"pressure_msl"
            f"&timezone=auto"
        )
        url = f"{self.BASE_URL}?{params}"

        logger.info("Fetching weather from Open-Meteo: %s", url)

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                # Enforce response size limit.
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > _MAX_API_RESPONSE_SIZE:
                    raise ConnectionError(
                        f"Open-Meteo response too large: {content_length} bytes"
                    )
                body = response.read(_MAX_API_RESPONSE_SIZE + 1)
                if len(body) > _MAX_API_RESPONSE_SIZE:
                    raise ConnectionError(
                        f"Open-Meteo response exceeds {_MAX_API_RESPONSE_SIZE} bytes"
                    )
                data = json.loads(body.decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise ConnectionError(
                f"Open-Meteo request failed: {exc}"
            ) from exc

        hourly = data.get("hourly", {})
        if not hourly:
            raise ValueError("Open-Meteo response missing hourly data.")

        times = hourly.get("time", [])
        df = pd.DataFrame({
            "timestamp": times,
            "latitude": latitude,
            "longitude": longitude,
            "temperature": hourly.get("temperature_2m", []),
            "humidity": hourly.get("relative_humidity_2m", []),
            "cloud_cover": hourly.get("cloud_cover", []),
            "wind_speed": hourly.get("wind_speed_10m", []),
            "precipitation": hourly.get("precipitation", []),
            "pressure": hourly.get("pressure_msl", []),
        })

        return self._normalize_columns(df)


class LocalWeatherProvider(WeatherProvider):
    """Local file weather data provider."""

    @property
    def name(self) -> str:
        return "local"

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Not implemented - use load_weather_data directly."""
        raise NotImplementedError(
            "LocalWeatherProvider.fetch() is not used. "
            "Use data_pipeline.weather.loader.load_weather_data() instead."
        )

    def load_file(self, file_path: Path | str) -> pd.DataFrame:
        """Load weather data from a local CSV or JSON file."""
        path = Path(file_path)

        # Validate file safety.
        if path.is_symlink():
            raise ValueError(
                f"Symlinked file not allowed: {path}. Use a regular file."
            )
        file_size = path.stat().st_size
        if file_size > 200 * 1024 * 1024:
            raise ValueError(
                f"File {path.name} exceeds 200 MB limit."
            )

        suffix = path.suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                records = data.get("records", data.get("data", []))
            else:
                records = data
            df = pd.DataFrame(records)
        else:
            raise ValueError(f"Unsupported format: {suffix}")

        return self._normalize_columns(df)


def get_weather_provider(
    provider_name: str = "local",
) -> WeatherProvider:
    """Factory function to get a weather provider by name.

    Args:
        provider_name: One of 'open-meteo', 'local'.

    Returns:
        A WeatherProvider instance.
    """
    providers = {
        "open-meteo": OpenMeteoProvider,
        "local": LocalWeatherProvider,
    }

    cls = providers.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available: {list(providers.keys())}"
        )
    return cls()
