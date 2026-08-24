"""Solar radiation data validator.

Validates solar data against defined constraints and
produces structured ``ValidationResult`` objects.
"""

from __future__ import annotations

import pandas as pd

from data_pipeline.schemas import ValidationResult
from data_pipeline.validation import build_validation_result


def validate_solar_df(df: pd.DataFrame) -> ValidationResult:
    """Validate a solar radiation DataFrame.

    Returns a ``ValidationResult`` with detailed error information.
    """
    errors = []

    required_fields = [
        "timestamp",
        "latitude",
        "longitude",
    ]

    # Check for required columns
    for field in required_fields:
        if field not in df.columns:
            errors.append(
                {
                    "record_index": -1,
                    "field": field,
                    "error": f"Missing required column: {field}",
                }
            )

    if errors:
        return build_validation_result(len(df), errors)

    # Validate each row
    for idx, row in df.iterrows():
        record = row.to_dict()
        row_errors = _validate_single_solar_record(record, idx)
        errors.extend(row_errors)

    return build_validation_result(len(df), errors)


def _validate_single_solar_record(
    record: dict,
    index: int,
) -> list[dict]:
    """Validate a single solar record."""
    errors = []

    # Latitude
    lat = record.get("latitude")
    if pd.notna(lat):
        if not (-90.0 <= float(lat) <= 90.0):
            errors.append(
                {
                    "record_index": index,
                    "field": "latitude",
                    "error": f"Latitude {lat} out of range.",
                }
            )

    # Longitude
    lon = record.get("longitude")
    if pd.notna(lon):
        if not (-180.0 <= float(lon) <= 180.0):
            errors.append(
                {
                    "record_index": index,
                    "field": "longitude",
                    "error": f"Longitude {lon} out of range.",
                }
            )

    # Timestamp
    ts = record.get("timestamp")
    if pd.isna(ts):
        errors.append(
            {
                "record_index": index,
                "field": "timestamp",
                "error": "Missing timestamp.",
            }
        )

    # Irradiance values should be non-negative
    for field in ("ghi", "dni", "dhi", "solar_irradiance"):
        val = record.get(field)
        if pd.notna(val):
            if float(val) < 0:
                errors.append(
                    {
                        "record_index": index,
                        "field": field,
                        "error": f"{field} is negative: {val}.",
                    }
                )

    return errors
