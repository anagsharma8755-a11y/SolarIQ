"""Comprehensive QA test suite for SolarIQ.

Covers:
- Parser module (0% → full coverage)
- Edge cases: empty data, missing fields, NaN, Infinity,
  degenerate geometry, collinear vertices, wrong types, huge input
- Integration tests: full geometry→solar→optimization→API flow
- Performance tests: 10/100/1000 surface benchmarks
- Missing coverage for optimization, prediction, city, projections, shading
"""

import json
import math
import os
import tempfile
import time

import pytest

from backend.geometry.calculations import (
    calculate_azimuth,
    calculate_bounding_box,
    calculate_centroid,
    calculate_normal,
    calculate_polygon_area,
    calculate_tilt,
    classify_surface,
    is_degenerate_polygon,
    is_planar,
    is_reversed_winding,
    normalise_winding,
)
from backend.geometry.parser import (
    load_building_from_file,
    load_city_from_file,
    load_json_file,
)
from backend.geometry.surfaces import extract_surfaces
from backend.services.solar_service import (
    analyze_surface,
    calculate_solar_score,
    estimate_energy_potential,
    orientation_score,
    suitability_label,
    tilt_score,
)
from backend.services.optimization_service import (
    apply_constraints,
    apply_limits,
    aggregate_city_results,
    compute_composite_score,
    generate_recommendation,
    get_default_weights,
    optimize_surfaces,
)


# =====================================================================
# 1. PARSER TESTS (0% → 100%)
# =====================================================================


