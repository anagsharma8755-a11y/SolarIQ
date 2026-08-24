"""Tests for solar data providers.

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

from data_pipeline.solar.providers import (
    FallbackSolarProvider,
    LocalSolarProvider,
    get_solar_provider,
)


@pytest.fixture
def temp_dir() -> Path:
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestSolarProviderFactory:
    """Tests for solar provider factory."""

    def test_get_local_provider(self) -> None:
        provider = get_solar_provider("local")
        assert isinstance(provider, LocalSolarProvider)
        assert provider.name == "local"

    def test_get_fallback_provider(self) -> None:
        provider = get_solar_provider("fallback")
        assert isinstance(provider, FallbackSolarProvider)
        assert provider.name == "fallback"
        assert provider.data_quality == "fallback"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider"):
            get_solar_provider("nonexistent")


class TestFallbackSolarProvider:
    """Tests for fallback solar provider."""

    def test_generates_data(self) -> None:
        provider = FallbackSolarProvider()
        df = provider.fetch(19.076, 72.878, "2024-01-15T00:00:00", "2024-01-15T23:00:00")

        assert len(df) > 0
        assert "ghi" in df.columns
        assert "dni" in df.columns
        assert "dhi" in df.columns
        assert "solar_irradiance" in df.columns

    def test_solar_shape(self) -> None:
        provider = FallbackSolarProvider()
        df = provider.fetch(19.076, 72.878, "2024-01-15T00:00:00", "2024-01-15T23:00:00")

        # 24 hours in a day
        assert len(df) == 24

    def test_night_zero(self) -> None:
        provider = FallbackSolarProvider()
        df = provider.fetch(19.076, 72.878, "2024-01-15T00:00:00", "2024-01-15T23:00:00")

        # Hour 0 (midnight) should have zero GHI
        assert df.iloc[0]["ghi"] == 0.0

    def test_non_negative(self) -> None:
        provider = FallbackSolarProvider()
        df = provider.fetch(19.076, 72.878, "2024-01-15T00:00:00", "2024-01-15T23:00:00")

        assert (df["ghi"] >= 0).all()
        assert (df["dni"] >= 0).all()
        assert (df["dhi"] >= 0).all()


class TestLocalSolarProvider:
    """Tests for local file solar provider."""

    def test_load_csv(self, temp_dir: Path) -> None:
        df = pd.DataFrame({
            "timestamp": ["2024-01-15T08:00:00Z", "2024-01-15T09:00:00Z"],
            "latitude": [19.0, 19.0],
            "longitude": [72.8, 72.8],
            "ghi": [500.0, 600.0],
            "dni": [700.0, 740.0],
            "dhi": [200.0, 220.0],
            "solar_irradiance": [500.0, 600.0],
        })
        path = temp_dir / "solar.csv"
        df.to_csv(path, index=False)

        provider = LocalSolarProvider()
        result = provider.load_file(path)

        assert len(result) == 2
        assert "ghi" in result.columns

    def test_load_json(self, temp_dir: Path) -> None:
        data = {
            "records": [
                {
                    "timestamp": "2024-01-15T08:00:00Z",
                    "latitude": 19.0,
                    "longitude": 72.8,
                    "global_horizontal": 500.0,
                    "direct_normal": 700.0,
                    "diffuse_horizontal": 200.0,
                    "solar_irradiance": 500.0,
                }
            ]
        }
        path = temp_dir / "solar.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        provider = LocalSolarProvider()
        result = provider.load_file(path)

        assert len(result) == 1
        assert "ghi" in result.columns
        assert "dni" in result.columns
        assert "dhi" in result.columns

    def test_unsupported_format(self, temp_dir: Path) -> None:
        path = temp_dir / "data.xml"
        path.write_text("<data/>")

        provider = LocalSolarProvider()
        with pytest.raises(ValueError, match="Unsupported"):
            provider.load_file(path)


class TestSolarDataQuality:
    """Tests for data quality distinction."""

    def test_fallback_quality(self) -> None:
        provider = FallbackSolarProvider()
        assert provider.data_quality == "fallback"

    def test_local_quality(self) -> None:
        provider = LocalSolarProvider()
        assert provider.data_quality == "real"
