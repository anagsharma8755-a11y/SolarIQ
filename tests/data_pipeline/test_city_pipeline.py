"""Tests for the city data pipeline."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from data_pipeline.pipeline.city_pipeline import (
    load_for_backend,
    process_city_data,
)
from data_pipeline.config import SAMPLE_CITY_DIR


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test outputs."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestCityPipeline:
    """Tests for the city data pipeline."""

    def test_process_geojson(self, temp_dir: Path) -> None:
        """Process a GeoJSON file and verify output."""
        source = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        output = temp_dir / "city_output.json"

        report = process_city_data(source, output)

        assert report.status == "success"
        assert output.exists()

        with output.open("r") as f:
            data = json.load(f)

        assert "buildings" in data
        assert len(data["buildings"]) == 5

        for building in data["buildings"]:
            assert "building_id" in building
            assert "surfaces" in building
            assert len(building["surfaces"]) > 0

    def test_process_json(self, temp_dir: Path) -> None:
        """Process a city JSON file."""
        source = SAMPLE_CITY_DIR / "mumbai_buildings.json"
        output = temp_dir / "city_output.json"

        report = process_city_data(source, output)

        assert report.status == "success"
        assert output.exists()

    def test_utm_conversion(self, temp_dir: Path) -> None:
        """Verify UTM coordinates are generated."""
        source = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        output = temp_dir / "city_output.json"

        report = process_city_data(source, output, convert_to_utm=True)

        with output.open("r") as f:
            data = json.load(f)

        for building in data["buildings"]:
            if "utm" in building:
                utm = building["utm"]
                assert "easting" in utm
                assert "northing" in utm
                assert "zone" in utm
                assert "hemisphere" in utm
                assert utm["easting"] > 0

    def test_load_for_backend(self, temp_dir: Path) -> None:
        """Verify processed data loads in backend-compatible format."""
        source = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        output = temp_dir / "city_output.json"

        process_city_data(source, output)

        buildings = load_for_backend(output)

        assert len(buildings) == 5

        for b in buildings:
            assert "building_id" in b
            assert "surfaces" in b

    def test_load_for_backend_missing_file(self) -> None:
        """Loading from non-existent file should raise."""
        with pytest.raises(FileNotFoundError):
            load_for_backend("/nonexistent/path.json")

    def test_report_has_steps(self, temp_dir: Path) -> None:
        """Report should contain processing steps."""
        source = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        output = temp_dir / "city_output.json"

        report = process_city_data(source, output)

        assert len(report.steps) >= 4  # load, clean, validate, save

        step_names = [s.step for s in report.steps]
        assert "load" in step_names
        assert "clean" in step_names
        assert "validate" in step_names
        assert "save" in step_names

    def test_source_file_not_found(self, temp_dir: Path) -> None:
        """Non-existent source should return error report."""
        output = temp_dir / "city_output.json"

        report = process_city_data(
            "/nonexistent/file.geojson", output
        )

        assert report.status == "error"

    def test_metadata_in_output(self, temp_dir: Path) -> None:
        """Output should contain metadata."""
        source = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        output = temp_dir / "city_output.json"

        process_city_data(source, output)

        with output.open("r") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "building_count" in data["metadata"]
        assert "source_hash" in data["metadata"]