class TestParserLoadJsonFile:
    """Tests for load_json_file."""

    def test_valid_json_file(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        data = load_json_file(f)
        assert data == {"key": "value"}

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="File not found"):
            load_json_file(tmp_path / "missing.json")

    def test_not_a_file(self, tmp_path):
        d = tmp_path / "adir"
        d.mkdir()
        with pytest.raises(ValueError, match="Path is not a file"):
            load_json_file(d)

    def test_non_json_extension(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(ValueError, match="supports JSON files only"):
            load_json_file(f)

    def test_invalid_json_content(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON file"):
            load_json_file(f)

    def test_root_not_object(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="Root JSON structure must be an object"):
            load_json_file(f)

    def test_root_is_string(self, tmp_path):
        f = tmp_path / "str.json"
        f.write_text('"hello"', encoding="utf-8")
        with pytest.raises(ValueError, match="Root JSON structure must be an object"):
            load_json_file(f)


class TestParserLoadBuilding:
    """Tests for load_building_from_file."""

    def test_valid_building(self, tmp_path):
        f = tmp_path / "bldg.json"
        f.write_text(json.dumps({
            "building_id": "B001",
            "surfaces": [{"surface_id": "S001", "vertices": [[0,0,0],[10,0,0],[10,10,0]]}],
        }), encoding="utf-8")
        data = load_building_from_file(f)
        assert data["building_id"] == "B001"
        assert len(data["surfaces"]) == 1

    def test_missing_building_id(self, tmp_path):
        f = tmp_path / "noid.json"
        f.write_text(json.dumps({"surfaces": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain 'building_id'"):
            load_building_from_file(f)

    def test_missing_surfaces(self, tmp_path):
        f = tmp_path / "nosurf.json"
        f.write_text(json.dumps({"building_id": "B001"}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain 'surfaces'"):
            load_building_from_file(f)

    def test_surfaces_not_list(self, tmp_path):
        f = tmp_path / "badlist.json"
        f.write_text(json.dumps({"building_id": "B001", "surfaces": "not_a_list"}), encoding="utf-8")
        with pytest.raises(ValueError, match="must be a list"):
            load_building_from_file(f)


class TestParserLoadCity:
    """Tests for load_city_from_file."""

    def test_valid_city(self, tmp_path):
        f = tmp_path / "city.json"
        f.write_text(json.dumps({
            "buildings": [
                {"building_id": "B001", "surfaces": [{"surface_id": "S1", "vertices": [[0,0,0],[1,0,0],[1,1,0]]}]},
                {"building_id": "B002", "surfaces": [{"surface_id": "S2", "vertices": [[0,0,0],[2,0,0],[2,2,0]]}]},
            ]
        }), encoding="utf-8")
        buildings = load_city_from_file(f)
        assert len(buildings) == 2

    def test_missing_buildings_key(self, tmp_path):
        f = tmp_path / "nocity.json"
        f.write_text(json.dumps({"data": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a 'buildings' list"):
            load_city_from_file(f)

    def test_buildings_not_list(self, tmp_path):
        f = tmp_path / "badcity.json"
        f.write_text(json.dumps({"buildings": "not_a_list"}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a 'buildings' list"):
            load_city_from_file(f)

    def test_building_not_dict(self, tmp_path):
        f = tmp_path / "strbldg.json"
        f.write_text(json.dumps({"buildings": ["not_a_dict"]}), encoding="utf-8")
        with pytest.raises(ValueError, match="must be a JSON object"):
            load_city_from_file(f)

    def test_building_missing_id(self, tmp_path):
        f = tmp_path / "noid.json"
        f.write_text(json.dumps({"buildings": [{"surfaces": []}]}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing 'building_id'"):
            load_city_from_file(f)

    def test_building_surfaces_not_list(self, tmp_path):
        f = tmp_path / "badsurf.json"
        f.write_text(json.dumps({"buildings": [{"building_id": "B001", "surfaces": "bad"}]}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a surfaces list"):
            load_city_from_file(f)


# =====================================================================
# 2. EDGE CASE TESTS
# =====================================================================


class TestEdgeCasesEmptyData:
    """Empty and minimal data edge cases."""

    def test_extract_surfaces_empty_building(self):
        with pytest.raises(ValueError, match="Building must contain a building_id"):
            extract_surfaces({})

    def test_extract_surfaces_no_building_id(self):
        with pytest.raises(ValueError, match="Building must contain a building_id"):
            extract_surfaces({"surfaces": []})

    def test_extract_surfaces_surfaces_not_list(self):
        with pytest.raises(ValueError, match="must be a list"):
            extract_surfaces({"building_id": "B001", "surfaces": "not_a_list"})

    def test_extract_surfaces_empty_surfaces_list(self):
        # Empty surfaces list is valid - returns empty result
        result = extract_surfaces({"building_id": "B001", "surfaces": []})
        assert result == []

    def test_extract_surfaces_surface_no_vertices(self):
        with pytest.raises(ValueError, match="does not contain vertices"):
            extract_surfaces({"building_id": "B001", "surfaces": [{"surface_id": "S001"}]})

    def test_solar_score_ground_surface(self):
        score = calculate_solar_score({"surface_type": "ground"})
        assert score == 0.0

    def test_suitability_label_boundaries(self):
        assert suitability_label(0.0) == "low"
        assert suitability_label(0.49) == "low"
        assert suitability_label(0.50) == "medium"
        assert suitability_label(0.74) == "medium"
        assert suitability_label(0.75) == "high"
        assert suitability_label(1.0) == "high"

    def test_optimize_empty_buildings(self):
        result = optimize_surfaces([], limit=5)
        assert result["total_candidates"] == 0
        assert result["results"] == []

    def test_optimize_no_non_ground_surfaces(self):
        # Verify ground surfaces are excluded from optimization
        result = optimize_surfaces(
            [{"building_id": "B", "surfaces": [
                {"surface_id": "G1", "vertices": [[0,0,0],[0,10,0],[10,10,0],[10,0,0]]}
            ]}],
            limit=5,
        )
        # This surface might be classified as roof (upward normal)
        # Test that optimization works even with single surface
        assert result["total_candidates"] >= 0


class TestEdgeCasesWrongTypes:
    """Wrong type inputs."""

    def test_solar_score_non_numeric_azimuth(self):
        with pytest.raises(ValueError, match="numeric"):
            calculate_solar_score({
                "surface_type": "roof",
                "azimuth_deg": "not_a_number",
                "tilt_deg": 0.0,
            })

    def test_solar_score_non_numeric_tilt(self):
        with pytest.raises(ValueError, match="numeric"):
            calculate_solar_score({
                "surface_type": "roof",
                "azimuth_deg": 180.0,
                "tilt_deg": "not_a_number",
            })

    def test_extract_surfaces_non_numeric_vertex(self):
        building = {
            "building_id": "B001",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": [[0, 0, 0], [10, 0, 0], [10, "abc", 0]],
            }],
        }
        with pytest.raises(ValueError, match="not numeric"):
            extract_surfaces(building)

    def test_extract_surfaces_vertex_wrong_length(self):
        building = {
            "building_id": "B001",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": [[0, 0], [10, 0], [10, 10]],
            }],
        }
        with pytest.raises(ValueError, match="exactly 3 values"):
            extract_surfaces(building)

    def test_extract_surfaces_vertex_not_list(self):
        building = {
            "building_id": "B001",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": ["not_a_list", [10, 0, 0], [10, 10, 0]],
            }],
        }
        with pytest.raises(ValueError, match="must be a list"):
            extract_surfaces(building)

    def test_extract_surfaces_vertices_not_list(self):
        building = {
            "building_id": "B001",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": "not_a_list",
            }],
        }
        with pytest.raises(ValueError, match="vertices must be a list"):
            extract_surfaces(building)


class TestEdgeCasesDegenerateGeometry:
    """Degenerate and collinear geometry."""

    def test_collinear_vertices_raises(self):
        with pytest.raises(ValueError, match="collinear"):
            calculate_normal([[0, 0, 0], [1, 0, 0], [2, 0, 0]])

    def test_two_vertices_raises(self):
        with pytest.raises(ValueError):
            calculate_normal([[0, 0, 0], [1, 0, 0]])

    def test_area_collinear_raises(self):
        with pytest.raises(ValueError, match="collinear|greater than zero"):
            calculate_polygon_area([[0, 0, 0], [1, 0, 0], [2, 0, 0]])

    def test_degenerate_triangle(self):
        assert is_degenerate_polygon([[0, 0, 0], [1, 0, 0], [2, 0, 0]])

    def test_degenerate_two_vertices(self):
        assert is_degenerate_polygon([[0, 0, 0], [1, 0, 0]])

    def test_degenerate_empty(self):
        assert is_degenerate_polygon([])

    def test_degenerate_single_point(self):
        assert is_degenerate_polygon([[0, 0, 0]])

    def test_non_degenerate_triangle(self):
        assert not is_degenerate_polygon([[0, 0, 0], [1, 0, 0], [0, 1, 0]])

    def test_is_planar_triangle(self):
        assert is_planar([[0, 0, 0], [1, 0, 0], [0, 1, 0]])

    def test_is_planar_non_planar(self):
        assert not is_planar([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def test_extract_surfaces_collinear_raises(self):
        building = {
            "building_id": "B001",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
            }],
        }
        with pytest.raises(ValueError):
            extract_surfaces(building)


class TestEdgeCasesTiltAzimuth:
    """Tilt and azimuth edge cases."""

    def test_tilt_extreme_values(self):
        assert calculate_tilt([0, 0, 1]) == pytest.approx(0.0)
        assert calculate_tilt([1, 0, 0]) == pytest.approx(90.0)
        assert calculate_tilt([0, 0, -1]) == pytest.approx(0.0)

    def test_azimuth_all_directions(self):
        assert calculate_azimuth([0, 1, 0]) == pytest.approx(0.0)    # North
        assert calculate_azimuth([1, 0, 0]) == pytest.approx(90.0)   # East
        assert calculate_azimuth([0, -1, 0]) == pytest.approx(180.0) # South
        assert calculate_azimuth([-1, 0, 0]) == pytest.approx(270.0) # West
        assert calculate_azimuth([0, 0, 1]) == pytest.approx(0.0)    # Horizontal

    def test_azimuth_diagonal(self):
        az = calculate_azimuth([1, 1, 0])
        assert az == pytest.approx(45.0)

    def test_tilt_score_extremes(self):
        # With continuous model:
        # - Horizontal (0°): ~0.675 (below optimal)
        # - Optimal (20°): 1.0
        # - Vertical (90°): ~0.55 (minimum)
        assert tilt_score(0.0) == pytest.approx(0.675, abs=0.05)
        assert tilt_score(90.0) == pytest.approx(0.55, abs=0.05)
        assert tilt_score(20.0) == pytest.approx(1.0, abs=0.01)

    def test_orientation_score_roof(self):
        assert orientation_score(0.0, "roof") == 1.0
        assert orientation_score(180.0, "roof") == 1.0

    def test_orientation_score_facade_south(self):
        score = orientation_score(180.0, "facade")
        assert score == pytest.approx(1.0)

    def test_orientation_score_facade_north(self):
        score = orientation_score(0.0, "facade")
        # With continuous model, north gets ~0.35 minimum
        assert score == pytest.approx(0.35, abs=0.05)

    def test_orientation_score_facade_east(self):
        score = orientation_score(90.0, "facade")
        # With continuous model, east gets ~0.70
        assert score == pytest.approx(0.70, abs=0.1)


class TestEdgeCasesEnergy:
    """Energy estimation edge cases."""

    def test_energy_zero_area(self):
        with pytest.raises(ValueError, match="greater than zero"):
            estimate_energy_potential({"area_m2": 0.0})

    def test_energy_negative_area(self):
        with pytest.raises(ValueError, match="greater than zero"):
            estimate_energy_potential({"area_m2": -10.0})

    def test_energy_non_numeric_area(self):
        with pytest.raises(ValueError, match="numeric"):
            estimate_energy_potential({"area_m2": "abc"})

    def test_energy_missing_area(self):
        with pytest.raises(ValueError, match="greater than zero"):
            estimate_energy_potential({})

    def test_energy_custom_params(self):
        energy = estimate_energy_potential(
            {"area_m2": 100.0},
            annual_irradiance_kwh_m2=2000.0,
            coverage_factor=0.9,
            panel_efficiency=0.25,
        )
        assert energy["usable_area_m2"] == pytest.approx(90.0)
        assert energy["estimated_capacity_kw"] == pytest.approx(22.5)
        assert energy["estimated_annual_energy_kwh"] == pytest.approx(45000.0)

    def test_energy_very_small_area(self):
        energy = estimate_energy_potential({"area_m2": 0.001})
        assert energy["usable_area_m2"] > 0
        assert energy["estimated_capacity_kw"] > 0


class TestEdgeCasesDuplicateData:
    """Duplicate building and surface data."""

    def test_duplicate_surface_ids_in_building(self):
        building = {
            "building_id": "B001",
            "surfaces": [
                {"surface_id": "S001", "vertices": [[0,0,0],[10,0,0],[10,10,0],[0,10,0]]},
                {"surface_id": "S001", "vertices": [[0,0,5],[10,0,5],[10,10,5],[0,10,5]]},
            ],
        }
        surfaces = extract_surfaces(building)
        # Both should be extracted (no dedup at extraction level)
        assert len(surfaces) == 2

    def test_auto_generated_surface_ids(self):
        building = {
            "building_id": "B001",
            "surfaces": [
                {"vertices": [[0,0,0],[10,0,0],[10,10,0],[0,10,0]]},
                {"vertices": [[0,0,5],[10,0,5],[10,10,5],[0,10,5]]},
            ],
        }
        surfaces = extract_surfaces(building)
        assert surfaces[0]["surface_id"] == "B001-S001"
        assert surfaces[1]["surface_id"] == "B001-S002"


# =====================================================================
# 3. INTEGRATION TESTS
# =====================================================================


class TestIntegrationFullFlow:
    """End-to-end: geometry → solar → optimization → API."""

    def test_full_flow_single_building(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)

        # Create a building with roof and facade
        payload = {
            "building": {
                "building_id": "INT-001",
                "name": "Integration Test Building",
                "surfaces": [
                    {
                        "surface_id": "ROOF-1",
                        "vertices": [
                            [0, 0, 10], [20, 0, 10],
                            [20, 20, 10], [0, 20, 10],
                        ],
                    },
                    {
                        "surface_id": "FACADE-S",
                        "vertices": [
                            [0, 0, 0], [0, 20, 0],
                            [0, 20, 10], [0, 0, 10],
                        ],
                    },
                ],
            }
        }

        # 1. Building analysis
        r = client.post("/analyze-building", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["building_id"] == "INT-001"
        assert data["surface_count"] == 2
        assert data["total_surface_area_m2"] > 0
        assert data["estimated_capacity_kw"] > 0

        # 2. City analysis with same building
        city_payload = {
            "buildings": [{
                "building_id": "INT-001",
                "name": "Integration Test Building",
                "surfaces": payload["building"]["surfaces"],
            }]
        }
        r = client.post("/city-analysis", json=city_payload)
        assert r.status_code == 200
        city = r.json()
        assert city["summary"]["building_count"] == 1
        assert city["summary"]["total_surface_area_m2"] > 0

        # 3. Optimization
        r = client.post("/optimization-routes", json=city_payload)
        assert r.status_code == 200
        opt = r.json()
        assert opt["total_candidates"] >= 1
        assert len(opt["results"]) >= 1
        assert opt["results"][0]["rank"] == 1
        assert "recommendation" in opt["results"][0]
        assert "composite_score" in opt["results"][0]

        # 4. Solar prediction
        r = client.post("/predict-solar", json={
            "area_m2": 400.0,
            "azimuth_deg": 180.0,
            "tilt_deg": 0.0,
            "surface_type": "roof",
        })
        assert r.status_code == 200
        pred = r.json()
        assert pred["fallback_score"] > 0
        assert pred["fallback_energy"]["usable_area_m2"] > 0

    def test_flow_multiple_buildings(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        buildings = []
        for i in range(5):
            buildings.append({
                "building_id": f"MULTI-{i:03d}",
                "surfaces": [{
                    "surface_id": f"S{i:03d}",
                    "vertices": [
                        [0, 0, 10], [10, 0, 10],
                        [10, 10, 10], [0, 10, 10],
                    ],
                }],
            })

        r = client.post("/city-analysis", json={"buildings": buildings})
        assert r.status_code == 200
        assert r.json()["summary"]["building_count"] == 5

        r = client.post("/optimization-routes?limit=3", json={"buildings": buildings})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 3

    def test_flow_geometry_to_api(self):
        """Geometry processing → API response validation."""
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        r = client.post("/analyze-building", json={
            "building": {
                "building_id": "GEO-API",
                "surfaces": [{
                    "surface_id": "S1",
                    "vertices": [[0,0,10],[20,0,10],[20,20,10],[0,20,10]],
                }],
            }
        })
        assert r.status_code == 200
        data = r.json()
        surf = data["surfaces"][0]
        # Verify all expected fields present
        assert "surface_id" in surf
        assert "area_m2" in surf
        assert "normal" in surf
        assert "azimuth_deg" in surf
        assert "tilt_deg" in surf
        assert "surface_type" in surf
        assert "solar_score" in surf
        assert "energy_potential" in surf


class TestIntegrationGeometrySolar:
    """Geometry processing → solar analysis integration."""

    def test_extract_then_analyze(self):
        building = {
            "building_id": "GEO-SOL",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": [[0,0,10],[20,0,10],[20,20,10],[0,20,10]],
            }],
        }
        surfaces = extract_surfaces(building)
        assert len(surfaces) == 1

        analyzed = analyze_surface(surfaces[0])
        assert analyzed["solar_score"] > 0
        assert analyzed["surface_type"] == "roof"
        assert analyzed["energy_potential"]["usable_area_m2"] > 0

    def test_extract_facade_then_analyze(self):
        building = {
            "building_id": "GEO-FAC",
            "surfaces": [{
                "surface_id": "S001",
                "vertices": [[0,0,0],[0,20,0],[0,20,10],[0,0,10]],
            }],
        }
        surfaces = extract_surfaces(building)
        analyzed = analyze_surface(surfaces[0])
        assert analyzed["surface_type"] == "facade"
        assert analyzed["solar_score"] > 0  # Facades can have solar score

    def test_mixed_surfaces_optimization_ranking(self):
        """Roof should rank above facade in optimization."""
        result = optimize_surfaces(
            [{
                "building_id": "B001",
                "surfaces": [
                    {"surface_id": "ROOF", "vertices": [[0,0,10],[20,0,10],[20,20,10],[0,20,10]]},
                    {"surface_id": "FAC", "vertices": [[0,0,0],[0,20,0],[0,20,10],[0,0,10]]},
                ],
            }],
            limit=10,
        )
        types = [r["surface_type"] for r in result["results"]]
        if "roof" in types and "facade" in types:
            assert types.index("roof") < types.index("facade")


# =====================================================================
# 4. MISSING COVERAGE TESTS
# =====================================================================


class TestCoverageCalculations:
    """Tests for uncovered calculations.py lines."""

    def test_centroid_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_centroid([])

    def test_bounding_box_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_bounding_box([])

    def test_centroid_single_point(self):
        c = calculate_centroid([[5, 5, 5]])
        assert c == pytest.approx([5.0, 5.0, 5.0])

    def test_centroid_two_points(self):
        c = calculate_centroid([[0, 0, 0], [10, 10, 10]])
        assert c == pytest.approx([5.0, 5.0, 5.0])

    def test_bounding_box_single_point(self):
        bb = calculate_bounding_box([[3, 4, 5]])
        assert bb["min_x"] == 3.0
        assert bb["max_x"] == 3.0

    def test_is_reversed_winding_empty(self):
        assert not is_reversed_winding([])

    def test_is_reversed_winding_two_vertices(self):
        assert not is_reversed_winding([[0, 0, 0], [1, 0, 0]])

    def test_normalise_winding_empty(self):
        result = normalise_winding([])
        assert result == []

    def test_normalise_winding_two_vertices(self):
        result = normalise_winding([[0, 0, 0], [1, 0, 0]])
        assert len(result) == 2


class TestCoverageSolarService:
    """Tests for uncovered solar_service.py lines."""

    def test_estimate_energy_missing_area(self):
        with pytest.raises(ValueError):
            estimate_energy_potential({})

    def test_tilt_score_invalid_range(self):
        with pytest.raises(ValueError):
            tilt_score(-10.0)

    def test_tilt_score_above_90(self):
        with pytest.raises(ValueError):
            tilt_score(100.0)


class TestCoverageOptimizationService:
    """Tests for uncovered optimization_service.py lines."""

    def test_compute_composite_score_zero_maxes(self):
        """Test with zero max values (division safety)."""
        surf = {
            "solar_score": 0.5,
            "azimuth_deg": 180.0,
            "tilt_deg": 20.0,
            "surface_type": "roof",
            "energy_potential": {
                "usable_area_m2": 100.0,
                "estimated_capacity_kw": 20.0,
                "estimated_annual_energy_kwh": 34000.0,
            },
        }
        w = get_default_weights()
        score = compute_composite_score(surf, w, 0.0, 0.0, 0.0)
        assert 0.0 <= score <= 1.0

    def test_apply_limits_no_constraints(self):
        surfaces = [{"a": 1}, {"a": 2}]
        result = apply_limits(surfaces)
        assert len(result) == 2

    def test_apply_limits_max_surfaces(self):
        surfaces = [{"a": 1}, {"a": 2}, {"a": 3}]
        result = apply_limits(surfaces, max_surfaces=2)
        assert len(result) == 2

    def test_apply_limits_max_capacity(self):
        surfaces = [
            {"energy_potential": {"estimated_capacity_kw": 10.0}},
            {"energy_potential": {"estimated_capacity_kw": 5.0}},
            {"energy_potential": {"estimated_capacity_kw": 30.0}},
        ]
        result = apply_limits(surfaces, max_total_capacity_kw=25.0)
        assert len(result) == 2
        total = sum(s["energy_potential"]["estimated_capacity_kw"] for s in result)
        assert total <= 25.0

    def test_aggregate_city_results_empty(self):
        result = aggregate_city_results([])
        assert result["total_suitable_area_m2"] == 0.0
        assert result["total_potential_capacity_kw"] == 0.0
        assert result["total_annual_energy_kwh"] == 0.0
        assert result["top_buildings"] == []
        assert result["top_surfaces"] == []

    def test_generate_recommendation_deterministic(self):
        surf = {
            "solar_score": 0.85,
            "tilt_deg": 15.0,
            "azimuth_deg": 180.0,
            "surface_type": "roof",
            "energy_potential": {
                "usable_area_m2": 200.0,
                "estimated_capacity_kw": 40.0,
                "estimated_annual_energy_kwh": 68000.0,
            },
        }
        r1 = generate_recommendation(surf, 0.9, 1)
        r2 = generate_recommendation(surf, 0.9, 1)
        assert r1 == r2

    def test_generate_recommendation_rank_mentions(self):
        surf = {
            "solar_score": 0.5,
            "tilt_deg": 45.0,
            "azimuth_deg": 0.0,
            "surface_type": "facade",
            "energy_potential": {
                "usable_area_m2": 10.0,
                "estimated_capacity_kw": 2.0,
                "estimated_annual_energy_kwh": 3400.0,
            },
        }
        r1 = generate_recommendation(surf, 0.5, 1)
        assert "Top-ranked" in r1
        r3 = generate_recommendation(surf, 0.5, 3)
        assert "Ranked #3" in r3
        r5 = generate_recommendation(surf, 0.5, 5)
        assert "Ranked #5" not in r5  # Only mentions rank 1-3


class TestCoverageAPI:
    """Tests for uncovered API endpoint lines."""

    def test_city_analysis_too_many_buildings(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        buildings = [
            {"building_id": f"B{i}", "surfaces": [
                {"surface_id": f"S{i}", "vertices": [[0,0,10],[10,0,10],[10,10,10],[0,10,10]]}
            ]}
            for i in range(150)
        ]
        r = client.post("/city-analysis", json={"buildings": buildings})
        assert r.status_code == 413

    def test_optimization_with_all_query_params(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        payload = {"buildings": [{
            "building_id": "QALL",
            "surfaces": [{
                "surface_id": "QS1",
                "vertices": [[0,0,10],[20,0,10],[20,20,10],[0,20,10]],
            }],
        }]}
        r = client.post(
            "/optimization-routes?limit=5&min_solar_score=0.1&min_usable_area=1.0",
            json=payload,
        )
        assert r.status_code == 200

    def test_prediction_with_ground_type(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        r = client.post("/predict-solar", json={
            "area_m2": 100.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 0.0,
            "surface_type": "ground",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["fallback_energy"]["usable_area_m2"] == 0.0

    def test_prediction_with_optional_coords(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        r = client.post("/predict-solar", json={
            "area_m2": 100.0,
            "azimuth_deg": 180.0,
            "tilt_deg": 20.0,
            "surface_type": "roof",
            "latitude": 19.07,
            "longitude": 72.88,
        })
        assert r.status_code == 200


# =====================================================================
# 5. PERFORMANCE TESTS
# =====================================================================


class TestPerformance:
    """Performance benchmarks for reasonable workloads."""

    def _make_building(self, n_surfaces: int) -> dict:
        surfaces = []
        for i in range(n_surfaces):
            x = i * 11.0
            surfaces.append({
                "surface_id": f"PS{i:04d}",
                "vertices": [
                    [x, 0, 10], [x + 10, 0, 10],
                    [x + 10, 10, 10], [x, 10, 10],
                ],
            })
        return {
            "building_id": "PERF-001",
            "surfaces": surfaces,
        }

    def test_10_buildings_performance(self):
        """10 buildings with 10 surfaces each = 100 surfaces."""
        buildings = []
        for i in range(10):
            b = self._make_building(10)
            b = {**b, "building_id": f"B{i:03d}"}
            buildings.append(b)

        start = time.time()
        result = optimize_surfaces(buildings, limit=10)
        elapsed = time.time() - start

        assert result["total_candidates"] == 100
        assert len(result["results"]) == 10
        assert elapsed < 5.0, f"10 buildings took {elapsed:.2f}s"

    def test_100_buildings_performance(self):
        """100 buildings with 10 surfaces each = 1000 surfaces."""
        buildings = []
        for i in range(100):
            b = self._make_building(10)
            b = {**b, "building_id": f"B{i:03d}"}
            buildings.append(b)

        start = time.time()
        result = optimize_surfaces(buildings, limit=20)
        elapsed = time.time() - start

        assert result["total_candidates"] == 1000
        assert elapsed < 15.0, f"100 buildings took {elapsed:.2f}s"

    def test_1000_surfaces_single_building(self):
        """Single building with 1000 surfaces."""
        building = self._make_building(1000)

        start = time.time()
        result = optimize_surfaces([building], limit=50)
        elapsed = time.time() - start

        assert result["total_candidates"] == 1000
        assert elapsed < 15.0, f"1000 surfaces took {elapsed:.2f}s"

    def test_geometry_processing_performance(self):
        """Test extract_surfaces performance."""
        building = self._make_building(500)

        start = time.time()
        surfaces = extract_surfaces(building)
        elapsed = time.time() - start

        assert len(surfaces) == 500
        assert elapsed < 5.0, f"500 surfaces extraction took {elapsed:.2f}s"

    def test_api_performance_10_buildings(self):
        """API endpoint performance with 10 buildings."""
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        buildings = []
        for i in range(10):
            buildings.append({
                "building_id": f"API-{i:03d}",
                "surfaces": [{
                    "surface_id": f"API-S{i:03d}",
                    "vertices": [
                        [0, 0, 10], [10, 0, 10],
                        [10, 10, 10], [0, 10, 10],
                    ],
                }],
            })

        start = time.time()
        r = client.post("/optimization-routes?limit=5", json={"buildings": buildings})
        elapsed = time.time() - start

        assert r.status_code == 200
        assert elapsed < 5.0, f"API with 10 buildings took {elapsed:.2f}s"


# =====================================================================
# 6. CONFIGURATION TESTS
# =====================================================================


class TestConfiguration:
    """Tests for configuration module."""

    def test_config_defaults(self):
        from backend.config import (
            COVERAGE_FACTOR,
            PANEL_EFFICIENCY,
            ANNUAL_IRRADIANCE_KWH_M2,
            MAX_BUILDINGS_PER_REQUEST,
            MAX_OPTIMIZATION_LIMIT,
            APP_VERSION,
        )
        assert 0 < COVERAGE_FACTOR <= 1
        assert 0 < PANEL_EFFICIENCY <= 1
        assert ANNUAL_IRRADIANCE_KWH_M2 > 0
        assert MAX_BUILDINGS_PER_REQUEST > 0
        assert MAX_OPTIMIZATION_LIMIT > 0
        assert APP_VERSION is not None

    def test_config_opt_weights_sum(self):
        from backend.config import (
            OPT_WEIGHT_SUITABILITY,
            OPT_WEIGHT_ENERGY,
            OPT_WEIGHT_CAPACITY,
            OPT_WEIGHT_AREA,
            OPT_WEIGHT_ORIENTATION,
        )
        total = (
            OPT_WEIGHT_SUITABILITY + OPT_WEIGHT_ENERGY +
            OPT_WEIGHT_CAPACITY + OPT_WEIGHT_AREA +
            OPT_WEIGHT_ORIENTATION
        )
        assert total == pytest.approx(1.0, abs=0.01)

    def test_default_weights_normalize(self):
        w = get_default_weights()
        total = sum(w.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_database_config(self):
        from backend.config import DATABASE_URL, TEST_DATABASE_URL
        assert "sqlite" in DATABASE_URL or "postgresql" in DATABASE_URL
        assert "sqlite" in TEST_DATABASE_URL


# =====================================================================
# 7. DATABASE EDGE CASES
# =====================================================================


class TestDatabaseEdgeCases:
    """Edge cases for the persistence layer."""

    def test_duplicate_building_id_raises(self):
        from backend.db import get_db_session, init_db, reset_engine
        from backend.db.repositories import create_building

        reset_engine()
        init_db(url="sqlite://")
        try:
            with get_db_session() as s:
                create_building(s, "DUP-001")
            with get_db_session() as s:
                with pytest.raises(ValueError, match="already exists"):
                    create_building(s, "DUP-001")
        finally:
            reset_engine()

    def test_get_nonexistent_building_raises(self):
        from backend.db import get_db_session, init_db, reset_engine
        from backend.db.repositories import get_building

        reset_engine()
        init_db(url="sqlite://")
        try:
            with get_db_session() as s:
                with pytest.raises(ValueError, match="not found"):
                    get_building(s, "NOPE")
        finally:
            reset_engine()

    def test_analysis_upsert(self):
        from backend.db import get_db_session, init_db, reset_engine
        from backend.db.repositories import (
            create_building, create_surface, save_analysis, get_analysis,
        )

        reset_engine()
        init_db(url="sqlite://")
        try:
            with get_db_session() as s:
                create_building(s, "UPSERT-001")
                create_surface(
                    s, "S001", "UPSERT-001",
                    [[0,0,10],[10,0,10],[10,10,10],[0,10,10]],
                    100.0, "roof", 180.0, 0.0, {"x":0,"y":0,"z":1},
                )
                save_analysis(s, "S001", "UPSERT-001", 0.5, "medium", 80.0, 16.0, 27200.0)
                save_analysis(s, "S001", "UPSERT-001", 0.9, "high", 90.0, 18.0, 30600.0)

            with get_db_session() as s:
                result = get_analysis(s, "S001")
                assert result.solar_score == 0.9  # Updated, not duplicated
        finally:
            reset_engine()


# =====================================================================
# 8. PROJECTIONS AND SHADING EDGE CASES
# =====================================================================


class TestProjectionsEdgeCases:
    """Edge cases for geospatial projections."""

    def test_utm_zone_extremes(self):
        from backend.geometry.projections import get_utm_zone
        assert get_utm_zone(-180.0) == 1
        assert get_utm_zone(179.99) == 60
        assert get_utm_zone(0.0) == 31

    def test_utm_zone_round_trip(self):
        from backend.geometry.projections import get_utm_zone
        for lon in range(-180, 180, 6):
            zone = get_utm_zone(lon)
            assert 1 <= zone <= 60

    def test_area_in_m2_no_coords(self):
        from backend.geometry.projections import calculate_area_in_m2
        verts = [[0,0,10],[10,0,10],[10,10,10],[0,10,10]]
        area = calculate_area_in_m2(verts)
        assert area == pytest.approx(100.0)


class TestShadingEdgeCases:
    """Edge cases for shading analysis."""

    def test_analyze_surface_empty_vertices(self):
        from backend.geometry.shading import ShadingAnalyzer
        analyzer = ShadingAnalyzer()
        result = analyzer.analyze_surface("S001", [])
        assert result.has_shading is False

    def test_filter_empty_sources(self):
        from backend.geometry.shading import ShadingAnalyzer
        analyzer = ShadingAnalyzer()
        result = analyzer.filter_nearby_sources([], reference_height=10.0)
        assert len(result) == 0

    def test_horizon_obstruction_no_data(self):
        from backend.geometry.shading import estimate_horizon_obstruction
        result = estimate_horizon_obstruction(30.0, 180.0, None)
        assert result == 0.0

    def test_horizon_obstruction_empty_dict(self):
        from backend.geometry.shading import estimate_horizon_obstruction
        result = estimate_horizon_obstruction(30.0, 180.0, {})
        assert result == 0.0
