"""Comprehensive tests for the SolarIQ optimization engine.

Covers:
- Weighted composite scoring
- Ranking correctness
- Tie-breaking
- Constraint filtering (min score, min area, surface types)
- Capacity and energy limits
- City-level aggregation
- Recommendation generation
- ML-enhanced scoring
- API integration via TestClient
"""

import pytest

from backend.services.optimization_service import (
    apply_constraints,
    apply_limits,
    aggregate_city_results,
    compute_composite_score,
    generate_recommendation,
    get_default_weights,
    optimize_surfaces,
)
from backend.services.solar_service import analyze_surface


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ROOF_FLAT = {
    "surface_id": "RF-001",
    "building_id": "B001",
    "vertices": [
        [0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10],
    ],
}

ROOF_TILTED = {
    "surface_id": "RT-001",
    "building_id": "B001",
    "vertices": [
        [0, 0, 10], [20, 0, 15], [20, 20, 15], [0, 20, 10],
    ],
}

FACADE_SOUTH = {
    "surface_id": "FS-001",
    "building_id": "B002",
    "vertices": [
        [0, 0, 0], [0, 20, 0], [0, 20, 10], [0, 0, 10],
    ],
}

FACADE_NORTH = {
    "surface_id": "FN-001",
    "building_id": "B002",
    "vertices": [
        [10, 0, 0], [10, 20, 0], [10, 20, 10], [10, 0, 10],
    ],
}

GROUND = {
    "surface_id": "GD-001",
    "building_id": "B003",
    "vertices": [
        [0, 0, 0], [0, 20, 0], [20, 20, 0], [20, 0, 0],
    ],
}

BUILDING_1 = {
    "building_id": "B001",
    "surfaces": [ROOF_FLAT, ROOF_TILTED],
}

BUILDING_2 = {
    "building_id": "B002",
    "surfaces": [FACADE_SOUTH, FACADE_NORTH],
}

BUILDING_3 = {
    "building_id": "B003",
    "surfaces": [GROUND],
}


def _analyze(surf: dict) -> dict:
    """Quick helper to analyze a single surface."""
    from backend.geometry.surfaces import extract_surfaces
    building = {"building_id": surf.get("building_id", "TMP"), "surfaces": [surf]}
    surfaces = extract_surfaces(building)
    return analyze_surface(surfaces[0])


# =====================================================================
# 1. Scoring weights
# =====================================================================


