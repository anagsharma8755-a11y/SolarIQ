"""Tests for weather data providers.

All tests work offline - network calls are mocked.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from data_pipeline.weather.providers import (
    OpenMeteoProvider,
    LocalWeatherProvider,
    get_weather_provider,
)


@pytest.fixture
def temp_dir() -> Path:
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestWeatherProviderFactory:
    """Tests for weather provider factory."""

    def test_get_local_provider(self) -> None:
        provider = get_weather_provider("local")
        assert isinstance(provider, LocalWeatherProvider)
        assert provider.name == "local"

    def test_get_open_meteo_provider(self) -> None:
        provider = get_weather_provider("open-meteo")
        assert isinstance(provider, OpenMeteoProvider)
        assert provider.name == "open-meteo"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider"):
            get_weather_provider("nonexistent")


class TestLocalWeatherProvider:
    """Tests for local file weather provider."""

    def test_load_csv(self, temp_dir: Path) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, 19.0],
            "longitude": [72.8, 72.8],
            "temperature": [25.0, 26.0],
            "humidity": [70.0, 65.0],
            "wind_speed": [5.0, 6.0],
            "cloud_cover": [30.0, 40.0],
            "precipitation": [0.0, 0.0],
        })
        path = temp_dir / "weather.csv"
        df.to_csv(path, index=False)

        provider = LocalWeatherProvider()
        result = provider.load_file(path)

        assert len(result) == 2
        assert "temperature" in result.columns

    def test_load_json(self, temp_dir: Path) -> None:
        data = {
            "records": [
                {
                    "timestamp": "2024-01-15T08:00:00Z",
                    "latitude": 19.0,
                    "longitude": 72.8,
                    "temp": 25.0,
                    "rh": 70.0,
                }
            ]
        }
        path = temp_dir / "weather.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        provider = LocalWeatherProvider()
        result = provider.load_file(path)

        assert len(result) == 1
        assert "temperature" in result.columns
        assert "humidity" in result.columns

    def test_unsupported_format(self, temp_dir: Path) -> None:
        path = temp_dir / "data.xml"
        path.write_text("<data/>")

        provider = LocalWeatherProvider()
        with pytest.raises(ValueError, match="Unsupported"):
            provider.load_file(path)

    def test_column_normalization(self, temp_dir: Path) -> None:
        df = pd.DataFrame({
            "time": ["2024-01-15T08:00:00Z"],
            "lat": [19.0],
            "lon": [72.8],
            "temp_c": [25.0],
            "relative_humidity": [70.0],
            "wind": [5.0],
        })
        path = temp_dir / "weather.csv"
        df.to_csv(path, index=False)

        provider = LocalWeatherProvider()
        result = provider.load_file(path)

        assert "timestamp" in result.columns
        assert "latitude" in result.columns
        assert "longitude" in result.columns
        assert "temperature" in result.columns
        assert "humidity" in result.columns
        assert "wind_speed" in result.columns


class TestOpenMeteoProvider:
    """Tests for Open-Meteo provider (mocked network)."""

    def test_fetch_mocked(self) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "hourly": {
                "time": ["2024-01-15T08:00", "2024-01-15T09:00"],
                "temperature_2m": [25.0, 26.0],
                "relative_humidity_2m": [70.0, 65.0],
                "cloud_cover": [30.0, 40.0],
                "wind_speed_10m": [5.0, 6.0],
                "precipitation": [0.0, 0.0],
                "pressure_msl": [1013.0, 1012.0],
            }
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            provider = OpenMeteoProvider()
            df = provider.fetch(19.076, 72.878, "2024-01-15", "2024-01-15")

        assert len(df) == 2
        assert "temperature" in df.columns
        assert "humidity" in df.columns

    def test_fetch_network_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=ConnectionError("offline")):
            provider = OpenMeteoProvider()
            with pytest.raises(ConnectionError, match="Open-Meteo"):
                provider.fetch(19.076, 72.878, "2024-01-15", "2024-01-15")
