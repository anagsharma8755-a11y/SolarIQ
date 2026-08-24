"""Shared building analysis logic.

The building-analysis and city-analysis API endpoints were
duplicating the same extract → analyze → ML-predict loop.
This module extracts that into a single reusable function.
"""

from __future__ import annotations

from typing import Any

from backend.geometry.surfaces import extract_surfaces
from backend.services.ml_service import ml_service
from backend.services.solar_service import analyze_surface


def analyze_building_surfaces(
    building: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Extract, score and estimate energy for every surface.

    Returns:
        A tuple of (analyzed_surfaces, totals) where *totals*
        contains aggregated usable_area, capacity and energy
        values.

    Raises:
        ValueError: If the building geometry is malformed.
        RuntimeError: On unexpected processing errors.
    """

    surfaces = extract_surfaces(building)

    analyzed_surfaces: list[dict[str, Any]] = []

    for surface in surfaces:
        analyzed = analyze_surface(surface)

        ml_prediction = ml_service.predict_if_available(analyzed)
        analyzed["ml_prediction"] = ml_prediction

        analyzed_surfaces.append(analyzed)

    total_surface_area = 0.0
    total_usable_area = 0.0
    total_capacity = 0.0
    total_energy = 0.0

    for surface in analyzed_surfaces:
        total_surface_area += surface["area_m2"]

        if surface["surface_type"] != "ground":
            energy = surface["energy_potential"]
            total_usable_area += energy["usable_area_m2"]
            total_capacity += energy["estimated_capacity_kw"]
            total_energy += energy["estimated_annual_energy_kwh"]

    totals = {
        "total_surface_area_m2": round(total_surface_area, 4),
        "total_usable_area_m2": round(total_usable_area, 4),
        "total_capacity_kw": round(total_capacity, 4),
        "total_energy_kwh": round(total_energy, 4),
    }

    return analyzed_surfaces, totals