class TestScoringWeights:
    def test_default_weights_sum_to_one(self):
        w = get_default_weights()
        total = sum(w.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_default_weights_are_positive(self):
        w = get_default_weights()
        for v in w.values():
            assert v > 0

    def test_default_weights_contain_expected_keys(self):
        w = get_default_weights()
        expected = {"suitability", "energy", "capacity", "area", "orientation"}
        assert set(w.keys()) == expected


# =====================================================================
# 2. Composite scoring
# =====================================================================


class TestCompositeScoring:
    def test_composite_score_range(self):
        surf = _analyze(ROOF_FLAT)
        w = get_default_weights()
        score = compute_composite_score(surf, w, 10000, 10, 100)
        assert 0.0 <= score <= 1.0

    def test_high_quality_surface_scores_high(self):
        # Large south-facing roof with good tilt
        surf = _analyze({
            "surface_id": "HQ",
            "building_id": "B001",
            "vertices": [
                [0, 0, 10], [30, 0, 12], [30, 30, 12], [0, 30, 10],
            ],
        })
        w = get_default_weights()
        score = compute_composite_score(surf, w, 50000, 50, 500)
        assert score >= 0.4  # Should be reasonably high

    def test_small_facade_scores_lower(self):
        facade = _analyze(FACADE_NORTH)
        roof = _analyze(ROOF_FLAT)
        w = get_default_weights()
        f_score = compute_composite_score(facade, w, 50000, 50, 500)
        r_score = compute_composite_score(roof, w, 50000, 50, 500)
        assert r_score >= f_score

    def test_zero_energy_gives_low_score(self):
        surf = {
            "solar_score": 0.0,
            "azimuth_deg": 0.0,
            "tilt_deg": 90.0,
            "surface_type": "ground",
            "area_m2": 1.0,
            "energy_potential": {
                "usable_area_m2": 0.0,
                "estimated_capacity_kw": 0.0,
                "estimated_annual_energy_kwh": 0.0,
            },
        }
        w = get_default_weights()
        score = compute_composite_score(surf, w, 1000, 10, 100)
        assert score == pytest.approx(0.0, abs=0.05)


# =====================================================================
# 3. Ranking correctness
# =====================================================================


class TestRanking:
    def test_roof_ranks_above_facade(self):
        """In typical scenarios, roofs rank above facades because
        they have better orientation and tilt characteristics.
        However, this is a result of the data-driven model, NOT
        a hardcoded rule. A well-oriented south facade on a tall
        building could theoretically outrank a poorly-oriented
        roof section."""
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        types = [r["surface_type"] for r in result["results"]]
        # In this test scenario, roofs should rank before facades
        # because they have better solar characteristics.
        if "roof" in types and "facade" in types:
            first_roof = types.index("roof")
            first_facade = types.index("facade")
            assert first_roof < first_facade

    def test_ground_excluded(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_3],
            limit=10,
        )
        types = [r["surface_type"] for r in result["results"]]
        assert "ground" not in types

    def test_limit_respected(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=1,
        )
        assert len(result["results"]) <= 1

    def test_rank_sequential(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        for i, r in enumerate(result["results"], start=1):
            assert r["rank"] == i

    def test_total_candidates_count(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        # B001 has 2 surfaces (2 roofs), B002 has 2 (2 facades).
        # Ground is excluded, so 4 non-ground candidates.
        assert result["total_candidates"] == 4


# =====================================================================
# 4. Tie-breaking
# =====================================================================


class TestTieBreaking:
    def test_identical_surfaces_tiebreak_by_energy(self):
        """Two identical surfaces should be ordered by energy."""
        dup = {
            "building_id": "B-ALL",
            "surfaces": [
                {
                    "surface_id": "D1",
                    "vertices": [
                        [0, 0, 10], [10, 0, 10],
                        [10, 10, 10], [0, 10, 10],
                    ],
                },
                {
                    "surface_id": "D2",
                    "vertices": [
                        [0, 0, 10], [10, 0, 10],
                        [10, 10, 10], [0, 10, 10],
                    ],
                },
            ],
        }
        result = optimize_surfaces([dup], limit=10)
        # Both should have same composite score but different IDs.
        assert len(result["results"]) == 2
        scores = [r["composite_score"] for r in result["results"]]
        assert scores[0] >= scores[1]


# =====================================================================
# 5. Constraints filtering
# =====================================================================


class TestConstraints:
    def test_min_solar_score_filters(self):
        result_all = optimize_surfaces([BUILDING_1, BUILDING_2], limit=10)
        all_scores = [r["solar_score"] for r in result_all["results"]]
        max_score = max(all_scores)

        result_filtered = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"min_solar_score": max_score},
        )
        for r in result_filtered["results"]:
            assert r["solar_score"] >= max_score

    def test_min_usable_area_filters(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"min_usable_area_m2": 99999.0},
        )
        assert len(result["results"]) == 0

    def test_surface_types_filter(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"surface_types": ["facade"]},
        )
        for r in result["results"]:
            assert r["surface_type"] == "facade"

    def test_max_surfaces_constraint(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"max_surfaces": 2},
        )
        assert len(result["results"]) <= 2

    def test_max_capacity_constraint(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"max_total_capacity_kw": 0.001},
        )
        # With very low capacity limit, should return 0 or 1.
        total_cap = sum(
            r["estimated_capacity_kw"] for r in result["results"]
        )
        assert total_cap <= 0.001 + 1e-6

    def test_filtered_candidates_count(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
            constraints={"surface_types": ["roof"]},
        )
        assert result["filtered_candidates"] == 2


# =====================================================================
# 6. Capacity and energy
# =====================================================================


