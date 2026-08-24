from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config import MAX_BUILDINGS_PER_REQUEST
from backend.schemas.building import (
    AnalyzedSurface,
    BuildingAnalysisResponse,
    CityAnalysisRequest,
    CityAnalysisResponse,
    CitySummary,
)
from backend.services.analysis_service import (
    analyze_building_surfaces,
)


router = APIRouter(
    prefix="/city-analysis",
    tags=["City Analysis"],
)


@router.post(
    "",
    response_model=CityAnalysisResponse,
)
def analyze_city(
    request: CityAnalysisRequest,
) -> CityAnalysisResponse:

    if len(request.buildings) > MAX_BUILDINGS_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Request contains {len(request.buildings)} "
                f"buildings, exceeding the limit of "
                f"{MAX_BUILDINGS_PER_REQUEST}."
            ),
        )

    analyzed_buildings = []

    total_surface_area = 0.0
    total_usable_area = 0.0
    total_capacity = 0.0
    total_energy = 0.0

    total_surfaces = 0

    for building_input in request.buildings:

        building = building_input.model_dump()

        try:
            analyzed_surfaces, totals = (
                analyze_building_surfaces(building)
            )

        except (ValueError, RuntimeError) as exc:

            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        response_building = BuildingAnalysisResponse(
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

        analyzed_buildings.append(response_building)

        total_surface_area += totals["total_surface_area_m2"]
        total_usable_area += totals["total_usable_area_m2"]
        total_capacity += totals["total_capacity_kw"]
        total_energy += totals["total_energy_kwh"]
        total_surfaces += len(analyzed_surfaces)

    summary = CitySummary(
        building_count=len(analyzed_buildings),
        surface_count=total_surfaces,
        total_surface_area_m2=round(total_surface_area, 4),
        total_usable_surface_area_m2=round(total_usable_area, 4),
        total_estimated_capacity_kw=round(total_capacity, 4),
        total_estimated_annual_energy_kwh=round(total_energy, 4),
    )

    return CityAnalysisResponse(
        summary=summary,
        buildings=analyzed_buildings,
    )
