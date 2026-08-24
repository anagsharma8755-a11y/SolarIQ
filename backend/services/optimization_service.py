"""Solar optimization engine for BIPV planning.

Provides a transparent weighted scoring system for ranking
building surfaces by solar suitability. Every ranking
decision is explainable and deterministic.

Scoring formula (public, not hidden):

    composite = w1 * suitability_score
              + w2 * energy_score
              + w3 * capacity_score
              + w4 * area_score
              + w5 * orientation_score

Each component is normalised to [0, 1] before weighting.
"""

from __future__ import annotations

from typing import Any

from backend.config import (
    ANNUAL_IRRADIANCE_KWH_M2,
    COVERAGE_FACTOR,
    OPT_WEIGHT_AREA,
    OPT_WEIGHT_CAPACITY,
    OPT_WEIGHT_ENERGY,
    OPT_WEIGHT_ORIENTATION,
    OPT_WEIGHT_SUITABILITY,
    PANEL_EFFICIENCY,
    PERFORMANCE_RATIO,
)
from backend.services.solar_service import (
    analyze_surface,
    calculate_installation_priority,
    calculate_solar_score,
    estimate_energy_potential,
    orientation_score,
    suitability_label,
    tilt_score,
)


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------


def get_default_weights() -> dict[str, float]:
    """Return the default scoring weights.

    The weights sum to 1.0 by construction.
    """
    total = (
        OPT_WEIGHT_SUITABILITY
        + OPT_WEIGHT_ENERGY
        + OPT_WEIGHT_CAPACITY
        + OPT_WEIGHT_AREA
        + OPT_WEIGHT_ORIENTATION
    )

    # Normalise so they sum to exactly 1.0.
    return {
        "suitability": round(OPT_WEIGHT_SUITABILITY / total, 4),
        "energy": round(OPT_WEIGHT_ENERGY / total, 4),
        "capacity": round(OPT_WEIGHT_CAPACITY / total, 4),
        "area": round(OPT_WEIGHT_AREA / total, 4),
        "orientation": round(OPT_WEIGHT_ORIENTATION / total, 4),
    }


# ---------------------------------------------------------------------------
# Score normalisation helpers
# ---------------------------------------------------------------------------


def _normalise(value: float, max_val: float) -> float:
    """Clamp value to [0, 1] by dividing by *max_val*."""
    if max_val <= 0:
        return 0.0
    return max(0.0, min(1.0, value / max_val))


def _compute_energy_score(
    annual_energy_kwh: float,
    max_energy_kwh: float,
) -> float:
    """Normalise annual energy to [0, 1]."""
    return _normalise(annual_energy_kwh, max_energy_kwh)


def _compute_capacity_score(
    capacity_kw: float,
    max_capacity_kw: float,
) -> float:
    """Normalise capacity to [0, 1]."""
    return _normalise(capacity_kw, max_capacity_kw)


def _compute_area_score(
    usable_area_m2: float,
    max_area_m2: float,
) -> float:
    """Normalise usable area to [0, 1]."""
    return _normalise(usable_area_m2, max_area_m2)


def _compute_orientation_score(
    azimuth_deg: float,
    surface_type: str,
) -> float:
    """Delegates to the solar service orientation_score."""
    return orientation_score(azimuth_deg, surface_type)


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


def compute_composite_score(
    surface: dict[str, Any],
    weights: dict[str, float],
    max_energy_kwh: float,
    max_capacity_kw: float,
    max_area_m2: float,
) -> float:
    """Compute a transparent composite score for one surface.

    Components (all in [0, 1]):
        suitability  -- from the solar suitability calculation
        energy       -- normalised annual energy
        capacity     -- normalised capacity
        area         -- normalised usable area
        orientation  -- orientation suitability

    Returns:
        Weighted composite score in [0, 1].
    """
    score = surface.get("solar_score", 0.0)
    energy = surface.get("energy_potential", {})
    annual = energy.get("estimated_annual_energy_kwh", 0.0)
    capacity = energy.get("estimated_capacity_kw", 0.0)
    usable = energy.get("usable_area_m2", 0.0)
    azimuth = surface.get("azimuth_deg", 0.0)
    stype = surface.get("surface_type", "facade")

    composite = (
        weights["suitability"] * score
        + weights["energy"] * _compute_energy_score(annual, max_energy_kwh)
        + weights["capacity"] * _compute_capacity_score(capacity, max_capacity_kw)
        + weights["area"] * _compute_area_score(usable, max_area_m2)
        + weights["orientation"] * _compute_orientation_score(azimuth, stype)
    )

    return round(max(0.0, min(1.0, composite)), 4)


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