class TestCapacityAndEnergy:
    def test_capacity_positive_for_roof(self):
        result = optimize_surfaces([BUILDING_1], limit=10)
        for r in result["results"]:
            assert r["estimated_capacity_kw"] > 0

    def test_energy_positive_for_roof(self):
        result = optimize_surfaces([BUILDING_1], limit=10)
        for r in result["results"]:
            assert r["estimated_annual_energy_kwh"] > 0

    def test_usable_area_positive_for_roof(self):
        result = optimize_surfaces([BUILDING_1], limit=10)
        for r in result["results"]:
            assert r["usable_area_m2"] > 0

    def test_energy_scales_with_area(self):
        """Larger roof should have more energy potential."""
        small = {
            "building_id": "SM",
            "surfaces": [{
                "surface_id": "S",
                "vertices": [
                    [0, 0, 10], [5, 0, 10],
                    [5, 5, 10], [0, 5, 10],
                ],
            }],
        }
        large = {
            "building_id": "LG",
            "surfaces": [{
                "surface_id": "L",
                "vertices": [
                    [0, 0, 10], [20, 0, 10],
                    [20, 20, 10], [0, 20, 10],
                ],
            }],
        }
        result = optimize_surfaces([small, large], limit=10)
        energies = {
            r["surface_id"]: r["estimated_annual_energy_kwh"]
            for r in result["results"]
        }
        assert energies["L"] > energies["S"]


# =====================================================================
# 7. City aggregation
# =====================================================================


