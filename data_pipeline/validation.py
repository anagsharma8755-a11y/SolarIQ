"""Reusable validation utilities for the data pipeline.

Provides structured validation of records with detailed error reporting.
"""

from __future__ import annotations

import math
from typing import Any

from data_pipeline.config import (
    HUMIDITY_MAX,
    HUMIDITY_MIN,
    IRRADIANCE_MAX,
    IRRADIANCE_MIN,
    LATITUDE_MAX,
    LATITUDE_MIN,
    LONGITUDE_MAX,
    LONGITUDE_MIN,
    PRECIPITATION_MAX,
    PRECIPITATION_MIN,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    WIND_SPEED_MAX,
    WIND_SPEED_MIN,
)
from data_pipeline.schemas import ValidationError, ValidationResult


def validate_latitude(value: float) -> str | None:
    """Return an error message if latitude is out of range, else None."""
    if not isinstance(value, (int, float)):
        return "Latitude must be numeric."
    if math.isnan(value) or math.isinf(value):
        return "Latitude must not be NaN or Infinity."
    if not (LATITUDE_MIN <= value <= LATITUDE_MAX):
        return (
            f"Latitude {value} is out of range "
            f"[{LATITUDE_MIN}, {LATITUDE_MAX}]."
        )
    return None


def validate_longitude(value: float) -> str | None:
    """Return an error message if longitude is out of range, else None."""
    if not isinstance(value, (int, float)):
        return "Longitude must be numeric."
    if math.isnan(value) or math.isinf(value):
        return "Longitude must not be NaN or Infinity."
    if not (LONGITUDE_MIN <= value <= LONGITUDE_MAX):
        return (
            f"Longitude {value} is out of range "
            f"[{LONGITUDE_MIN}, {LONGITUDE_MAX}]."
        )
    return None


def validate_timestamp(value: str) -> str | None:
    """Return an error message if timestamp is not parseable, else None."""
    if not isinstance(value, str) or not value.strip():
        return "Timestamp must be a non-empty string."
    # Quick check: must contain at least a date part
    if "T" not in value and " " not in value:
        # Could be just a date string like "2024-01-15"
        if len(value) == 10 and value.count("-") == 2:
            return None
        return f"Timestamp '{value}' does not match ISO-8601 format."
    return None


def validate_range(
    value: float,
    min_val: float,
    max_val: float,
    field_name: str,
) -> str | None:
    """Generic numeric range check."""
    if not isinstance(value, (int, float)):
        return f"{field_name} must be numeric."
    if math.isnan(value) or math.isinf(value):
        return f"{field_name} must not be NaN or Infinity."
    if not (min_val <= value <= max_val):
        return (
            f"{field_name} {value} is out of range "
            f"[{min_val}, {max_val}]."
        )
    return None


def validate_weather_record(
    record: dict[str, Any],
    index: int,
) -> list[ValidationError]:
    """Validate a single weather record, returning all errors found."""
    errors: list[ValidationError] = []

    # Latitude
    lat = record.get("latitude")
    if lat is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="latitude",
                error="Missing latitude.",
            )
        )
    else:
        err = validate_latitude(lat)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="latitude",
                    error=err,
                )
            )

    # Longitude
    lon = record.get("longitude")
    if lon is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="longitude",
                error="Missing longitude.",
            )
        )
    else:
        err = validate_longitude(lon)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="longitude",
                    error=err,
                )
            )

    # Timestamp
    ts = record.get("timestamp")
    if ts is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="timestamp",
                error="Missing timestamp.",
            )
        )
    else:
        err = validate_timestamp(ts)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="timestamp",
                    error=err,
                )
            )

    # Temperature
    temp = record.get("temperature")
    if temp is not None:
        err = validate_range(
            temp, TEMPERATURE_MIN, TEMPERATURE_MAX, "temperature"
        )
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="temperature",
                    error=err,
                )
            )

    # Humidity
    hum = record.get("humidity")
    if hum is not None:
        err = validate_range(
            hum, HUMIDITY_MIN, HUMIDITY_MAX, "humidity"
        )
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="humidity",
                    error=err,
                )
            )

    # Wind speed
    ws = record.get("wind_speed")
    if ws is not None:
        err = validate_range(
            ws, WIND_SPEED_MIN, WIND_SPEED_MAX, "wind_speed"
        )
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="wind_speed",
                    error=err,
                )
            )

    # Precipitation
    prec = record.get("precipitation")
    if prec is not None:
        err = validate_range(
            prec,
            PRECIPITATION_MIN,
            PRECIPITATION_MAX,
            "precipitation",
        )
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="precipitation",
                    error=err,
                )
            )

    return errors


