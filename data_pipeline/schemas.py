"""Standardized data schemas for the data pipeline.

These Pydantic models define the canonical internal format for
building, weather, and solar data that the rest of SolarIQ consumes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Building / City schemas
# ---------------------------------------------------------------------------


class BuildingCoordinates(BaseModel):
    """Geographic coordinates for a building."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (WGS84).",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (WGS84).",
    )


class BuildingSurface(BaseModel):
    """A single surface belonging to a building.

    ``vertices`` is a list of [x, y, z] triples in the
    building's local coordinate system.
    """

    surface_id: str
    vertices: list[list[float]] = Field(
        ...,
        min_length=3,
        description="Ordered vertices as [x, y, z] triples.",
    )


class StandardizedBuilding(BaseModel):
    """Canonical building representation.

    This schema is compatible with the existing SolarIQ backend
    parser (``backend.geometry.parser.load_city_from_file``).
    """

    building_id: str
    name: str | None = None
    source: str = "unknown"
    coordinates: BuildingCoordinates | None = None
    crs: str = "EPSG:4326"
    surfaces: list[BuildingSurface] = Field(
        ...,
        min_length=1,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class StandardizedCity(BaseModel):
    """Collection of standardized buildings."""

    buildings: list[StandardizedBuilding]


# ---------------------------------------------------------------------------
# Weather schemas
# ---------------------------------------------------------------------------


class WeatherRecord(BaseModel):
    """Single weather observation record."""

    timestamp: str = Field(
        ...,
        description="ISO-8601 timestamp.",
    )
    latitude: float
    longitude: float
    temperature: float = Field(
        description="Temperature in degrees Celsius.",
    )
    humidity: float = Field(
        ge=0.0,
        le=100.0,
        description="Relative humidity in percent.",
    )
    wind_speed: float = Field(
        ge=0.0,
        description="Wind speed in m/s.",
    )
    cloud_cover: float = Field(
        ge=0.0,
        le=100.0,
        description="Cloud cover in percent.",
    )
    precipitation: float = Field(
        ge=0.0,
        description="Precipitation in mm.",
    )


class WeatherDataset(BaseModel):
    """Collection of weather records."""

    records: list[WeatherRecord]
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Solar schemas
# ---------------------------------------------------------------------------


class SolarRecord(BaseModel):
    """Single solar radiation observation."""

    timestamp: str = Field(
        ...,
        description="ISO-8601 timestamp.",
    )
    latitude: float
    longitude: float
    ghi: float = Field(
        ge=0.0,
        description="Global horizontal irradiance in W/m².",
    )
    dni: float = Field(
        ge=0.0,
        description="Direct normal irradiance in W/m².",
    )
    dhi: float = Field(
        ge=0.0,
        description="Diffuse horizontal irradiance in W/m².",
    )
    solar_irradiance: float = Field(
        ge=0.0,
        description="Total solar irradiance in W/m².",
    )


class SolarDataset(BaseModel):
    """Collection of solar records."""

    records: list[SolarRecord]
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation result schemas
# ---------------------------------------------------------------------------


class ValidationError(BaseModel):
    """Single validation error entry."""

    record_index: int
    field: str
    error: str
    severity: str = "error"


class ValidationResult(BaseModel):
    """Structured validation output."""

    valid: bool
    records_total: int
    records_valid: int
    records_invalid: int
    errors: list[ValidationError] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Processing report
# ---------------------------------------------------------------------------


class ProcessingStep(BaseModel):
    """Single step in a processing report."""

    step: str
    status: str  # "success" | "warning" | "error"
    records_in: int
    records_out: int
    details: str = ""


class ProcessingReport(BaseModel):
    """Report generated after a pipeline run."""

    pipeline: str
    source: str
    status: str  # "success" | "partial" | "error"
    steps: list[ProcessingStep] = Field(default_factory=list)
    validation: ValidationResult | None = None
