"""Centralized configuration for the SolarIQ backend.

All tunable parameters are defined here. Environment variables
take precedence over defaults.  Never hardcode secrets.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

ENVIRONMENT: str = os.getenv("SOLARIQ_ENV", "development")

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------

APP_TITLE: str = "SolarIQ Backend"
APP_VERSION: str = "0.1.0"
APP_DESCRIPTION: str = (
    "3D building geometry analysis and "
    "BIPV solar potential assessment API."
)

# ---------------------------------------------------------------------------
# Solar / BIPV defaults
# ---------------------------------------------------------------------------

COVERAGE_FACTOR: float = float(
    os.getenv("SOLARIQ_COVERAGE_FACTOR", "0.80")
)

PANEL_EFFICIENCY: float = float(
    os.getenv("SOLARIQ_PANEL_EFFICIENCY", "0.20")
)

ANNUAL_IRRADIANCE_KWH_M2: float = float(
    os.getenv("SOLARIQ_ANNUAL_IRRADIANCE", "1700.0")
)

PERFORMANCE_RATIO: float = float(
    os.getenv("SOLARIQ_PERFORMANCE_RATIO", "0.85")
)

# ---------------------------------------------------------------------------
# Optimization scoring weights
# ---------------------------------------------------------------------------

OPT_WEIGHT_SUITABILITY: float = float(
    os.getenv("SOLARIQ_OPT_WEIGHT_SUITABILITY", "0.35")
)
OPT_WEIGHT_ENERGY: float = float(
    os.getenv("SOLARIQ_OPT_WEIGHT_ENERGY", "0.25")
)
OPT_WEIGHT_CAPACITY: float = float(
    os.getenv("SOLARIQ_OPT_WEIGHT_CAPACITY", "0.15")
)
OPT_WEIGHT_AREA: float = float(
    os.getenv("SOLARIQ_OPT_WEIGHT_AREA", "0.15")
)
OPT_WEIGHT_ORIENTATION: float = float(
    os.getenv("SOLARIQ_OPT_WEIGHT_ORIENTATION", "0.10")
)

# ---------------------------------------------------------------------------
# Request limits
# ---------------------------------------------------------------------------

MAX_BUILDINGS_PER_REQUEST: int = int(
    os.getenv("SOLARIQ_MAX_BUILDINGS", "100")
)

MAX_SURFACES_PER_BUILDING: int = int(
    os.getenv("SOLARIQ_MAX_SURFACES", "50")
)

MAX_OPTIMIZATION_LIMIT: int = int(
    os.getenv("SOLARIQ_MAX_OPTIMIZATION_LIMIT", "1000")
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "SOLARIQ_DATABASE_URL",
    "sqlite:///solariq.db",
)

# For tests, use an in-memory SQLite database.
# This can be overridden via the SOLARIQ_DATABASE_URL env var.
TEST_DATABASE_URL: str = os.getenv(
    "SOLARIQ_TEST_DATABASE_URL",
    "sqlite://",
)

# ---------------------------------------------------------------------------
# Model / data paths
# ---------------------------------------------------------------------------

MODEL_DIR: str = os.getenv(
    "SOLARIQ_MODEL_DIR", "models"
)

DATA_DIR: str = os.getenv(
    "SOLARIQ_DATA_DIR", "data"
)

PROCESSED_DATA_DIR: str = os.getenv(
    "SOLARIQ_PROCESSED_DATA_DIR", "data/processed"
)