def validate_solar_record(
    record: dict[str, Any],
    index: int,
) -> list[ValidationError]:
    """Validate a single solar radiation record."""
    errors: list[ValidationError] = []

    # Latitude / Longitude
    lat = record.get("latitude")
    if lat is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="latitude",
                error="Missing latitude.",
            )
        )
    else:
        err = validate_latitude(lat)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="latitude",
                    error=err,
                )
            )

    lon = record.get("longitude")
    if lon is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="longitude",
                error="Missing longitude.",
            )
        )
    else:
        err = validate_longitude(lon)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="longitude",
                    error=err,
                )
            )

    # Timestamp
    ts = record.get("timestamp")
    if ts is None:
        errors.append(
            ValidationError(
                record_index=index,
                field="timestamp",
                error="Missing timestamp.",
            )
        )
    else:
        err = validate_timestamp(ts)
        if err:
            errors.append(
                ValidationError(
                    record_index=index,
                    field="timestamp",
                    error=err,
                )
            )

    # Irradiance fields
    for field_name in ("ghi", "dni", "dhi", "solar_irradiance"):
        val = record.get(field_name)
        if val is not None:
            err = validate_range(
                val,
                IRRADIANCE_MIN,
                IRRADIANCE_MAX,
                field_name,
            )
            if err:
                errors.append(
                    ValidationError(
                        record_index=index,
                        field=field_name,
                        error=err,
                    )
                )

    return errors


def validate_building(
    building: dict[str, Any],
    index: int,
) -> list[ValidationError]:
    """Validate a standardized building record."""
    errors: list[ValidationError] = []

    # building_id
    bid = building.get("building_id")
    if not bid or not isinstance(bid, str):
        errors.append(
            ValidationError(
                record_index=index,
                field="building_id",
                error="Missing or invalid building_id.",
            )
        )

    # surfaces
    surfaces = building.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) == 0:
        errors.append(
            ValidationError(
                record_index=index,
                field="surfaces",
                error="Building must have at least one surface.",
            )
        )
    else:
        for s_idx, surface in enumerate(surfaces):
            verts = surface.get("vertices")
            if not isinstance(verts, list) or len(verts) < 3:
                errors.append(
                    ValidationError(
                        record_index=index,
                        field=f"surfaces[{s_idx}].vertices",
                        error="Surface must have at least 3 vertices.",
                    )
                )

    # coordinates
    coords = building.get("coordinates")
    if coords is not None:
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat is not None:
            err = validate_latitude(lat)
            if err:
                errors.append(
                    ValidationError(
                        record_index=index,
                        field="coordinates.latitude",
                        error=err,
                    )
                )
        if lon is not None:
            err = validate_longitude(lon)
            if err:
                errors.append(
                    ValidationError(
                        record_index=index,
                        field="coordinates.longitude",
                        error=err,
                    )
                )

    return errors


def build_validation_result(
    total: int,
    errors: list[ValidationError],
) -> ValidationResult:
    """Build a ``ValidationResult`` from a list of errors."""
    unique_error_indices = set(e.record_index for e in errors)
    return ValidationResult(
        valid=len(errors) == 0,
        records_total=total,
        records_valid=total - len(unique_error_indices),
        records_invalid=len(unique_error_indices),
        errors=errors,
    )
