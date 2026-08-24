"""Data quality reporting module.

Generates comprehensive validation reports containing:
- Record count
- Missing values
- Duplicates
- Invalid coordinates
- Invalid timestamps
- Outliers
- CRS metadata
- Source information
- Processing timestamp
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from data_pipeline.config import (
    LATITUDE_MAX, LATITUDE_MIN,
    LONGITUDE_MAX, LONGITUDE_MIN,
)

logger = logging.getLogger(__name__)


class DataQualityReport:
    """Structured data quality report."""

    def __init__(
        self,
        source: str,
        dataset_type: str,
        crs: str = "EPSG:4326",
    ) -> None:
        self.source = source
        self.dataset_type = dataset_type
        self.crs = crs
        self.processing_timestamp = datetime.now(timezone.utc).isoformat()
        self.record_count = 0
        self.missing_values: dict[str, int] = {}
        self.duplicate_count = 0
        self.invalid_coordinates = 0
        self.invalid_timestamps = 0
        self.outliers: dict[str, int] = {}
        self.quality_score = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "source": self.source,
            "dataset_type": self.dataset_type,
            "crs": self.crs,
            "processing_timestamp": self.processing_timestamp,
            "record_count": self.record_count,
            "missing_values": self.missing_values,
            "duplicate_count": self.duplicate_count,
            "invalid_coordinates": self.invalid_coordinates,
            "invalid_timestamps": self.invalid_timestamps,
            "outliers": self.outliers,
            "quality_score": round(self.quality_score, 4),
        }


def generate_quality_report(
    df: pd.DataFrame,
    source: str,
    dataset_type: str = "unknown",
    crs: str = "EPSG:4326",
    timestamp_col: str = "timestamp",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    outlier_columns: list[str] | None = None,
) -> DataQualityReport:
    """Generate a comprehensive data quality report for a DataFrame.

    Args:
        df: Input DataFrame.
        source: Data source identifier.
        dataset_type: Type of dataset (weather, solar, building, etc.).
        crs: Coordinate Reference System.
        timestamp_col: Name of timestamp column.
        lat_col: Name of latitude column.
        lon_col: Name of longitude column.
        outlier_columns: Columns to check for outliers.

    Returns:
        DataQualityReport with all findings.
    """
    report = DataQualityReport(source=source, dataset_type=dataset_type, crs=crs)
    report.record_count = len(df)

    if df.empty:
        report.quality_score = 1.0
        return report

    # --- Missing values ---
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing > 0:
            report.missing_values[col] = n_missing

    # --- Duplicates ---
    if timestamp_col in df.columns:
        report.duplicate_count = int(
            df.duplicated(subset=[timestamp_col], keep="first").sum()
        )

    # --- Invalid coordinates ---
    if lat_col in df.columns and lon_col in df.columns:
        lat_valid = df[lat_col].notna() & df[lat_col].apply(
            lambda x: LATITUDE_MIN <= x <= LATITUDE_MAX if pd.notna(x) else False
        )
        lon_valid = df[lon_col].notna() & df[lon_col].apply(
            lambda x: LONGITUDE_MIN <= x <= LONGITUDE_MAX if pd.notna(x) else False
        )
        invalid = (~lat_valid) | (~lon_valid)
        report.invalid_coordinates = int(invalid.sum())

    # --- Invalid timestamps ---
    if timestamp_col in df.columns:
        try:
            parsed = pd.to_datetime(df[timestamp_col], errors="coerce")
            report.invalid_timestamps = int(parsed.isna().sum())
        except Exception:
            report.invalid_timestamps = 0

    # --- Outliers (IQR method) ---
    if outlier_columns is None:
        outlier_columns = [
            c for c in df.columns
            if df[c].dtype in ("float64", "int64", "float32", "int32")
        ]

    for col in outlier_columns:
        if col in df.columns:
            series = df[col].dropna()
            if len(series) < 4:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower = q1 - 3.0 * iqr
            upper = q3 + 3.0 * iqr
            n_outliers = int(((series < lower) | (series > upper)).sum())
            if n_outliers > 0:
                report.outliers[col] = n_outliers

    # --- Quality score ---
    total_records = report.record_count
    if total_records > 0:
        issues = (
            sum(report.missing_values.values())
            + report.duplicate_count
            + report.invalid_coordinates
            + report.invalid_timestamps
            + sum(report.outliers.values())
        )
        report.quality_score = max(0.0, 1.0 - (issues / total_records))
    else:
        report.quality_score = 0.0

    logger.info(
        "Quality report for %s: %d records, score=%.4f",
        source, total_records, report.quality_score,
    )

    return report
