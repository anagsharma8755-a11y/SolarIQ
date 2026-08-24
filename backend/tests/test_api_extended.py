"""Extended API tests for the SolarIQ backend.

Covers TASK 6 requirements:
- ML prediction endpoint
- Global error handling
- Oversized / malformed requests
- Validation edge cases
- All system endpoints
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


SAMPLE_BUILDING = {
    "building_id": "EXT-001",
    "name": "Extension Test Building",
    "surfaces": [
        {
            "surface_id": "EXT-001-S001",
            "vertices": [
                [0, 0, 10],
                [20, 0, 10],
                [20, 20, 10],
                [0, 20, 10],
            ],
        },
    ],
}


def _make_building(bid="B1", **overrides):
    return {
        "building_id": bid,
        "surfaces": [
            {
                "surface_id": f"{bid}-S1",
                "vertices": [
                    [0, 0, 5],
                    [10, 0, 5],
                    [10, 10, 5],
                    [0, 10, 5],
                ],
            }
        ],
        **overrides,
    }


# ------------------------------------------------------------------
# /predict-solar -- success
# ------------------------------------------------------------------


def test_roof_prediction():
    resp = client.post(
        "/predict-solar",
        json={
            "surface_id": "PS-001",
            "building_id": "PB-001",
            "area_m2": 400.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["prediction"] is None
    assert data["fallback_score"] >= 0.75
    assert data["fallback_suitability"] == "high"
    assert data["fallback_energy"]["usable_area_m2"] > 0


def test_facade_prediction():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 180.0,
            "tilt_deg": 90.0,
            "surface_type": "facade",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert 0.0 <= data["fallback_score"] <= 1.0


def test_ground_prediction_zero():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 200.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "ground",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fallback_score"] == 0.0
    assert data["fallback_energy"]["usable_area_m2"] == 0.0


def test_with_optional_coordinates():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 50.0,
            "azimuth_deg": 90.0,
            "tilt_deg": 20.0,
            "surface_type": "roof",
            "latitude": 19.076,
            "longitude": 72.878,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["fallback_score"] > 0


# ------------------------------------------------------------------
# /predict-solar -- validation errors
# ------------------------------------------------------------------


def test_predict_negative_area():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": -10.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
        },
    )
    assert resp.status_code == 422


def test_predict_zero_area():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 0.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
        },
    )
    assert resp.status_code == 422


def test_predict_azimuth_out_of_range():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 400.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
        },
    )
    assert resp.status_code == 422


def test_predict_tilt_out_of_range():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 100.0,
            "surface_type": "roof",
        },
    )
    assert resp.status_code == 422


def test_predict_invalid_surface_type():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "unknown",
        },
    )
    assert resp.status_code == 422


def test_predict_latitude_out_of_range():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
            "latitude": 999.0,
        },
    )
    assert resp.status_code == 422


def test_predict_longitude_out_of_range():
    resp = client.post(
        "/predict-solar",
        json={
            "area_m2": 100.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
            "longitude": 200.0,
        },
    )
    assert resp.status_code == 422


def test_predict_missing_required_fields():
    resp = client.post("/predict-solar", json={})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# /analyze-building -- additional validation
# ------------------------------------------------------------------


def test_analyze_empty_body():
    resp = client.post("/analyze-building", json={})
    assert resp.status_code == 422


def test_analyze_building_id_empty_string():
    resp = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "",
                "surfaces": [
                    {
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                        ]
                    }
                ],
            }
        },
    )
    assert resp.status_code == 422


def test_analyze_multiple_surfaces():
    resp = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "MULTI-001",
                "surfaces": [
                    {
                        "vertices": [
                            [0, 0, 10],
                            [10, 0, 10],
                            [10, 10, 10],
                            [0, 10, 10],
                        ]
                    },
                    {
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 0, 10],
                            [0, 0, 10],
                        ]
                    },
                ],
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["surface_count"] == 2


def test_analyze_building_with_name():
    resp = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "NAMED-001",
                "name": "My Building",
                "surfaces": [
                    {
                        "vertices": [
                            [0, 0, 10],
                            [10, 0, 10],
                            [10, 10, 10],
                            [0, 10, 10],
                        ]
                    }
                ],
            }
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Building"


# ------------------------------------------------------------------
# /city-analysis -- additional tests
# ------------------------------------------------------------------


def test_city_single_building():
    resp = client.post(
        "/city-analysis",
        json={"buildings": [SAMPLE_BUILDING]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["building_count"] == 1
    assert len(data["buildings"]) == 1


def test_city_three_buildings():
    buildings = [_make_building(f"B{i}") for i in range(3)]
    resp = client.post(
        "/city-analysis",
        json={"buildings": buildings},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["building_count"] == 3


def test_city_summary_totals_match():
    buildings = [_make_building("BA"), _make_building("BB")]
    resp = client.post(
        "/city-analysis",
        json={"buildings": buildings},
    )
    assert resp.status_code == 200
    data = resp.json()
    building_totals = sum(
        b["total_surface_area_m2"] for b in data["buildings"]
    )
    assert data["summary"]["total_surface_area_m2"] == round(
        building_totals, 4
    )


# ------------------------------------------------------------------
# /optimization-routes -- additional tests
# ------------------------------------------------------------------


def test_optimization_limit_exceeds_candidates():
    resp = client.post(
        "/optimization-routes?limit=500",
        json={"buildings": [SAMPLE_BUILDING]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) <= data["total_candidates"]


def test_optimization_ground_excluded():
    resp = client.post(
        "/optimization-routes",
        json={
            "buildings": [
                {
                    "building_id": "GND-001",
                    "surfaces": [
                        {
                            "surface_id": "GND-001-S001",
                            "vertices": [
                                [0, 0, 10],
                                [20, 0, 10],
                                [20, 20, 10],
                                [0, 20, 10],
                            ],
                        },
                        {
                            "surface_id": "GND-001-S002",
                            "vertices": [
                                [0, 0, 0],
                                [20, 0, 0],
                                [20, 20, 0],
                                [0, 20, 0],
                            ],
                        },
                    ],
                }
            ]
        },
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    types = {r["surface_type"] for r in results}
    assert "ground" not in types


def test_optimization_limit_zero_invalid():
    resp = client.post(
        "/optimization-routes?limit=0",
        json={"buildings": [SAMPLE_BUILDING]},
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------
# System endpoints -- additional tests
# ------------------------------------------------------------------


def test_root_all_fields():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] == "SolarIQ"
    assert data["status"] == "running"
    assert "version" in data


def test_health_simple():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_status_all_services():
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    services = data["services"]
    assert services["geometry_engine"] == "available"
    assert services["solar_engine"] == "available"
    assert services["optimization_engine"] == "available"
    assert services["ml_engine"] in ("fallback", "connected")


# ------------------------------------------------------------------
# Global error handlers -- malformed requests
# ------------------------------------------------------------------


def test_invalid_json_body():
    resp = client.post(
        "/analyze-building",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_empty_json_object_building():
    resp = client.post(
        "/analyze-building",
        json={"building": {}},
    )
    assert resp.status_code == 422


def test_city_empty_buildings_list():
    resp = client.post(
        "/city-analysis",
        json={"buildings": []},
    )
    assert resp.status_code == 422


def test_nonexistent_endpoint():
    resp = client.get("/nonexistent")
    assert resp.status_code in (404, 405)


def test_wrong_http_method():
    resp = client.get("/analyze-building")
    assert resp.status_code in (404, 405)


# ------------------------------------------------------------------
# Response schema validation
# ------------------------------------------------------------------


def test_building_response_fields():
    resp = client.post(
        "/analyze-building",
        json={"building": _make_building("SCHEMA-001")},
    )
    assert resp.status_code == 200
    data = resp.json()

    required_fields = [
        "building_id",
        "surface_count",
        "total_surface_area_m2",
        "usable_surface_area_m2",
        "estimated_capacity_kw",
        "estimated_annual_energy_kwh",
        "surfaces",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    surface = data["surfaces"][0]
    surface_fields = [
        "surface_id",
        "building_id",
        "area_m2",
        "normal",
        "azimuth_deg",
        "tilt_deg",
        "surface_type",
        "vertices",
        "solar_score",
        "solar_suitability",
        "energy_potential",
    ]
    for field in surface_fields:
        assert field in surface, f"Missing surface field: {field}"


def test_optimization_response_fields():
    resp = client.post(
        "/optimization-routes",
        json={"buildings": [_make_building("OPT-001")]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_candidates" in data
    assert "results" in data
    result = data["results"][0]
    assert "rank" in result
    assert "solar_score" in result
    assert "building_id" in result


def test_city_response_fields():
    resp = client.post(
        "/city-analysis",
        json={"buildings": [_make_building("CITY-001")]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "buildings" in data
    summary = data["summary"]
    summary_fields = [
        "building_count",
        "surface_count",
        "total_surface_area_m2",
        "total_usable_surface_area_m2",
        "total_estimated_capacity_kw",
        "total_estimated_annual_energy_kwh",
    ]
    for field in summary_fields:
        assert field in summary, f"Missing summary field: {field}"
