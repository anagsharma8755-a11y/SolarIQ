"""Solar radiation data provider interface.

Supports multiple solar data sources:
- PVGIS-compatible data (EU Joint Research Centre)
- Local CSV/JSON files
- Existing SolarIQ solar datasets

Distinguishes between:
- real data (from APIs or validated sources)
- synthetic data (generated for testing)
- fallback/demo data (default values)
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from data_pipeline.config import SOLAR_COLUMN_MAP

logger = logging.getLogger(__name__)

# Maximum response size from external APIs (10 MB).
_MAX_API_RESPONSE_SIZE = 10 * 1024 * 1024


class SolarProvider(ABC):
    """Abstract base class for solar data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    @abstractmethod
    def data_quality(self) -> str:
        """Data quality indicator: 'real', 'synthetic', or 'fallback'."""
        ...

    @abstractmethod
    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch solar irradiance data for a location and date range.

        Args:
            latitude: WGS84 latitude.
            longitude: WGS84 longitude.
            start_date: ISO date string (YYYY-MM-DD).
            end_date: ISO date string (YYYY-MM-DD).

        Returns:
            DataFrame with normalized solar columns.
        """
        ...

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply standard column name normalization."""
        df.columns = [
            SOLAR_COLUMN_MAP.get(c.strip().lower().replace(" ", "_"), c)
            for c in df.columns
        ]
        return df


class PVGISProvider(SolarProvider):
    """PVGIS (Photovoltaic Geographical Information System) provider.

    Uses the EU JRC PVGIS API for solar radiation data.
    https://re.jrc.ec.europa.eu/pvg_tools/en/
    """

    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_2 series"

    @property
    def name(self) -> str:
        return "pvgis"

    @property
    def data_quality(self) -> str:
        return "real"

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch hourly solar data from PVGIS."""
        # PVGIS TMY endpoint for typical meteorological year data
        params = (
            f"lat={latitude}"
            f"&lon={longitude}"
            f"&outputformat=json"
            f"&angle=35"
            f"&aspect=0"
        )
        url = f"https://re.jrc.ec.europa.eu/api/v5_2/TMY?{params}"

        logger.info("Fetching solar data from PVGIS: %s", url)

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                # Enforce response size limit.
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > _MAX_API_RESPONSE_SIZE:
                    raise ConnectionError(
                        f"PVGIS response too large: {content_length} bytes"
                    )
                body = response.read(_MAX_API_RESPONSE_SIZE + 1)
                if len(body) > _MAX_API_RESPONSE_SIZE:
                    raise ConnectionError(
                        f"PVGIS response exceeds {_MAX_API_RESPONSE_SIZE} bytes"
                    )
                data = json.loads(body.decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise ConnectionError(
                f"PVGIS request failed: {exc}"
            ) from exc

        outputs = data.get("outputs", {})
        tmy_data = outputs.get("tmy_hourly", [])

        if not tmy_data:
            raise ValueError("PVGIS response missing TMY data.")

        records = []
        for entry in tmy_data:
            records.append({
                "timestamp": entry.get("time", ""),
                "latitude": latitude,
                "longitude": longitude,
                "ghi": entry.get("G(h)", 0.0),
                "dni": entry.get("G(h)", 0.0) * 0.7,  # Approximate
                "dhi": entry.get("G(h)", 0.0) * 0.3,  # Approximate
                "solar_irradiance": entry.get("G(h)", 0.0),
            })

        df = pd.DataFrame(records)
        return self._normalize_columns(df)


class FallbackSolarProvider(SolarProvider):
    """Fallback provider that generates synthetic demo data.

    Uses clear-sky approximation based on latitude and month.
    """

    @property
    def name(self) -> str:
        return "fallback"

    @property
    def data_quality(self) -> str:
        return "fallback"

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Generate synthetic hourly solar data."""
        from datetime import datetime, timedelta

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        records = []
        current = start
        while current <= end:
            hour = current.hour
            month = current.month

            # Simple clear-sky model
            # Peak at noon, zero at night
            solar_angle = max(0, math.sin(math.pi * (hour - 6) / 12))

            # Seasonal variation (higher in summer for northern hemisphere)
            seasonal = 0.7 + 0.3 * math.sin(
                2 * math.pi * (month - 3) / 12
            )

            # Latitude factor
            lat_factor = math.cos(math.radians(abs(latitude)))

            ghi = max(0, 1000 * solar_angle * seasonal * lat_factor)
            dni = ghi * 0.7
            dhi = ghi * 0.3

            records.append({
                "timestamp": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "latitude": latitude,
                "longitude": longitude,
                "ghi": round(ghi, 2),
                "dni": round(dni, 2),
                "dhi": round(dhi, 2),
                "solar_irradiance": round(ghi, 2),
            })

            current += timedelta(hours=1)

        df = pd.DataFrame(records)
        return self._normalize_columns(df)


class LocalSolarProvider(SolarProvider):
    """Local file solar data provider."""

    @property
    def name(self) -> str:
        return "local"

    @property
    def data_quality(self) -> str:
        return "real"

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Not implemented - use load_solar_data directly."""
        raise NotImplementedError(
            "LocalSolarProvider.fetch() is not used. "
            "Use data_pipeline.solar.loader.load_solar_data() instead."
        )

    def load_file(self, file_path: Path | str) -> pd.DataFrame:
        """Load solar data from a local CSV or JSON file."""
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


def get_solar_provider(
    provider_name: str = "local",
) -> SolarProvider:
    """Factory function to get a solar provider by name.

    Args:
        provider_name: One of 'pvgis', 'fallback', 'local'.

    Returns:
        A SolarProvider instance.
    """
    providers = {
        "pvgis": PVGISProvider,
        "fallback": FallbackSolarProvider,
        "local": LocalSolarProvider,
    }

    cls = providers.get(provider_name)
    if cls is None:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available: {list(providers.keys())}"
        )
    return cls()
