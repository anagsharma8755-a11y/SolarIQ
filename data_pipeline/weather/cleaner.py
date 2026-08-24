"""Weather data cleaner.

Handles missing values, duplicate timestamps, invalid readings,
and generates cleaning reports.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from data_pipeline.config import (
    CLOUD_COVER_MAX,
    CLOUD_COVER_MIN,
    HUMIDITY_MAX,
    HUMIDITY_MIN,
    PRECIPITATION_MAX,
    PRECIPITATION_MIN,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    WIND_SPEED_MAX,
    WIND_SPEED_MIN,
)

logger = logging.getLogger(__name__)


def _convert_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to parse the timestamp column."""
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], errors="coerce"
        )
    return df


def _remove_duplicate_timestamps(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove duplicate timestamp rows, keeping the first occurrence."""
    before = len(df)

    if "timestamp" in df.columns:
        df = df.drop_duplicates(subset=["timestamp"], keep="first")

    removed = before - len(df)
    return df, removed


def _remove_rows_with_missing_required_fields(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Remove rows where any required field is missing."""
    required = [
        "timestamp",
        "latitude",
        "longitude",
    ]

    present_required = [c for c in required if c in df.columns]

    before = len(df)

    if present_required:
        df = df.dropna(subset=present_required)

    removed = before - len(df)
    return df, removed


def _clip_range(
    df: pd.DataFrame,
    column: str,
    min_val: float,
    max_val: float,
) -> int:
    """Clip values in a column to [min_val, max_val].

    Returns the number of out-of-range values that were clipped.
    """
    if column not in df.columns:
        return 0

    out_of_range = (
        (df[column] < min_val) | (df[column] > max_val)
    ).sum()

    df[column] = df[column].clip(lower=min_val, upper=max_val)

    return int(out_of_range)


def _fill_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Fill missing values with sensible defaults or interpolate.

    Returns a dict of how many values were filled per column.
    """
    filled: dict[str, int] = {}

    # Temperature: interpolate
    if "temperature" in df.columns:
        n_missing = df["temperature"].isna().sum()
        if n_missing > 0:
            df["temperature"] = df["temperature"].interpolate(
                method="linear"
            )
            filled["temperature"] = int(n_missing)

    # Humidity: fill with median
    if "humidity" in df.columns:
        n_missing = df["humidity"].isna().sum()
        if n_missing > 0:
            median_val = df["humidity"].median()
            df["humidity"] = df["humidity"].fillna(median_val)
            filled["humidity"] = int(n_missing)

    # Wind speed: fill with median
    if "wind_speed" in df.columns:
        n_missing = df["wind_speed"].isna().sum()
        if n_missing > 0:
            median_val = df["wind_speed"].median()
            df["wind_speed"] = df["wind_speed"].fillna(median_val)
            filled["wind_speed"] = int(n_missing)

    # Cloud cover: fill with median
    if "cloud_cover" in df.columns:
        n_missing = df["cloud_cover"].isna().sum()
        if n_missing > 0:
            median_val = df["cloud_cover"].median()
            df["cloud_cover"] = df["cloud_cover"].fillna(median_val)
            filled["cloud_cover"] = int(n_missing)

    # Precipitation: fill with 0 (no rain is the default)
    if "precipitation" in df.columns:
        n_missing = df["precipitation"].isna().sum()
        if n_missing > 0:
            df["precipitation"] = df["precipitation"].fillna(0.0)
            filled["precipitation"] = int(n_missing)

    return filled


def clean_weather_data(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean a weather DataFrame.

    Steps:
    1. Parse timestamps
    2. Remove rows with missing required fields
    3. Remove duplicate timestamps
    4. Clip out-of-range values
    5. Fill remaining missing values

    Returns:
        (cleaned DataFrame, cleaning report)
    """
    report: dict[str, Any] = {
        "rows_input": len(df),
        "rows_removed_missing": 0,
        "rows_removed_duplicates": 0,
        "clipped": {},
        "filled_missing": {},
        "rows_output": 0,
    }

    # Step 1: Parse timestamps
    df = _convert_timestamps(df)

    # Step 2: Remove rows with missing required fields
    df, removed_missing = _remove_rows_with_missing_required_fields(df)
    report["rows_removed_missing"] = removed_missing

    # Step 3: Remove duplicate timestamps
    df, removed_dups = _remove_duplicate_timestamps(df)
    report["rows_removed_duplicates"] = removed_dups

    # Step 4: Clip out-of-range values
    clip_ranges = {
        "temperature": (TEMPERATURE_MIN, TEMPERATURE_MAX),
        "humidity": (HUMIDITY_MIN, HUMIDITY_MAX),
        "wind_speed": (WIND_SPEED_MIN, WIND_SPEED_MAX),
        "cloud_cover": (CLOUD_COVER_MIN, CLOUD_COVER_MAX),
        "precipitation": (PRECIPITATION_MIN, PRECIPITATION_MAX),
    }

    for col, (min_val, max_val) in clip_ranges.items():
        clipped = _clip_range(df, col, min_val, max_val)
        if clipped > 0:
            report["clipped"][col] = clipped

    # Step 5: Fill remaining missing values
    report["filled_missing"] = _fill_missing_values(df)

    # Reset index
    df = df.reset_index(drop=True)

    # Format timestamp back to ISO string
    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    report["rows_output"] = len(df)

    logger.info(
        "Weather cleaning complete: %d → %d rows.",
        report["rows_input"],
        report["rows_output"],
    )

    return df, report
