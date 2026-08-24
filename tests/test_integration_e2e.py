"""End-to-end integration test for SolarIQ.

Exercises the complete flow:
    Raw data → Data pipeline → Standardized datasets →
    Building geometry → Surface extraction → Classification →
    Solar prediction → Energy estimation → Optimization →
    City aggregation → FastAPI response

Uses sample data only. Does not require network or ML model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CITY = PROJECT_ROOT / "sample_data" / "city" / "mumbai_sample.geojson"
SAMPLE_WEATHER = PROJECT_ROOT / "sample_data" / "weather" / "mumbai_weather.csv"
SAMPLE_SOLAR = PROJECT_ROOT / "sample_data" / "solar" / "mumbai_solar.csv"
SAMPLE_BUILDINGS_JSON = PROJECT_ROOT / "sample_data" / "buildings.json"


@pytest.fixture
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper: build a realistic multi-building dataset
# ---------------------------------------------------------------------------

def _make_building(bid: str, w: float = 20.0, h: float = 15.0) -> dict:
    """Create a building with roof, 2 facades, and ground."""
    return {
        "building_id": bid,
        "name": f"Building {bid}",
        "surfaces": [
            {
                "surface_id": f"{bid}-S001",
                "vertices": [
                    [0, 0, h], [w, 0, h], [w, w, h], [0, w, h],
                ],
            },
            {
                "surface_id": f"{bid}-S002",
                "vertices": [
                    [0, 0, 0], [w, 0, 0], [w, 0, h], [0, 0, h],
                ],
            },
            {
                "surface_id": f"{bid}-S003",
                "vertices": [
                    [0, 0, 0], [0, w, 0], [0, w, h], [0, 0, h],
                ],
            },
            {
                "surface_id": f"{bid}-S004",
                "vertices": [
                    [0, w, 0], [w, w, 0], [w, 0, 0], [0, 0, 0],
                ],
            },
        ],
    }


# ===================================================================
# Test 1: Data Pipeline → Backend Integration
# ===================================================================


class TestDataPipelineToBackend:
    """Verify data pipeline output can be consumed by the backend."""

    def test_city_pipeline_produces_backend_compatible_data(self):
        """Process sample city data and verify backend can analyze it."""
        from data_pipeline.pipeline.city_pipeline import (
            process_city_data,
            load_for_backend,
        )

        # Step 1: Run the city pipeline.
        report = process_city_data(SAMPLE_CITY)
        assert report.status == "success"

        # Step 2: Load in backend-compatible format.
        buildings = load_for_backend()
        assert len(buildings) > 0

        # Step 3: Verify each building has required fields.
        for b in buildings:
            assert "building_id" in b
            assert "surfaces" in b
            assert len(b["surfaces"]) > 0
            for s in b["surfaces"]:
                assert "vertices" in s
                assert len(s["vertices"]) >= 3


# ===================================================================
# Test 2: Geometry → Solar → Energy Full Pipeline
# ===================================================================


class TestGeometrySolarEnergyPipeline:
    """Verify the full geometry → solar → energy pipeline."""

    def test_single_building_full_pipeline(self):
        """Analyze one building through all stages."""
        from backend.geometry.surfaces import extract_surfaces
        from backend.services.solar_service import (
            analyze_surface,
            calculate_solar_score,
            estimate_energy_potential,
            suitability_label,
        )

        building = _make_building("INT-001")

        # Step 1: Extract surfaces.
        surfaces = extract_surfaces(building)
        assert len(surfaces) == 4

        # Step 2: Classify surfaces.
        types = {s["surface_type"] for s in surfaces}
        # All surfaces should be classified as roof, facade, or ground.
        assert types.issubset({"roof", "facade", "ground"})
        assert len(types) >= 1  # At least one type present

        # Step 3: Solar scoring.
        for s in surfaces:
            analyzed = analyze_surface(s)
            assert "solar_score" in analyzed
            assert "solar_suitability" in analyzed
            assert "energy_potential" in analyzed
            assert 0.0 <= analyzed["solar_score"] <= 1.0

        # Step 4: Non-ground surfaces have positive energy.
        non_ground = [s for s in surfaces if s["surface_type"] != "ground"]
        for ng in non_ground:
            analyzed = analyze_surface(ng)
            assert analyzed["energy_potential"]["usable_area_m2"] > 0

        # Step 5: Every surface has a valid solar score.
        for s in surfaces:
            analyzed = analyze_surface(s)
            assert 0.0 <= analyzed["solar_score"] <= 1.0
            assert analyzed["solar_suitability"] in ("high", "medium", "low")

    def test_ml_fallback_returns_none(self):
        """Verify ML prediction returns None when no model is connected."""
        from backend.services.ml_service import ml_service

        assert ml_service.available is False
        result = ml_service.predict_if_available({"area_m2": 100})
        assert result is None


# ===================================================================
# Test 3: Optimization Pipeline
# ===================================================================


class TestOptimizationPipeline:
    """Verify optimization ranks surfaces correctly."""

    def test_optimization_full_pipeline(self):
        """Run optimization on multiple buildings."""
        from backend.services.optimization_service import optimize_surfaces

        buildings = [_make_building(f"B{i}") for i in range(5)]

        result = optimize_surfaces(
            buildings=buildings,
            limit=10,
            include_city_summary=True,
        )

        # Verify structure.
        assert "total_candidates" in result
        assert "filtered_candidates" in result
        assert "scoring_weights" in result
        assert "results" in result
        assert "city_summary" in result

        # Verify counts.
        assert result["total_candidates"] > 0
        # Ground surfaces excluded from candidates.
        assert result["filtered_candidates"] <= result["total_candidates"]

        # Verify ranking.
        if result["results"]:
            scores = [r["composite_score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)

        # Verify city summary.
        summary = result["city_summary"]
        assert summary["total_potential_capacity_kw"] > 0
        assert summary["total_annual_energy_kwh"] > 0
        assert len(summary["top_buildings"]) > 0


# ===================================================================
# Test 4: FastAPI Endpoints (Full Stack)
# ===================================================================


class TestAPIEndpoints:
    """Verify all API endpoints work end-to-end."""

    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_status(self, client: TestClient):
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["services"]["geometry_engine"] == "available"
        assert data["services"]["solar_engine"] == "available"
        assert data["services"]["ml_engine"] == "fallback"

    def test_analyze_building(self, client: TestClient):
        building = _make_building("API-001")
        resp = client.post("/analyze-building", json={"building": building})
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == "API-001"
        assert data["surface_count"] == 4
        assert data["total_surface_area_m2"] > 0
        assert data["estimated_capacity_kw"] > 0

    def test_city_analysis(self, client: TestClient):
        buildings = [_make_building(f"C{i}") for i in range(3)]
        resp = client.post("/city-analysis", json={"buildings": buildings})
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["building_count"] == 3
        assert data["summary"]["total_estimated_capacity_kw"] > 0

    def test_optimization(self, client: TestClient):
        buildings = [_make_building(f"O{i}") for i in range(3)]
        resp = client.post(
            "/optimization-routes",
            json={"buildings": buildings},
            params={"limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_candidates"] > 0
        assert len(data["results"]) <= 5

    def test_prediction(self, client: TestClient):
        resp = client.post(
            "/predict-solar",
            json={
                "area_m2": 400.0,
                "azimuth_deg": 180.0,
                "tilt_deg": 20.0,
                "surface_type": "roof",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["fallback_score"] > 0
        assert data["fallback_energy"]["usable_area_m2"] > 0


# ===================================================================
# Test 5: Sample Data Loading
# ===================================================================


class TestSampleDataLoading:
    """Verify sample data files are loadable and valid."""

    def test_load_sample_city_geojson(self):
        with SAMPLE_CITY.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert "features" in data
        assert len(data["features"]) > 0

    def test_load_sample_weather_csv(self):
        import pandas as pd
        df = pd.read_csv(SAMPLE_WEATHER)
        assert len(df) > 0
        assert "temperature" in df.columns or "temp" in df.columns

    def test_load_sample_solar_csv(self):
        import pandas as pd
        df = pd.read_csv(SAMPLE_SOLAR)
        assert len(df) > 0

    def test_load_sample_buildings_json(self):
        with SAMPLE_BUILDINGS_JSON.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert "buildings" in data
        assert len(data["buildings"]) > 0


# ===================================================================
# Test 6: Weather/Solar Pipeline (Offline)
# ===================================================================


class TestDataPipelines:
    """Verify data pipelines process sample data correctly."""

    def test_weather_pipeline(self):
        from data_pipeline.pipeline.weather_pipeline import process_weather_data

        report = process_weather_data(SAMPLE_WEATHER)
        assert report.status in ("success", "partial")

    def test_solar_pipeline(self):
        from data_pipeline.pipeline.solar_pipeline import process_solar_data

        report = process_solar_data(SAMPLE_SOLAR)
        assert report.status in ("success", "partial")

    def test_city_pipeline(self):
        from data_pipeline.pipeline.city_pipeline import process_city_data

        report = process_city_data(SAMPLE_CITY)
        assert report.status == "success"