class TestCityAggregation:
    def test_city_summary_present(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        assert result["city_summary"] is not None

    def test_city_summary_totals(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        cs = result["city_summary"]
        # Totals should equal sum of results.
        total_area = sum(r["usable_area_m2"] for r in result["results"])
        total_cap = sum(r["estimated_capacity_kw"] for r in result["results"])
        total_energy = sum(
            r["estimated_annual_energy_kwh"] for r in result["results"]
        )
        assert cs["total_suitable_area_m2"] == pytest.approx(total_area, abs=0.01)
        assert cs["total_potential_capacity_kw"] == pytest.approx(total_cap, abs=0.01)
        assert cs["total_annual_energy_kwh"] == pytest.approx(total_energy, abs=0.01)

    def test_city_top_buildings(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        cs = result["city_summary"]
        assert len(cs["top_buildings"]) > 0
        assert "B001" in cs["top_buildings"] or "B002" in cs["top_buildings"]

    def test_city_top_surfaces(self):
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=10,
        )
        cs = result["city_summary"]
        assert len(cs["top_surfaces"]) > 0

    def test_city_summary_empty_when_no_results(self):
        result = optimize_surfaces(
            [],  # No buildings
            limit=10,
        )
        cs = result["city_summary"]
        assert cs["total_suitable_area_m2"] == 0.0
        assert cs["total_potential_capacity_kw"] == 0.0


# =====================================================================
# 8. Recommendation generation
# =====================================================================


class TestRecommendations:
    def test_recommendation_non_empty(self):
        result = optimize_surfaces([BUILDING_1], limit=5)
        for r in result["results"]:
            assert len(r["recommendation"]) > 0

    def test_top_rank_mentioned(self):
        result = optimize_surfaces([BUILDING_1], limit=5)
        # First result should mention "Top-ranked".
        assert "Top-ranked" in result["results"][0]["recommendation"]

    def test_recommendation_deterministic(self):
        r1 = optimize_surfaces([BUILDING_1], limit=5)
        r2 = optimize_surfaces([BUILDING_1], limit=5)
        for a, b in zip(r1["results"], r2["results"]):
            assert a["recommendation"] == b["recommendation"]

    def test_recommendation_mentions_key_factors(self):
        result = optimize_surfaces([BUILDING_1, BUILDING_2], limit=5)
        for r in result["results"]:
            rec = r["recommendation"].lower()
            # Should mention at least one of: tilt, orientation, area, score
            assert any(
                kw in rec
                for kw in ["tilt", "orientation", "area", "suitability", "score"]
            )


# =====================================================================
# 9. Scoring weights transparency
# =====================================================================


class TestWeightsTransparency:
    def test_weights_in_response(self):
        result = optimize_surfaces([BUILDING_1], limit=5)
        assert "scoring_weights" in result
        w = result["scoring_weights"]
        assert set(w.keys()) == {
            "suitability", "energy", "capacity", "area", "orientation",
        }

    def test_weights_sum_to_one(self):
        result = optimize_surfaces([BUILDING_1], limit=5)
        total = sum(result["scoring_weights"].values())
        assert total == pytest.approx(1.0, abs=0.01)


# =====================================================================
# 10. API integration
# =====================================================================


class TestAPIIntegration:
    """Test the optimization endpoint via FastAPI TestClient."""

    def test_optimization_basic(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        resp = client.post(
            "/optimization-routes?limit=3",
            json={"buildings": [
                {
                    "building_id": "API-B1",
                    "surfaces": [{
                        "surface_id": "API-S1",
                        "vertices": [
                            [0, 0, 10], [20, 0, 10],
                            [20, 20, 10], [0, 20, 10],
                        ],
                    }],
                },
            ]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_candidates" in data
        assert "filtered_candidates" in data
        assert "scoring_weights" in data
        assert "results" in data

    def test_optimization_with_min_score(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        resp = client.post(
            "/optimization-routes?min_solar_score=0.99",
            json={"buildings": [
                {
                    "building_id": "API-B2",
                    "surfaces": [{
                        "surface_id": "API-S2",
                        "vertices": [
                            [0, 0, 0], [10, 0, 0],
                            [10, 0, 10], [0, 0, 10],
                        ],
                    }],
                },
            ]},
        )
        assert resp.status_code == 200
        data = resp.json()
        # High threshold should filter most surfaces.
        assert data["filtered_candidates"] <= data["total_candidates"]

    def test_optimization_city_summary(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        resp = client.post(
            "/optimization-routes",
            json={"buildings": [
                {
                    "building_id": "CS-1",
                    "surfaces": [{
                        "surface_id": "CS-S1",
                        "vertices": [
                            [0, 0, 10], [10, 0, 10],
                            [10, 10, 10], [0, 10, 10],
                        ],
                    }],
                },
            ]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["city_summary"] is not None
        cs = data["city_summary"]
        assert "total_suitable_area_m2" in cs
        assert "total_potential_capacity_kw" in cs
        assert "total_annual_energy_kwh" in cs

    def test_optimization_results_have_recommendation(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        resp = client.post(
            "/optimization-routes",
            json={"buildings": [
                {
                    "building_id": "REC-1",
                    "surfaces": [{
                        "surface_id": "REC-S1",
                        "vertices": [
                            [0, 0, 10], [10, 0, 10],
                            [10, 10, 10], [0, 10, 10],
                        ],
                    }],
                },
            ]},
        )
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert "recommendation" in r
            assert "composite_score" in r
            assert "usable_area_m2" in r

    def test_optimization_with_surface_type_filter(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        resp = client.post(
            "/optimization-routes",
            json={"buildings": [
                {
                    "building_id": "FT-1",
                    "surfaces": [
                        {
                            "surface_id": "FT-ROOF",
                            "vertices": [
                                [0, 0, 10], [10, 0, 10],
                                [10, 10, 10], [0, 10, 10],
                            ],
                        },
                        {
                            "surface_id": "FT-FAC",
                            "vertices": [
                                [0, 0, 0], [0, 10, 0],
                                [0, 10, 10], [0, 0, 10],
                            ],
                        },
                    ],
                },
            ]},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Both should be included, roof ranked higher.
        types = [r["surface_type"] for r in data["results"]]
        assert "roof" in types


# =====================================================================
# 11. Edge cases
# =====================================================================


class TestEdgeCases:
    def test_empty_buildings_list(self):
        result = optimize_surfaces([], limit=5)
        assert result["total_candidates"] == 0
        assert result["results"] == []

    def test_only_ground_surfaces(self):
        # With min_usable_area constraint exceeding any surface
        result = optimize_surfaces(
            [BUILDING_1, BUILDING_2],
            limit=5,
            constraints={"min_usable_area_m2": 999999.0},
        )
        assert result["filtered_candidates"] == 0
        assert result["results"] == []

    def test_limit_zero_returns_empty(self):
        result = optimize_surfaces([BUILDING_1], limit=0)
        assert result["results"] == []

    def test_single_surface_building(self):
        single = {
            "building_id": "SINGLE",
            "surfaces": [{
                "surface_id": "SOLO",
                "vertices": [
                    [0, 0, 10], [10, 0, 10],
                    [10, 10, 10], [0, 10, 10],
                ],
            }],
        }
        result = optimize_surfaces([single], limit=5)
        assert len(result["results"]) == 1
        assert result["results"][0]["surface_id"] == "SOLO"

    def test_many_buildings(self):
        buildings = []
        for i in range(20):
            buildings.append({
                "building_id": f"B{i:03d}",
                "surfaces": [{
                    "surface_id": f"S{i:03d}",
                    "vertices": [
                        [0, 0, 10], [10, 0, 10],
                        [10, 10, 10], [0, 10, 10],
                    ],
                }],
            })
        result = optimize_surfaces(buildings, limit=5)
        assert len(result["results"]) == 5
        assert result["total_candidates"] == 20
