from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas.building import (
    AnalyzedSurface,
    BuildingAnalysisRequest,
    BuildingAnalysisResponse,
)
from backend.services.analysis_service import (
    analyze_building_surfaces,
)


router = APIRouter(
    prefix="/analyze-building",
    tags=["Building Analysis"],
)


@router.post(
    "",
    response_model=BuildingAnalysisResponse,
)
def analyze_building(
    request: BuildingAnalysisRequest,
) -> BuildingAnalysisResponse:
    """
    Analyze one building.

    Performs:

    - Surface extraction
    - Area calculation
    - Normal calculation
    - Azimuth calculation
    - Tilt calculation
    - Roof/facade/ground classification
    - Solar suitability scoring
    - Baseline energy estimation
    - Optional ML prediction
    """

    building = request.building.model_dump()

    try:
        analyzed_surfaces, totals = analyze_building_surfaces(
            building
        )

    except (ValueError, RuntimeError) as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return BuildingAnalysisResponse(
        building_id=building["building_id"],
        name=building.get("name"),
        surface_count=len(analyzed_surfaces),
        total_surface_area_m2=totals["total_surface_area_m2"],
        usable_surface_area_m2=totals["total_usable_area_m2"],
        estimated_capacity_kw=totals["total_capacity_kw"],
        estimated_annual_energy_kwh=totals["total_energy_kwh"],
        surfaces=[
            AnalyzedSurface(**surface)
            for surface in analyzed_surfaces
        ],
    )
