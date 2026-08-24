"""Tests for the solar radiation data pipeline."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.config import SAMPLE_SOLAR_DIR
from data_pipeline.pipeline.solar_pipeline import (
    load_processed_solar,
    process_solar_data,
)
from data_pipeline.solar.cleaner import clean_solar_data
from data_pipeline.solar.loader import load_solar_data


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test outputs."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestSolarLoader:
    """Tests for solar data loading."""

    def test_load_csv(self) -> None:
        """Load sample solar CSV."""
        path = SAMPLE_SOLAR_DIR / "mumbai_solar.csv"
        df = load_solar_data(path)

        assert len(df) > 0
        assert "ghi" in df.columns
        assert "dni" in df.columns
        assert "dhi" in df.columns

    def test_load_nonexistent(self) -> None:
        """Loading non-existent file should raise."""
        with pytest.raises(FileNotFoundError):
            load_solar_data("/nonexistent/solar.csv")


class TestSolarCleaning:
    """Tests for solar data cleaning."""

    def test_basic_cleaning(self) -> None:
        """Clean sample data and verify output."""
        path = SAMPLE_SOLAR_DIR / "mumbai_solar.csv"
        df = load_solar_data(path)
        df_clean, report = clean_solar_data(df)

        assert report["rows_output"] > 0
        assert report["rows_output"] <= report["rows_input"]

    def test_handles_missing_values(self) -> None:
        """Missing irradiance values should be filled with 0."""
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2024-01-15T08:00:00Z",
                    "2024-01-15T09:00:00Z",
                ],
                "latitude": [19.0, 19.0],
                "longitude": [72.8, 72.8],
                "ghi": [500.0, None],
                "dni": [700.0, 750.0],
                "dhi": [200.0, 210.0],
                "solar_irradiance": [500.0, None],
            }
        )

        df_clean, report = clean_solar_data(df)

        assert df_clean["ghi"].isna().sum() == 0
        assert df_clean["solar_irradiance"].isna().sum() == 0

    def test_removes_duplicates(self) -> None:
        """Duplicate timestamps should be removed."""
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2024-01-15T08:00:00Z",
                    "2024-01-15T08:00:00Z",
                    "2024-01-15T09:00:00Z",
                ],
                "latitude": [19.0, 19.0, 19.0],
                "longitude": [72.8, 72.8, 72.8],
                "ghi": [500.0, 550.0, 600.0],
                "dni": [700.0, 720.0, 740.0],
                "dhi": [200.0, 210.0, 220.0],
                "solar_irradiance": [500.0, 550.0, 600.0],
            }
        )

        df_clean, report = clean_solar_data(df)

        assert len(df_clean) == 2
        assert report["rows_removed_duplicates"] == 1

    def test_computes_solar_irradiance(self) -> None:
        """solar_irradiance should be computed from GHI if missing."""
        df = pd.DataFrame(
            {
                "timestamp": ["2024-01-15T08:00:00Z"],
                "latitude": [19.0],
                "longitude": [72.8],
                "ghi": [500.0],
                "dni": [700.0],
                "dhi": [200.0],
            }
        )

        df_clean, _ = clean_solar_data(df)

        assert "solar_irradiance" in df_clean.columns
        assert df_clean["solar_irradiance"].iloc[0] == 500.0


class TestSolarPipeline:
    """Tests for the complete solar pipeline."""

    def test_process_solar(self, temp_dir: Path) -> None:
        """Process solar data end-to-end."""
        source = SAMPLE_SOLAR_DIR / "mumbai_solar.csv"
        output = temp_dir / "solar_clean.csv"

        report = process_solar_data(source, output)

        assert report.status == "success"
        assert output.exists()

    def test_report_structure(self, temp_dir: Path) -> None:
        """Report should have proper structure."""
        source = SAMPLE_SOLAR_DIR / "mumbai_solar.csv"
        output = temp_dir / "solar_clean.csv"

        report = process_solar_data(source, output)

        assert report.pipeline == "solar"
        assert len(report.steps) >= 3

    def test_load_processed(self, temp_dir: Path) -> None:
        """Load processed solar data."""
        source = SAMPLE_SOLAR_DIR / "mumbai_solar.csv"
        output = temp_dir / "solar_clean.csv"

        process_solar_data(source, output)

        df = load_processed_solar(output)
        assert len(df) > 0

    def test_load_processed_missing(self) -> None:
        """Loading from non-existent file should raise."""
        with pytest.raises(FileNotFoundError):
            load_processed_solar("/nonexistent/solar.csv")
