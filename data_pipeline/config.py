"""Central configuration for the data pipeline.

Defines directory paths, coordinate reference system defaults,
and validation limits used across the pipeline modules.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Project root (resolved relative to this file)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
SAMPLE_CITY_DIR = SAMPLE_DATA_DIR / "city"
SAMPLE_WEATHER_DIR = SAMPLE_DATA_DIR / "weather"
SAMPLE_SOLAR_DIR = SAMPLE_DATA_DIR / "solar"

# Ensure output directories exist.
for _dir in (RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTERNAL_DATA_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Default paths for processed output
# ---------------------------------------------------------------------------

DEFAULT_CITY_OUTPUT = PROCESSED_DATA_DIR / "city_buildings.geojson"
DEFAULT_WEATHER_OUTPUT = PROCESSED_DATA_DIR / "weather_clean.csv"
DEFAULT_SOLAR_OUTPUT = PROCESSED_DATA_DIR / "solar_clean.csv"
DEFAULT_REPORT_OUTPUT = PROCESSED_DATA_DIR / "processing_report.json"
DEFAULT_PIPELINE_STATE = PROCESSED_DATA_DIR / "pipeline_state.json"

# ---------------------------------------------------------------------------
# Coordinate Reference Systems
# ---------------------------------------------------------------------------

DEFAULT_CRS = "EPSG:4326"  # WGS84
UTM_CRS_PREFIX = "EPSG:"  # Append UTM zone number

# ---------------------------------------------------------------------------
# Validation limits
# ---------------------------------------------------------------------------

LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0

# Temperature in Celsius
TEMPERATURE_MIN = -60.0
TEMPERATURE_MAX = 60.0

# Humidity in percent
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0

# Wind speed in m/s (must be non-negative)
WIND_SPEED_MIN = 0.0
WIND_SPEED_MAX = 200.0

# Cloud cover in percent
CLOUD_COVER_MIN = 0.0
CLOUD_COVER_MAX = 100.0

# Precipitation in mm (non-negative)
PRECIPITATION_MIN = 0.0
PRECIPITATION_MAX = 500.0

# Solar irradiance in W/m² (non-negative)
IRRADIANCE_MIN = 0.0
IRRADIANCE_MAX = 1600.0

# ---------------------------------------------------------------------------
# Column name mappings (normalize various dataset column names)
# ---------------------------------------------------------------------------

WEATHER_COLUMN_MAP: dict[str, str] = {
    # Timestamp
    "time": "timestamp",
    "datetime": "timestamp",
    "date": "timestamp",
    "date_time": "timestamp",
    "recorded_at": "timestamp",
    "measurement_time": "timestamp",
    # Location
    "lat": "latitude",
    "lat_deg": "latitude",
    "latitude_deg": "latitude",
    "lon": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "lon_deg": "longitude",
    "longitude_deg": "longitude",
    # Weather
    "temp": "temperature",
    "temp_c": "temperature",
    "temperature_c": "temperature",
    "temp_celsius": "temperature",
    "rh": "humidity",
    "relative_humidity": "humidity",
    "humidity_pct": "humidity",
    "wind": "wind_speed",
    "wind_mps": "wind_speed",
    "wind_speed_ms": "wind_speed",
    "cloud": "cloud_cover",
    "cloud_pct": "cloud_cover",
    "cloudiness": "cloud_cover",
    "rain": "precipitation",
    "rainfall": "precipitation",
    "precip": "precipitation",
    "precipitation_mm": "precipitation",
}

SOLAR_COLUMN_MAP: dict[str, str] = {
    # Timestamp
    "time": "timestamp",
    "datetime": "timestamp",
    "date": "timestamp",
    "date_time": "timestamp",
    "recorded_at": "timestamp",
    "measurement_time": "timestamp",
    # Location
    "lat": "latitude",
    "lat_deg": "latitude",
    "latitude_deg": "latitude",
    "lon": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "lon_deg": "longitude",
    "longitude_deg": "longitude",
    # Solar
    "global_horizontal": "ghi",
    "global_irradiance": "ghi",
    "direct_normal": "dni",
    "direct_normal_irradiance": "dni",
    "diffuse_horizontal": "dhi",
    "diffuse_irradiance": "dhi",
    "irradiance": "solar_irradiance",
    "solar": "solar_irradiance",
    "solar_power": "solar_irradiance",
}