def generate_recommendation(
    surface: dict[str, Any],
    composite_score: float,
    rank: int,
) -> str:
    """Generate a deterministic explanation for the ranking.

    The explanation highlights the key factors that contributed
    to the surface's position in the ranking and provides
    actionable installation recommendations.
    """
    parts: list[str] = []

    score = surface.get("solar_score", 0.0)
    tilt = surface.get("tilt_deg", 0.0)
    azimuth = surface.get("azimuth_deg", 0.0)
    stype = surface.get("surface_type", "facade")
    energy = surface.get("energy_potential", {})
    usable = energy.get("usable_area_m2", 0.0)
    annual = energy.get("estimated_annual_energy_kwh", 0.0)
    capacity = energy.get("estimated_capacity_kw", 0.0)

    # Rank-specific note.
    if rank == 1:
        parts.insert(0, "Top-ranked surface.")
    elif rank <= 3:
        parts.insert(0, f"Ranked #{rank}.")

    # Suitability assessment.
    if score >= 0.75:
        parts.append("high solar suitability")
    elif score >= 0.50:
        parts.append("moderate solar suitability")
    else:
        parts.append("low solar suitability")

    # Surface type and installation.
    if stype == "roof":
        parts.append("flat roof with flexible panel mounting")
        parts.append("panels can be installed at optimal 20-degree tilt")
    else:
        # Facade-specific assessment
        diff = abs(((azimuth - 180.0 + 180.0) % 360.0) - 180.0)
        if diff <= 30.0:
            parts.append("south-facing facade with excellent solar exposure")
        elif diff <= 60.0:
            parts.append("southeast/southwest facade with good solar exposure")
        elif diff <= 90.0:
            parts.append("east/west-facing facade with moderate solar exposure")
        else:
            parts.append("north-facing facade with limited solar exposure")

        # Tilt assessment for facades
        tilt_dev = abs(tilt - 90.0)
        if tilt_dev <= 5.0:
            parts.append("vertical installation (standard facade mounting)")
        else:
            parts.append(f"tilted facade at {tilt:.0f} degrees")

    # Area and capacity assessment.
    if usable >= 200.0:
        parts.append(f"large installation area ({usable:.0f} m\u00b2)")
    elif usable >= 50.0:
        parts.append(f"moderate installation area ({usable:.0f} m\u00b2)")
    else:
        parts.append(f"small installation area ({usable:.0f} m\u00b2)")

    # Energy and capacity assessment.
    if annual >= 50000.0:
        parts.append(f"high energy yield ({annual:,.0f} kWh/yr)")
    elif annual >= 20000.0:
        parts.append(f"moderate energy yield ({annual:,.0f} kWh/yr)")
    elif annual >= 5000.0:
        parts.append(f" modest energy yield ({annual:,.0f} kWh/yr)")

    if capacity >= 50.0:
        parts.append(f"significant capacity ({capacity:.1f} kW)")
    elif capacity >= 10.0:
        parts.append(f"moderate capacity ({capacity:.1f} kW)")

    # Installation recommendation
    if stype == "roof" and usable >= 100.0:
        parts.append("recommended for priority installation")
    elif stype == "facade" and score >= 0.6 and usable >= 100.0:
        parts.append("good candidate for facade-integrated PV")

    return "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Constraint filtering
# ---------------------------------------------------------------------------


