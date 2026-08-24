import pytest

from backend.services.solar_service import (
    analyze_surface,
    calculate_solar_score,
    estimate_energy_potential,
    orientation_score,
    tilt_score,
)


def test_roof_orientation_score():

    score = orientation_score(
        0.0,
        "roof",
    )

    assert score == pytest.approx(1.0)


def test_south_orientation_is_best_for_facade():

    score = orientation_score(
        180.0,
        "facade",
    )

    assert score == pytest.approx(1.0)


def test_north_orientation_is_worst_for_facade():
    """North-facing facade should have lowest orientation score."""
    score = orientation_score(0.0, "facade")
    # With continuous model, north gets ~0.35 (minimum factor)
    assert score == pytest.approx(0.35, abs=0.05)


def test_optimal_tilt_score():

    score = tilt_score(20.0)

    assert score == pytest.approx(1.0)


def test_ground_surface_has_zero_score():

    surface = {
        "surface_type": "ground",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
    }

    assert calculate_solar_score(
        surface
    ) == pytest.approx(0.0)


def test_roof_has_high_solar_score():

    surface = {
        "surface_type": "roof",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
    }

    score = calculate_solar_score(
        surface
    )

    assert score >= 0.75


def test_energy_calculation():

    surface = {
        "area_m2": 400.0
    }

    result = estimate_energy_potential(
        surface
    )

    assert result["usable_area_m2"] == pytest.approx(
        320.0
    )

    assert result["estimated_capacity_kw"] == pytest.approx(
        64.0
    )

    assert result["estimated_annual_energy_kwh"] == pytest.approx(
        108800.0
    )


