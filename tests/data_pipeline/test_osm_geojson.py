"""Tests for OSM GeoJSON loader and OSM pipeline.

All tests work offline - network calls are mocked.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from data_pipeline.osm.geojson_loader import (
    geojson_to_buildings,
    load_geojson_file,
    load_osm_buildings,
)
from data_pipeline.osm.parser import parse_osm_elements
from data_pipeline.pipeline.osm_pipeline import process_osm_data


@pytest.fixture
def temp_dir() -> Path:
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_osm_data() -> dict:
    """Sample OSM Overpass JSON response."""
    return {
        "elements": [
            {
                "type": "node",
                "id": 1001,
                "lat": 19.076,
                "lon": 72.878,
            },
            {
                "type": "node",
                "id": 1002,
                "lat": 19.077,
                "lon": 72.878,
            },
            {
                "type": "node",
                "id": 1003,
                "lat": 19.077,
                "lon": 72.879,
            },
            {
                "type": "node",
                "id": 1004,
                "lat": 19.076,
                "lon": 72.879,
            },
            {
                "type": "way",
                "id": 2001,
                "nodes": [1001, 1002, 1003, 1004, 1001],
                "tags": {
                    "building": "yes",
                    "name": "Test Building",
                    "height": "25m",
                    "building:levels": "5",
                },
            },
            {
                "type": "way",
                "id": 2002,
                "nodes": [1001, 1002, 1003, 1004, 1001],
                "tags": {
                    "building": "yes",
                    "name": "Another Building",
                },
            },
        ]
    }


@pytest.fixture
def sample_geojson() -> dict:
    """Sample GeoJSON with building features."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "GEO-001",
                    "name": "GeoJSON Building",
                    "building": "yes",
                    "height": 20.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.878, 19.076],
                        [72.879, 19.076],
                        [72.879, 19.077],
                        [72.878, 19.077],
                        [72.878, 19.076],
                    ]],
                },
            },
        ],
    }


class TestGeoJSONLoader:
    """Tests for GeoJSON file loading."""

    def test_load_geojson_file(self, temp_dir: Path, sample_geojson: dict) -> None:
        path = temp_dir / "buildings.geojson"
        path.write_text(json.dumps(sample_geojson), encoding="utf-8")

        data = load_geojson_file(path)
        assert "features" in data
        assert len(data["features"]) == 1

    def test_load_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_geojson_file("/nonexistent/file.geojson")

    def test_load_invalid_geojson(self, temp_dir: Path) -> None:
        path = temp_dir / "bad.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection"}), encoding="utf-8")

        with pytest.raises(ValueError, match="missing 'features'"):
            load_geojson_file(path)


class TestGeoJSONToBuildings:
    """Tests for GeoJSON to building conversion."""

    def test_convert_polygon(self, sample_geojson: dict) -> None:
        buildings = geojson_to_buildings(sample_geojson)
        assert len(buildings) == 1
        b = buildings[0]
        assert b["osm_id"] == "GEO-001"
        assert b["properties"]["name"] == "GeoJSON Building"
        assert len(b["coordinates"]) >= 4

    def test_convert_empty(self) -> None:
        buildings = geojson_to_buildings({"features": []})
        assert len(buildings) == 0

    def test_convert_multipolygon(self) -> None:
        data = {
            "features": [{
                "type": "Feature",
                "properties": {"id": "MP-001"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[72.878, 19.076], [72.879, 19.076], [72.879, 19.077], [72.878, 19.077], [72.878, 19.076]]],
                        [[[72.880, 19.076], [72.881, 19.076], [72.881, 19.077], [72.880, 19.077], [72.880, 19.076]]],
                    ],
                },
            }],
        }
        buildings = geojson_to_buildings(data)
        assert len(buildings) == 1


class TestOSMParser:
    """Tests for OSM element parsing."""

    def test_parse_elements(self, sample_osm_data: dict) -> None:
        buildings = parse_osm_elements(sample_osm_data)
        assert len(buildings) >= 1
        assert all("coordinates" in b for b in buildings)
        assert all("properties" in b for b in buildings)

    def test_parse_empty(self) -> None:
        buildings = parse_osm_elements({"elements": []})
        assert len(buildings) == 0

    def test_parse_no_elements_key(self) -> None:
        buildings = parse_osm_elements({})
        assert len(buildings) == 0

    def test_parse_extracts_height(self, sample_osm_data: dict) -> None:
        buildings = parse_osm_elements(sample_osm_data)
        heights = [b["properties"].get("height") for b in buildings]
        assert 25.0 in heights


class TestLoadOSMBuildings:
    """Tests for the unified OSM building loader."""

    def test_load_from_geojson_file(self, temp_dir: Path, sample_geojson: dict) -> None:
        path = temp_dir / "test.geojson"
        path.write_text(json.dumps(sample_geojson), encoding="utf-8")

        buildings = load_osm_buildings(path)
        assert len(buildings) == 1

    def test_load_from_osm_json(self, temp_dir: Path, sample_osm_data: dict) -> None:
        path = temp_dir / "test.json"
        path.write_text(json.dumps(sample_osm_data), encoding="utf-8")

        buildings = load_osm_buildings(path)
        assert len(buildings) >= 1

    def test_load_from_city_json(self, temp_dir: Path) -> None:
        city_data = {
            "buildings": [
                {
                    "building_id": "C001",
                    "surfaces": [
                        {"surface_id": "S001", "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0]]}
                    ],
                }
            ]
        }
        path = temp_dir / "city.json"
        path.write_text(json.dumps(city_data), encoding="utf-8")

        buildings = load_osm_buildings(path)
        assert len(buildings) == 1


class TestOSMPipeline:
    """Tests for the complete OSM pipeline."""

    def test_process_osm_data(self, temp_dir: Path, sample_osm_data: dict) -> None:
        source = temp_dir / "osm_input.json"
        output = temp_dir / "osm_output.json"

        source.write_text(json.dumps(sample_osm_data), encoding="utf-8")

        report = process_osm_data(source, output)

        assert report.status == "success"
        assert output.exists()

        with output.open("r") as f:
            data = json.load(f)

        assert "buildings" in data
        assert "metadata" in data
        assert data["metadata"]["pipeline"] == "osm"

    def test_report_has_steps(self, temp_dir: Path, sample_osm_data: dict) -> None:
        source = temp_dir / "osm_input.json"
        output = temp_dir / "osm_output.json"
        source.write_text(json.dumps(sample_osm_data), encoding="utf-8")

        report = process_osm_data(source, output)
        assert len(report.steps) >= 5
        step_names = [s.step for s in report.steps]
        assert "load" in step_names
        assert "parse" in step_names
        assert "clean" in step_names
        assert "validate" in step_names
        assert "save" in step_names

    def test_source_not_found(self, temp_dir: Path) -> None:
        report = process_osm_data("/nonexistent/file.json", temp_dir / "out.json")
        assert report.status == "error"
