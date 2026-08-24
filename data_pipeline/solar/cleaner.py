"""Solar radiation data cleaner.

Handles missing values, duplicate timestamps, invalid readings,
and generates cleaning reports.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from data_pipeline.config import IRRADIANCE_MAX, IRRADIANCE_MIN

logger = logging.getLogger(__name__)


def _convert_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to parse the timestamp column."""
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], errors="coerce"
        )
    return df


def _remove_duplicate_timestamps(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
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
    """Fill missing irradiance values with 0.

    Missing solar data during nighttime is expected to be 0.
    """
    filled: dict[str, int] = {}

    for col in ("ghi", "dni", "dhi", "solar_irradiance"):
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                df[col] = df[col].fillna(0.0)
                filled[col] = int(n_missing)

    return filled


def _compute_solar_irradiance(df: pd.DataFrame) -> pd.DataFrame:
    """Compute solar_irradiance from GHI if not already present.

    If solar_irradiance is missing but ghi is available,
    use ghi as the total irradiance.
    """
    if (
        "solar_irradiance" not in df.columns
        and "ghi" in df.columns
    ):
        df["solar_irradiance"] = df["ghi"]
        logger.info(
            "Computed solar_irradiance from GHI."
        )

    return df


def clean_solar_data(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean a solar radiation DataFrame.

    Steps:
    1. Parse timestamps
    2. Remove rows with missing required fields
    3. Remove duplicate timestamps
    4. Clip out-of-range irradiance values
    5. Fill missing values
    6. Compute derived fields

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

    # Step 4: Clip out-of-range irradiance values
    irradiance_fields = ["ghi", "dni", "dhi", "solar_irradiance"]

    for field in irradiance_fields:
        clipped = _clip_range(
            df, field, IRRADIANCE_MIN, IRRADIANCE_MAX
        )
        if clipped > 0:
            report["clipped"][field] = clipped

    # Step 5: Fill missing values
    report["filled_missing"] = _fill_missing_values(df)

    # Step 6: Compute derived fields
    df = _compute_solar_irradiance(df)

    # Reset index
    df = df.reset_index(drop=True)

    # Format timestamp back to ISO string
    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    report["rows_output"] = len(df)

    logger.info(
        "Solar cleaning complete: %d → %d rows.",
        report["rows_input"],
        report["rows_output"],
    )

    return df, report