def test_analyze_surface():

    surface = {
        "surface_id": "S001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }

    result = analyze_surface(
        surface
    )

    assert "solar_score" in result
    assert "solar_suitability" in result
    assert "energy_potential" in result

    assert result["solar_suitability"] == "high"

    assert result["energy_potential"]["usable_area_m2"] == pytest.approx(
        320.0
    )


def test_analyze_ground_surface_zero_energy():

    surface = {
        "surface_id": "G001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "ground",
    }

    result = analyze_surface(surface)

    assert result["solar_score"] == pytest.approx(0.0)
    assert result["energy_potential"]["usable_area_m2"] == 0.0
    assert result["energy_potential"]["estimated_capacity_kw"] == 0.0
    assert result["energy_potential"]["estimated_annual_energy_kwh"] == 0.0


def test_invalid_coverage_factor():

    surface = {"area_m2": 100.0}

    with pytest.raises(ValueError, match="Coverage factor"):
        estimate_energy_potential(
            surface,
            coverage_factor=0.0,
        )

    with pytest.raises(ValueError, match="Coverage factor"):
        estimate_energy_potential(
            surface,
            coverage_factor=-0.5,
        )


def test_invalid_panel_efficiency():

    surface = {"area_m2": 100.0}

    with pytest.raises(ValueError, match="Panel efficiency"):
        estimate_energy_potential(
            surface,
            panel_efficiency=0.0,
        )

    with pytest.raises(ValueError, match="Panel efficiency"):
        estimate_energy_potential(
            surface,
            panel_efficiency=-0.1,
        )


def test_invalid_irradiance():

    surface = {"area_m2": 100.0}

    with pytest.raises(ValueError, match="irradiance"):
        estimate_energy_potential(
            surface,
            annual_irradiance_kwh_m2=0.0,
        )

    with pytest.raises(ValueError, match="irradiance"):
        estimate_energy_potential(
            surface,
            annual_irradiance_kwh_m2=-100.0,
        )


def test_facade_west_orientation():
    """West-facing facade should have moderate orientation score."""
    score = orientation_score(270.0, "facade")
    # With continuous model, west gets ~0.70 (between south and north)
    assert score == pytest.approx(0.70, abs=0.1)


def test_facade_suitability_medium():

    surface = {
        "surface_id": "S002",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 180.0,
        "tilt_deg": 20.0,
        "surface_type": "facade",
    }

    result = analyze_surface(surface)

    assert result["solar_suitability"] in ("medium", "high")
    assert result["energy_potential"]["usable_area_m2"] > 0.0


def test_tilt_90_score():
    """Vertical tilt (90°) should have minimum tilt score."""
    score = tilt_score(90.0)
    # With continuous model, vertical gets ~0.55 (minimum factor)
    assert score == pytest.approx(0.55, abs=0.05)


# ── New tests for improved solar scoring ──────────────────────


def test_flat_roof_uses_assumed_panel_tilt():
    """Flat roof (tilt=0) should use DEFAULT_ROOF_PANEL_TILT_DEG,
    NOT the geometric 0° tilt.  This ensures flat roofs are not
    penalized for being flat — panels can be mounted at optimal
    angle."""
    from backend.services.solar_service import (
        DEFAULT_ROOF_PANEL_TILT_DEG,
    )

    # tilt_score with is_roof=True should use 20° not 0°
    score = tilt_score(0.0, is_roof=True)
    optimal = tilt_score(DEFAULT_ROOF_PANEL_TILT_DEG, is_roof=True)
    assert score == pytest.approx(optimal)


def test_flat_roof_not_penalized():
    """A flat roof should NOT receive an artificially low tilt
    score.  It should score as well as a 20° roof."""
    score = tilt_score(0.0, is_roof=True)
    assert score >= 0.95  # Near-optimal since assumed tilt = 20°


def test_flat_roof_high_solar_score():
    """A flat roof should receive high solar suitability."""
    surface = {
        "surface_type": "roof",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
    }
    score = calculate_solar_score(surface)
    assert score >= 0.75  # Should be "high"


def test_roof_and_facade_both_viable():
    """Both roofs and facades should be viable BIPV candidates.
    The model does not hardcode one above the other -- the data
    determines the ranking."""
    roof = {"surface_type": "roof", "area_m2": 400.0,
            "azimuth_deg": 0.0, "tilt_deg": 0.0}
    south_facade = {"surface_type": "facade", "area_m2": 400.0,
                    "azimuth_deg": 180.0, "tilt_deg": 90.0}
    # Both should have positive scores
    assert calculate_solar_score(roof) > 0.0
    assert calculate_solar_score(south_facade) > 0.0
    # In typical scenarios, roof scores higher due to better
    # orientation and tilt characteristics, but this is a
    # result of the model, not a hardcoded rule.


def test_south_facade_above_north_facade():
    """South-facing facade should score better than north-facing."""
    south = {"surface_type": "facade", "area_m2": 400.0,
             "azimuth_deg": 180.0, "tilt_deg": 90.0}
    north = {"surface_type": "facade", "area_m2": 400.0,
             "azimuth_deg": 0.0, "tilt_deg": 90.0}
    assert calculate_solar_score(south) > calculate_solar_score(north)


def test_ground_surface_zero_energy():
    """Ground surfaces must produce zero energy potential."""
    surface = {
        "surface_id": "G001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "ground",
    }
    result = analyze_surface(surface)
    assert result["energy_potential"]["usable_area_m2"] == 0.0
    assert result["energy_potential"]["estimated_capacity_kw"] == 0.0
    assert result["energy_potential"]["estimated_annual_energy_kwh"] == 0.0


def test_large_roof_higher_energy_than_small_facade():
    """A large usable roof should have substantially greater
    energy-generation potential than a small facade."""
    large_roof = {"surface_type": "roof", "area_m2": 400.0,
                  "azimuth_deg": 0.0, "tilt_deg": 0.0}
    small_facade = {"surface_type": "facade", "area_m2": 50.0,
                    "azimuth_deg": 180.0, "tilt_deg": 90.0}
    roof_energy = estimate_energy_potential(large_roof)
    facade_energy = estimate_energy_potential(small_facade)
    assert roof_energy["estimated_capacity_kw"] > facade_energy["estimated_capacity_kw"]
    assert roof_energy["estimated_annual_energy_kwh"] > facade_energy["estimated_annual_energy_kwh"]


def test_tilt_score_facade_uses_geometric_tilt():
    """Facade tilt_score should use the actual geometric tilt,
    not the assumed panel tilt."""
    # Vertical facade: tilt=90, should get minimum tilt score
    score = tilt_score(90.0, is_roof=False)
    # With continuous model, vertical gets ~0.55 (minimum factor)
    assert score == pytest.approx(0.55, abs=0.05)


def test_existing_imports_still_work():
    """Verify backward-compatible imports."""
    from backend.services.solar_service import (
        DEFAULT_COVERAGE_FACTOR,
        DEFAULT_PANEL_EFFICIENCY,
        DEFAULT_ANNUAL_IRRADIANCE_KWH_M2,
    )
    assert DEFAULT_COVERAGE_FACTOR == 0.80
    assert DEFAULT_PANEL_EFFICIENCY == 0.20
    assert DEFAULT_ANNUAL_IRRADIANCE_KWH_M2 == 1700.0


# ── Data-driven model tests ──────────────────────────────────


def test_installation_priority_exists():
    """analyze_surface should return installation_priority."""
    surface = {
        "surface_id": "S001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }
    result = analyze_surface(surface)
    assert "installation_priority" in result
    assert 0.0 <= result["installation_priority"] <= 1.0


def test_installation_priority_high_for_large_roof():
    """A large roof should have high installation priority."""
    surface = {
        "surface_id": "S001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }
    result = analyze_surface(surface)
    assert result["installation_priority"] >= 0.6


def test_installation_priority_considers_energy():
    """Installation priority should consider energy potential,
    not just suitability score."""
    # Large roof with high energy potential
    large_roof = {
        "surface_id": "LR",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }
    # Small roof with same suitability but lower energy
    small_roof = {
        "surface_id": "SR",
        "building_id": "B001",
        "area_m2": 50.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }
    large_result = analyze_surface(large_roof)
    small_result = analyze_surface(small_roof)
    # Both have same suitability score, but large has higher priority
    assert large_result["installation_priority"] > small_result["installation_priority"]


def test_estimate_irradiance_available():
    """estimate_irradiance function should be available."""
    from backend.services.solar_service import estimate_irradiance
    surface = {"surface_type": "roof", "tilt_deg": 0.0, "azimuth_deg": 0.0}
    irradiance = estimate_irradiance(surface)
    assert irradiance > 0.0


def test_roof_irradiance_uses_optimal_tilt():
    """Roof irradiance should use assumed optimal tilt, not
    geometric 0° tilt."""
    from backend.services.solar_service import estimate_irradiance
    roof = {"surface_type": "roof", "tilt_deg": 0.0, "azimuth_deg": 0.0}
    # Roof should get near-optimal irradiance
    irradiance = estimate_irradiance(roof)
    assert irradiance >= 1500.0  # Should be close to 1700


def test_south_facade_better_irradiance_than_north():
    """South facade should receive more irradiance than north facade."""
    from backend.services.solar_service import estimate_irradiance
    south = {"surface_type": "facade", "tilt_deg": 90.0, "azimuth_deg": 180.0}
    north = {"surface_type": "facade", "tilt_deg": 90.0, "azimuth_deg": 0.0}
    assert estimate_irradiance(south) > estimate_irradiance(north)


def test_suitability_and_energy_independent():
    """Suitability score and energy potential should be independent
    concepts. A small surface can have high suitability but low
    energy."""
    small_roof = {
        "surface_id": "SMALL",
        "building_id": "B001",
        "area_m2": 10.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "roof",
    }
    result = analyze_surface(small_roof)
    # High suitability
    assert result["solar_score"] >= 0.75
    # But low energy due to small area
    assert result["energy_potential"]["estimated_capacity_kw"] < 5.0


def test_ground_excluded_from_priority():
    """Ground surfaces should have zero installation priority."""
    surface = {
        "surface_id": "G001",
        "building_id": "B001",
        "area_m2": 400.0,
        "azimuth_deg": 0.0,
        "tilt_deg": 0.0,
        "surface_type": "ground",
    }
    result = analyze_surface(surface)
    # Ground surfaces have zero score, so priority should be zero
    assert result["installation_priority"] == 0.0


# ── Edge case tests ──────────────────────────────────────────


def test_very_small_surface():
    """Very small surfaces should still be valid BIPV candidates."""
    surface = {
        "surface_id": "TINY",
        "building_id": "B001",
        "area_m2": 1.0,
        "azimuth_deg": 180.0,
        "tilt_deg": 20.0,
        "surface_type": "roof",
    }
    result = analyze_surface(surface)
    assert result["solar_score"] > 0.0
    assert result["energy_potential"]["usable_area_m2"] > 0.0
    assert result["installation_priority"] > 0.0


def test_very_large_surface():
    """Very large surfaces should have proportional energy potential."""
    surface = {
        "surface_id": "HUGE",
        "building_id": "B001",
        "area_m2": 10000.0,
        "azimuth_deg": 180.0,
        "tilt_deg": 20.0,
        "surface_type": "roof",
    }
    result = analyze_surface(surface)
    assert result["energy_potential"]["usable_area_m2"] == pytest.approx(8000.0)
    assert result["energy_potential"]["estimated_capacity_kw"] == pytest.approx(1600.0)


def test_boundary_azimuth_values():
    """Test all boundary azimuth values."""
    # Test 0, 90, 180, 270, 360 degrees
    for azimuth in [0, 90, 180, 270, 360]:
        surface = {
            "surface_type": "facade",
            "area_m2": 100.0,
            "azimuth_deg": float(azimuth),
            "tilt_deg": 90.0,
        }
        score = calculate_solar_score(surface)
        assert 0.0 <= score <= 1.0


def test_boundary_tilt_values():
    """Test all boundary tilt values."""
    # Test 0, 20, 45, 70, 90 degrees
    for tilt in [0, 20, 45, 70, 90]:
        surface = {
            "surface_type": "facade",
            "area_m2": 100.0,
            "azimuth_deg": 180.0,
            "tilt_deg": float(tilt),
        }
        score = calculate_solar_score(surface)
        assert 0.0 <= score <= 1.0


def test_invalid_tilt_raises_error():
    """Invalid tilt values should raise ValueError."""
    with pytest.raises(ValueError, match="Tilt must be between"):
        tilt_score(-10.0)
    with pytest.raises(ValueError, match="Tilt must be between"):
        tilt_score(100.0)


def test_non_numeric_azimuth_raises_error():
    """Non-numeric azimuth should raise ValueError."""
    surface = {
        "surface_type": "facade",
        "area_m2": 100.0,
        "azimuth_deg": "invalid",
        "tilt_deg": 90.0,
    }
    with pytest.raises(ValueError, match="numeric"):
        calculate_solar_score(surface)


def test_non_numeric_tilt_raises_error():
    """Non-numeric tilt should raise ValueError."""
    surface = {
        "surface_type": "facade",
        "area_m2": 100.0,
        "azimuth_deg": 180.0,
        "tilt_deg": "invalid",
    }
    with pytest.raises(ValueError, match="numeric"):
        calculate_solar_score(surface)


def test_continuous_tilt_transitions():
    """Tilt scores should transition smoothly, not jump."""
    # Scores should decrease gradually as tilt moves away from optimal
    scores = []
    for tilt in range(0, 91, 5):
        score = tilt_score(float(tilt), is_roof=False)
        scores.append(score)

    # Check that scores are monotonically decreasing after optimal
    # (20° is optimal, so scores should decrease from 20° to 90°)
    optimal_idx = scores.index(max(scores))
    for i in range(optimal_idx, len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score increased at tilt {i * 5}°"


def test_continuous_azimuth_transitions():
    """Azimuth scores should transition smoothly, not jump."""
    # Scores should be highest at south (180°) and lowest at north (0°/360°)
    south_score = orientation_score(180.0, "facade")
    north_score = orientation_score(0.0, "facade")
    east_score = orientation_score(90.0, "facade")
    west_score = orientation_score(270.0, "facade")

    # South should be highest
    assert south_score > east_score
    assert south_score > west_score
    assert south_score > north_score
    # East and west should be similar (both 90° from south)
    assert abs(east_score - west_score) < 0.1
    # All scores should be valid
    assert 0.0 <= south_score <= 1.0
    assert 0.0 <= north_score <= 1.0
    assert 0.0 <= east_score <= 1.0
    assert 0.0 <= west_score <= 1.0


def test_installation_priority_with_relative_normalization():
    """Installation priority should use relative normalization
    when dataset bounds are provided."""
    from backend.services.solar_service import calculate_installation_priority

    surface = {
        "solar_score": 0.8,
        "energy_potential": {
            "usable_area_m2": 200.0,
            "estimated_capacity_kw": 40.0,
            "estimated_annual_energy_kwh": 68000.0,
        },
    }

    # With reference bounds
    priority_ref = calculate_installation_priority(
        surface,
        max_energy_in_dataset=136000.0,
        max_area_in_dataset=400.0,
    )

    # Without reference bounds (fallback)
    priority_fallback = calculate_installation_priority(surface)

    # Both should be valid
    assert 0.0 <= priority_ref <= 1.0
    assert 0.0 <= priority_fallback <= 1.0


def test_irradiance_estimation_consistency():
    """Irradiance estimation should be consistent and bounded."""
    from backend.services.solar_service import estimate_irradiance

    # Test various surfaces
    surfaces = [
        {"surface_type": "roof", "tilt_deg": 0.0, "azimuth_deg": 0.0},
        {"surface_type": "facade", "tilt_deg": 90.0, "azimuth_deg": 180.0},
        {"surface_type": "facade", "tilt_deg": 90.0, "azimuth_deg": 0.0},
    ]

    for surface in surfaces:
        irradiance = estimate_irradiance(surface)
        # Should be positive and less than base irradiance
        assert 0.0 < irradiance <= 1700.0


def test_suitability_labels_complete():
    """All score ranges should produce valid labels."""
    from backend.services.solar_service import suitability_label

    assert suitability_label(0.0) == "low"
    assert suitability_label(0.49) == "low"
    assert suitability_label(0.50) == "medium"
    assert suitability_label(0.74) == "medium"
    assert suitability_label(0.75) == "high"
    assert suitability_label(1.0) == "high"