def apply_constraints(
    candidates: list[dict[str, Any]],
    constraints: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Filter candidates according to optional constraints.

    Supported constraints:
        min_solar_score:    minimum solar_score to include
        min_usable_area_m2: minimum usable_area_m2 to include
        surface_types:      whitelist of surface types

    Capacity limits (max_total_capacity_kw, max_surfaces) are
    applied *after* sorting, not here.
    """
    if not constraints:
        return candidates

    result = list(candidates)

    min_score = constraints.get("min_solar_score")
    if min_score is not None:
        result = [
            c for c in result
            if c.get("solar_score", 0.0) >= min_score
        ]

    min_area = constraints.get("min_usable_area_m2")
    if min_area is not None:
        result = [
            c for c in result
            if c.get("energy_potential", {}).get(
                "usable_area_m2", 0.0
            ) >= min_area
        ]

    surface_types = constraints.get("surface_types")
    if surface_types is not None and surface_types:
        types_set = set(surface_types)
        result = [
            c for c in result
            if c.get("surface_type") in types_set
        ]

    return result


def apply_limits(
    ranked: list[dict[str, Any]],
    max_surfaces: int | None = None,
    max_total_capacity_kw: float | None = None,
) -> list[dict[str, Any]]:
    """Apply post-sort limits on count and cumulative capacity."""
    selected: list[dict[str, Any]] = []
    cumulative_kw = 0.0

    for surface in ranked:
        cap = surface.get(
            "energy_potential", {}
        ).get("estimated_capacity_kw", 0.0)

        if max_surfaces is not None and len(selected) >= max_surfaces:
            break

        if (
            max_total_capacity_kw is not None
            and cumulative_kw + cap > max_total_capacity_kw
        ):
            # Try to include this surface if it fits.
            if cumulative_kw >= max_total_capacity_kw:
                break
            # Include partially? No -- skip if it exceeds.
            break

        selected.append(surface)
        cumulative_kw += cap

    return selected


# ---------------------------------------------------------------------------
# City-level aggregation
# ---------------------------------------------------------------------------


def aggregate_city_results(
    ranked: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute city-level aggregation metrics.

    Returns:
        total_suitable_area_m2
        total_potential_capacity_kw
        total_annual_energy_kwh
        top_buildings: building IDs sorted by total capacity
        top_surfaces: surface IDs in rank order
    """
    total_area = 0.0
    total_capacity = 0.0
    total_energy = 0.0

    building_capacity: dict[str, float] = {}
    surface_ids: list[str] = []

    for s in ranked:
        energy = s.get("energy_potential", {})
        usable = energy.get("usable_area_m2", 0.0)
        cap = energy.get("estimated_capacity_kw", 0.0)
        annual = energy.get("estimated_annual_energy_kwh", 0.0)
        bid = s.get("building_id", "")
        sid = s.get("surface_id", "")

        total_area += usable
        total_capacity += cap
        total_energy += annual

        building_capacity[bid] = building_capacity.get(bid, 0.0) + cap
        if sid:
            surface_ids.append(sid)

    # Sort buildings by total capacity descending.
    top_buildings = [
        bid for bid, _ in sorted(
            building_capacity.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
    ]

    return {
        "total_suitable_area_m2": round(total_area, 4),
        "total_potential_capacity_kw": round(total_capacity, 4),
        "total_annual_energy_kwh": round(total_energy, 4),
        "top_buildings": top_buildings,
        "top_surfaces": surface_ids[:20],  # Top 20 surface IDs.
    }


# ---------------------------------------------------------------------------
# Main optimisation entry point
# ---------------------------------------------------------------------------


def optimize_surfaces(
    buildings: list[dict[str, Any]],
    limit: int = 5,
    constraints: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
    include_city_summary: bool = True,
) -> dict[str, Any]:
    """Run the full solar optimisation pipeline.

    Steps:
        1. Extract and analyse surfaces from all buildings.
        2. Filter out ground surfaces and apply constraints.
        3. Compute installation priority scores.
        4. Rank and select top surfaces.
        5. Generate human-readable recommendations.
        6. Aggregate city-level metrics.

    The ranking uses installation_priority which combines:
        - Solar suitability score
        - Expected annual energy generation
        - Usable area

    This ensures surfaces are ranked by actual solar opportunity,
    not by hardcoded surface type rules.

    Args:
        buildings: List of building dicts with surfaces.
        limit: Maximum number of results to return.
        constraints: Optional filtering constraints.
        weights: Optional custom scoring weights.
        include_city_summary: Whether to include city aggregation.

    Returns:
        Dict with total_candidates, filtered_candidates,
        scoring_weights, city_summary, and results.
    """
    if weights is None:
        weights = get_default_weights()

    # 1. Extract and analyse all surfaces.
    all_surfaces: list[dict[str, Any]] = []

    for building in buildings:
        from backend.geometry.surfaces import extract_surfaces

        raw_surfaces = extract_surfaces(building)
        for surface in raw_surfaces:
            analyzed = analyze_surface(surface)
            if analyzed.get("surface_type") == "ground":
                continue
            all_surfaces.append(analyzed)

    total_candidates = len(all_surfaces)

    # 2. Apply constraints.
    filtered = apply_constraints(all_surfaces, constraints)
    filtered_candidates = len(filtered)

    if not filtered:
        return {
            "total_candidates": total_candidates,
            "filtered_candidates": 0,
            "scoring_weights": weights,
            "city_summary": aggregate_city_results([])
            if include_city_summary
            else None,
            "results": [],
        }

    # 3. Compute normalisation bounds from the filtered set.
    max_energy = max(
        (
            c.get("energy_potential", {}).get(
                "estimated_annual_energy_kwh", 0.0
            )
            for c in filtered
        ),
        default=1.0,
    )
    max_capacity = max(
        (
            c.get("energy_potential", {}).get(
                "estimated_capacity_kw", 0.0
            )
            for c in filtered
        ),
        default=1.0,
    )
    max_area = max(
        (
            c.get("energy_potential", {}).get(
                "usable_area_m2", 0.0
            )
            for c in filtered
        ),
        default=1.0,
    )

    # Ensure minimum bounds so division is safe.
    max_energy = max(max_energy, 0.001)
    max_capacity = max(max_capacity, 0.001)
    max_area = max(max_area, 0.001)

    # 4. Score each surface using installation_priority.
    #    Use relative normalization based on dataset bounds.
    for surface in filtered:
        # Recalculate priority with relative normalization
        from backend.services.solar_service import calculate_installation_priority
        priority = calculate_installation_priority(
            surface,
            max_energy_in_dataset=max_energy,
            max_area_in_dataset=max_area,
        )

        # Also compute composite score for API response
        composite = compute_composite_score(
            surface, weights, max_energy, max_capacity, max_area
        )
        surface["_composite_score"] = composite

        # Priority score combines suitability + energy + area
        # This is what we use for ranking
        surface["_priority_score"] = priority

    # 5. Sort by priority score descending, then energy, then area.
    filtered.sort(
        key=lambda s: (
            s["_priority_score"],
            s.get("energy_potential", {}).get(
                "estimated_annual_energy_kwh", 0.0
            ),
            s.get("area_m2", 0.0),
        ),
        reverse=True,
    )

    # 6. Apply limits.
    max_surfaces = constraints.get("max_surfaces") if constraints else None
    max_cap = (
        constraints.get("max_total_capacity_kw")
        if constraints
        else None
    )
    selected = apply_limits(filtered, max_surfaces, max_cap)

    # Further trim to the requested limit.
    selected = selected[:limit]

    # 7. Build result dicts with recommendations.
    results: list[dict[str, Any]] = []
    for rank, surface in enumerate(selected, start=1):
        energy = surface.get("energy_potential", {})
        composite = surface["_composite_score"]

        recommendation = generate_recommendation(
            surface, composite, rank
        )

        results.append({
            "rank": rank,
            "building_id": surface.get("building_id", ""),
            "surface_id": surface.get("surface_id", ""),
            "area_m2": surface.get("area_m2", 0.0),
            "surface_type": surface.get("surface_type", ""),
            "azimuth_deg": surface.get("azimuth_deg", 0.0),
            "tilt_deg": surface.get("tilt_deg", 0.0),
            "solar_score": surface.get("solar_score", 0.0),
            "solar_suitability": surface.get(
                "solar_suitability", "low"
            ),
            "usable_area_m2": energy.get("usable_area_m2", 0.0),
            "estimated_capacity_kw": energy.get(
                "estimated_capacity_kw", 0.0
            ),
            "estimated_annual_energy_kwh": energy.get(
                "estimated_annual_energy_kwh", 0.0
            ),
            "composite_score": composite,
            "recommendation": recommendation,
        })

    # 8. City-level aggregation.
    city_summary = None
    if include_city_summary:
        city_summary = aggregate_city_results(selected)

    return {
        "total_candidates": total_candidates,
        "filtered_candidates": filtered_candidates,
        "scoring_weights": weights,
        "city_summary": city_summary,
        "results": results,
    }
