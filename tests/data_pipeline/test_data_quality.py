"""Tests for data quality reporting."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.quality import DataQualityReport, generate_quality_report


class TestDataQualityReport:
    """Tests for data quality report generation."""

    def test_clean_data(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, 19.0],
            "longitude": [72.8, 72.8],
            "temperature": [25.0, 26.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert report.record_count == 2
        assert report.quality_score == 1.0
        assert report.invalid_coordinates == 0
        assert report.duplicate_count == 0

    def test_missing_values(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, None],
            "longitude": [72.8, 72.8],
            "temperature": [25.0, 26.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert "latitude" in report.missing_values
        assert report.missing_values["latitude"] == 1
        assert report.quality_score < 1.0

    def test_duplicates(self) -> None:
        df = pd.DataFrame({
            "timestamp": [
                "2024-01-15T08:00:00Z",
                "2024-01-15T08:00:00Z",
                "2024-01-15T09:00:00Z",
            ],
            "latitude": [19.0, 19.0, 19.0],
            "longitude": [72.8, 72.8, 72.8],
            "temperature": [25.0, 25.0, 26.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert report.duplicate_count == 1

    def test_invalid_coordinates(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, 999.0],
            "longitude": [72.8, 72.8],
            "temperature": [25.0, 26.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert report.invalid_coordinates == 1

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame({
            "timestamp": [],
            "latitude": [],
            "longitude": [],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert report.record_count == 0
        assert report.quality_score == 1.0

    def test_report_to_dict(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z"],
            "latitude": [19.0],
            "longitude": [72.8],
            "temperature": [25.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")
        d = report.to_dict()

        assert "source" in d
        assert "crs" in d
        assert "processing_timestamp" in d
        assert "quality_score" in d
        assert d["crs"] == "EPSG:4326"

    def test_custom_crs(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z"],
            "latitude": [19.0],
            "longitude": [72.8],
            "temperature": [25.0],
        })

        report = generate_quality_report(
            df, source="test.csv", dataset_type="weather",
            crs="EPSG:32643",
        )

        assert report.crs == "EPSG:32643"

    def test_outlier_detection(self) -> None:
        # Create data with variance so IQR method works
        values = [20.0, 22.0, 24.0, 25.0, 25.5, 26.0, 27.0, 28.0, 30.0, 32.0, 500.0]
        n = len(values)
        df = pd.DataFrame({
            "timestamp": [f"2024-01-15T{i:02d}:00:00Z" for i in range(n)],
            "latitude": [19.0] * n,
            "longitude": [72.8] * n,
            "temperature": values,
        })

        report = generate_quality_report(
            df, source="test.csv", dataset_type="weather",
            outlier_columns=["temperature"],
        )

        assert "temperature" in report.outliers
        assert report.outliers["temperature"] >= 1

    def test_invalid_timestamps(self) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "not-a-date", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, 19.0, 19.0],
            "longitude": [72.8, 72.8, 72.8],
            "temperature": [25.0, 26.0, 27.0],
        })

        report = generate_quality_report(df, source="test.csv", dataset_type="weather")

        assert report.invalid_timestamps == 1
