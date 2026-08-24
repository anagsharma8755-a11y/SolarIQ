"""Tests for the weather data pipeline."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.config import SAMPLE_WEATHER_DIR
from data_pipeline.pipeline.weather_pipeline import (
    load_processed_weather,
    process_weather_data,
)
from data_pipeline.weather.cleaner import clean_weather_data
from data_pipeline.weather.loader import load_weather_data


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test outputs."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestWeatherLoader:
    """Tests for weather data loading."""

    def test_load_csv(self) -> None:
        """Load sample weather CSV."""
        path = SAMPLE_WEATHER_DIR / "mumbai_weather.csv"
        df = load_weather_data(path)

        assert len(df) > 0
        assert "temperature" in df.columns
        assert "humidity" in df.columns
        assert "wind_speed" in df.columns

    def test_load_nonexistent(self) -> None:
        """Loading non-existent file should raise."""
        with pytest.raises(FileNotFoundError):
            load_weather_data("/nonexistent/weather.csv")

    def test_unsupported_format(self, temp_dir: Path) -> None:
        """Unsupported format should raise ValueError."""
        path = temp_dir / "data.xml"
        path.write_text("<data/>")
        with pytest.raises(ValueError, match="Unsupported"):
            load_weather_data(path)


class TestWeatherCleaning:
    """Tests for weather data cleaning."""

    def test_basic_cleaning(self) -> None:
        """Clean sample data and verify output."""
        path = SAMPLE_WEATHER_DIR / "mumbai_weather.csv"
        df = load_weather_data(path)
        df_clean, report = clean_weather_data(df)

        assert report["rows_output"] > 0
        assert report["rows_output"] <= report["rows_input"]

    def test_handles_missing_values(self) -> None:
        """Missing values should be filled."""
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2024-01-15T08:00:00Z",
                    "2024-01-15T09:00:00Z",
                ],
                "latitude": [19.0, 19.0],
                "longitude": [72.8, 72.8],
                "temperature": [25.0, None],
                "humidity": [70.0, 65.0],
                "wind_speed": [5.0, 6.0],
                "cloud_cover": [30.0, 40.0],
                "precipitation": [0.0, 0.0],
            }
        )

        df_clean, report = clean_weather_data(df)

        assert df_clean["temperature"].isna().sum() == 0
        assert report["filled_missing"].get("temperature", 0) == 1

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
                "temperature": [25.0, 26.0, 27.0],
                "humidity": [70.0, 65.0, 60.0],
                "wind_speed": [5.0, 6.0, 7.0],
                "cloud_cover": [30.0, 40.0, 50.0],
                "precipitation": [0.0, 0.0, 0.0],
            }
        )

        df_clean, report = clean_weather_data(df)

        assert len(df_clean) == 2
        assert report["rows_removed_duplicates"] == 1

    def test_clips_out_of_range(self) -> None:
        """Out-of-range values should be clipped."""
        df = pd.DataFrame(
            {
                "timestamp": ["2024-01-15T08:00:00Z"],
                "latitude": [19.0],
                "longitude": [72.8],
                "temperature": [999.0],
                "humidity": [-5.0],
                "wind_speed": [5.0],
                "cloud_cover": [30.0],
                "precipitation": [0.0],
            }
        )

        df_clean, report = clean_weather_data(df)

        assert df_clean["temperature"].iloc[0] == 60.0
        assert df_clean["humidity"].iloc[0] == 0.0


class TestWeatherPipeline:
    """Tests for the complete weather pipeline."""

    def test_process_weather(self, temp_dir: Path) -> None:
        """Process weather data end-to-end."""
        source = SAMPLE_WEATHER_DIR / "mumbai_weather.csv"
        output = temp_dir / "weather_clean.csv"

        report = process_weather_data(source, output)

        assert report.status == "success"
        assert output.exists()
        assert output.stat().st_size > 0

    def test_report_structure(self, temp_dir: Path) -> None:
        """Report should have proper structure."""
        source = SAMPLE_WEATHER_DIR / "mumbai_weather.csv"
        output = temp_dir / "weather_clean.csv"

        report = process_weather_data(source, output)

        assert report.pipeline == "weather"
        assert len(report.steps) >= 3

    def test_load_processed(self, temp_dir: Path) -> None:
        """Load processed weather data."""
        source = SAMPLE_WEATHER_DIR / "mumbai_weather.csv"
        output = temp_dir / "weather_clean.csv"

        process_weather_data(source, output)

        df = load_processed_weather(output)
        assert len(df) > 0

    def test_load_processed_missing(self) -> None:
        """Loading from non-existent file should raise."""
        with pytest.raises(FileNotFoundError):
            load_processed_weather("/nonexistent/weather.csv")
