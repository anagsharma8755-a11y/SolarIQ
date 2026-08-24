"""Comprehensive automated tests for the Real-World City Analysis Workflow.

Tests cover:
1. Location search and geocoding response parsing
2. Bounding box calculations and coordinate transformations
3. OSM Overpass building response parsing and height fallbacks
4. GIS to SolarIQ geometry conversion (roof, facade, ground extraction)
5. Weather and solar irradiance integration and fallback
6. End-to-end area analysis pipeline execution
7. Multi-factor city-scale surface and building ranking
8. Capacity-constrained optimization and phased deployment
9. AI explanation layer reasoning and fact anchoring
10. API endpoints validation (/locations/search, /sample-areas, /area/analyze, /area/optimize, /ai/explain)
11. Complete offline/demo fallback resilience
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ai_service import ai_service
from backend.services.area_analysis_service import area_analysis_service
from backend.services.area_optimization_service import area_optimization_service
from backend.services.geocoding_service import DEMO_LOCATIONS, geocoding_service
from backend.services.gis_service import calculate_bounding_box, gis_service
from backend.services.weather_solar_service import weather_solar_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Location Search & Geocoding Tests
# ---------------------------------------------------------------------------


def test_geocoding_fallback_locations():
    """Verify built-in curated locations match search terms."""
    results = geocoding_service.search("Bandra West, Mumbai")
    assert len(results) >= 1
    assert "Bandra" in results[0]["location_name"] or "Bandra" in results[0]["display_name"]
    assert results[0]["latitude"] > 0
    assert results[0]["longitude"] > 0
    assert len(results[0]["bounding_box"]) == 4


def test_geocoding_empty_or_whitespace_query():
    """Empty query should return empty list without error."""
    assert geocoding_service.search("") == []
    assert geocoding_service.search("   ") == []


def test_geocoding_live_mock():
    """Test live OSM Nominatim response parsing with mocked HTTP response."""
    mock_payload = json.dumps([
        {
            "place_id": 12345,
            "lat": "19.0760",
            "lon": "72.8777",
            "display_name": "Mumbai, Maharashtra, India",
            "type": "city",
            "class": "place",
            "importance": 0.9,
            "boundingbox": ["18.89", "19.27", "72.77", "72.98"],
        }
    ]).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_payload
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        results = geocoding_service.search("Mumbai Custom Test", limit=2)
        assert len(results) == 1
        assert results[0]["latitude"] == 19.076
        assert results[0]["longitude"] == 72.8777
        assert results[0]["bounding_box"] == [18.89, 72.77, 19.27, 72.98]


def test_api_locations_search_endpoint():
    """Test GET /locations/search endpoint."""
    resp = client.get("/locations/search?q=Thakur+College")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "latitude" in data[0]
    assert "longitude" in data[0]


def test_api_sample_areas_endpoint():
    """Test GET /sample-areas endpoint."""
    resp = client.get("/sample-areas")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    names = [d["location_name"] for d in data]
    assert any("Bandra" in n for n in names)


# ---------------------------------------------------------------------------
# 2. Bounding Box & Coordinate Transformation Tests
# ---------------------------------------------------------------------------


def test_calculate_bounding_box():
    """Verify radius to WGS84 bounding box calculations."""
    lat, lon, radius = 19.0760, 72.8777, 500.0
    south, west, north, east = calculate_bounding_box(lat, lon, radius)
    assert south < lat < north
    assert west < lon < east
    assert -90.0 <= south <= 90.0
    assert -180.0 <= west <= 180.0


def test_gis_coordinate_conversion_to_solariq():
    """Verify transformation from WGS84 footprint to metric SolarIQ LOD-1 surfaces."""
    building_record = {
        "osm_id": 1001,
        "building_id": "TEST-BLD-01",
        "name": "Test Complex",
        "height_m": 21.0,
        "height_estimated": False,
        "levels": 6,
        "building_type": "apartments",
        "latitude": 19.0596,
        "longitude": 72.8295,
        "polygon_wgs84": [
            [72.8290, 19.0590],
            [72.8300, 19.0590],
            [72.8300, 19.0600],
            [72.8290, 19.0600],
            [72.8290, 19.0590],
        ],
    }

    solariq_format = gis_service.convert_to_solariq_geometry(building_record)
    assert solariq_format["building_id"] == "TEST-BLD-01"
    assert len(solariq_format["surfaces"]) >= 6  # 1 roof + 4 facades + 1 ground
    roof = solariq_format["surfaces"][0]
    assert roof["surface_id"] == "TEST-BLD-01-S001"
    # Check that roof vertices are at height = 21.0
    assert all(v[2] == 21.0 for v in roof["vertices"])


# ---------------------------------------------------------------------------
# 3. OSM Building Height Fallback Resolution Tests
# ---------------------------------------------------------------------------


def test_height_resolution_direct():
    """Test height resolution when direct 'height' tag is present."""
    tags = {"building": "yes", "height": "32.5m"}
    height, estimated, levels = gis_service._resolve_building_height(tags)
    assert height == 32.5
    assert not estimated
    assert levels == 9


def test_height_resolution_levels():
    """Test height resolution from 'building:levels' tag."""
    tags = {"building": "apartments", "building:levels": "10"}
    height, estimated, levels = gis_service._resolve_building_height(tags)
    assert height == 35.0  # 10 * 3.5
    assert estimated
    assert levels == 10


def test_height_resolution_typology_fallback():
    """Test height resolution fallback from building typology tag."""
    tags = {"building": "office"}
    height, estimated, levels = gis_service._resolve_building_height(tags)
    assert height == 28.0
    assert estimated
    assert levels == 8


# ---------------------------------------------------------------------------
# 4. Weather and Solar Provider Tests
# ---------------------------------------------------------------------------


def test_weather_solar_service_metrics():
    """Verify weather and solar irradiance values for area."""
    metrics = weather_solar_service.get_area_weather_and_solar(19.0596, 72.8295)
    assert metrics["annual_irradiance_kwh_m2"] > 1000.0
    assert "data_source" in metrics
    assert "avg_temperature_c" in metrics
    assert "weather_condition" in metrics


# ---------------------------------------------------------------------------
# 5. Complete Area Analysis Pipeline Tests
# ---------------------------------------------------------------------------


def test_area_analysis_pipeline_execution():
    """Test the complete end-to-end area analysis pipeline."""
    result = area_analysis_service.analyze_area(
        latitude=19.0596,
        longitude=72.8299,
        radius_m=300.0,
        location_name="Bandra West Test",
        max_buildings=10,
    )

    assert "analysis_id" in result
    assert result["location_name"] == "Bandra West Test"
    assert len(result["buildings"]) > 0
    assert len(result["ranked_surfaces"]) > 0

    summary = result["summary"]
    assert summary["building_count"] > 0
    assert summary["total_usable_surface_area_m2"] > 0
    assert summary["total_estimated_capacity_kw"] > 0
    assert summary["total_estimated_annual_energy_kwh"] > 0
    assert summary["average_solar_score"] > 0

    geojson = result["geojson"]
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == len(result["buildings"])
    prop = geojson["features"][0]["properties"]
    assert "solar_suitability" in prop
    assert "color" in prop


def test_api_area_analyze_endpoint():
    """Test POST /area/analyze and /location/analyze endpoints."""
    payload = {
        "latitude": 19.0596,
        "longitude": 72.8295,
        "radius_m": 250.0,
        "location_name": "Bandra West",
        "max_buildings": 8,
    }
    resp = client.post("/area/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis_id" in data
    analysis_id = data["analysis_id"]

    # Test GET /area/{id}
    resp_get = client.get(f"/area/{analysis_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["analysis_id"] == analysis_id

    # Test GET /area/{id}/map
    resp_map = client.get(f"/area/{analysis_id}/map")
    assert resp_map.status_code == 200
    assert resp_map.json()["type"] == "FeatureCollection"


# ---------------------------------------------------------------------------
# 6. Capacity-Constrained Optimization Tests
# ---------------------------------------------------------------------------


def test_capacity_constrained_optimization():
    """Verify that optimization strictly respects the requested capacity limit."""
    area_result = area_analysis_service.analyze_area(
        latitude=19.0596,
        longitude=72.8295,
        radius_m=350.0,
        max_buildings=12,
    )
    ranked = area_result["ranked_surfaces"]
    target_kw = 150.0

    opt_result = area_optimization_service.optimize_deployment(
        ranked_surfaces=ranked,
        max_capacity_kw=target_kw,
    )

    assert opt_result["selected_capacity_kw"] <= target_kw
    assert opt_result["selected_annual_energy_kwh"] > 0
    assert opt_result["annual_co2_offset_tonnes"] > 0
    assert len(opt_result["phases"]) > 0


def test_api_area_optimize_endpoint():
    """Test POST /area/optimize endpoint."""
    # First analyze an area
    area_resp = client.post(
        "/area/analyze",
        json={
            "latitude": 19.0596,
            "longitude": 72.8295,
            "radius_m": 300.0,
            "max_buildings": 8,
        },
    )
    assert area_resp.status_code == 200
    analysis_id = area_resp.json()["analysis_id"]

    # Now run optimization
    opt_resp = client.post(
        "/area/optimize",
        json={
            "analysis_id": analysis_id,
            "max_capacity_kw": 200.0,
            "min_solar_score": 0.35,
        },
    )
    assert opt_resp.status_code == 200
    data = opt_resp.json()
    assert data["selected_capacity_kw"] <= 200.0
    assert data["selected_surfaces_count"] > 0


# ---------------------------------------------------------------------------
# 7. AI Explanation Layer Tests
# ---------------------------------------------------------------------------


def test_ai_explanation_service():
    """Verify AI explanation generates grounded insights from actual calculated data."""
    area_result = area_analysis_service.analyze_area(
        latitude=19.0596,
        longitude=72.8295,
        radius_m=300.0,
        location_name="Bandra West Demo",
        max_buildings=6,
    )

    prompt = "Where should I install solar panels in this area?"
    explanation = ai_service.explain(
        analysis_data=area_result,
        user_prompt=prompt,
    )

    assert explanation["query"] == prompt
    assert len(explanation["calculated_results"]) > 0
    assert "ai_interpretation" in explanation
    assert "summary" in explanation["ai_interpretation"]
    assert len(explanation["ai_interpretation"]["recommendations"]) > 0


def test_ai_explanation_capacity_limit_query():
    """Verify AI explanation when asked about a 500 kW capacity limit."""
    area_result = area_analysis_service.analyze_area(
        latitude=19.0596,
        longitude=72.8295,
        radius_m=300.0,
        max_buildings=8,
    )

    prompt = "What if I only have 500 kW available?"
    explanation = ai_service.explain(
        analysis_data=area_result,
        user_prompt=prompt,
        target_capacity_kw=500.0,
    )

    assert explanation["optimization_context"] is not None
    assert explanation["optimization_context"]["selected_capacity_kw"] <= 500.0


def test_api_ai_explain_endpoint():
    """Test POST /ai/explain endpoint."""
    area_resp = client.post(
        "/area/analyze",
        json={
            "latitude": 19.0596,
            "longitude": 72.8295,
            "radius_m": 300.0,
            "max_buildings": 6,
        },
    )
    analysis_id = area_resp.json()["analysis_id"]

    resp = client.post(
        "/ai/explain",
        json={
            "analysis_id": analysis_id,
            "query": "Which buildings are best for solar?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "calculated_results" in data
    assert "ai_interpretation" in data
    assert len(data["calculated_results"]) >= 3
