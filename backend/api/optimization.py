"""Solar optimization API endpoint.

Ranks building surfaces by multi-factor solar suitability
using transparent weighted scoring.  Supports optional
constraints and city-level aggregation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.config import MAX_OPTIMIZATION_LIMIT
from backend.schemas.building import (
    CityAnalysisRequest,
    OptimizationConstraints,
    OptimizationResponse,
    OptimizationResult,
    CityOptimizationSummary,
)
from backend.services.optimization_service import (
    get_default_weights,
    optimize_surfaces,
)


router = APIRouter(
    prefix="/optimization-routes",
    tags=["Solar Optimization"],
)


@router.post(
    "",
    response_model=OptimizationResponse,
)
def optimize(
    request: CityAnalysisRequest,
    limit: int = Query(
        default=5,
        ge=1,
        le=MAX_OPTIMIZATION_LIMIT,
    ),
    min_solar_score: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum solar score filter.",
    ),
    min_usable_area: float | None = Query(
        default=None,
        gt=0.0,
        description="Minimum usable area (m\u00b2) filter.",
    ),
    max_surfaces: int | None = Query(
        default=None,
        gt=0,
        description="Maximum number of surfaces to return.",
    ),
    max_capacity: float | None = Query(
        default=None,
        gt=0.0,
        description="Maximum cumulative capacity (kW).",
    ),
) -> OptimizationResponse:
    """Rank building surfaces by solar suitability.

    The scoring uses a transparent weighted formula:

        composite = w1 x suitability
                  + w2 x energy
                  + w3 x capacity
                  + w4 x area
                  + w5 x orientation

    Ground surfaces are excluded.

    Optional query parameters allow filtering by minimum
    solar score, usable area, and maximum count/capacity.
    """

    # Build constraints dict from query params.
    constraints: dict[str, object] = {}

    if min_solar_score is not None:
        constraints["min_solar_score"] = min_solar_score

    if min_usable_area is not None:
        constraints["min_usable_area_m2"] = min_usable_area

    if max_surfaces is not None:
        constraints["max_surfaces"] = max_surfaces

    if max_capacity is not None:
        constraints["max_total_capacity_kw"] = max_capacity

    if not constraints:
        constraints = None

    # Convert request buildings to raw dicts.
    building_dicts = [
        b.model_dump() for b in request.buildings
    ]

    try:
        result = optimize_surfaces(
            buildings=building_dicts,
            limit=limit,
            constraints=constraints,
            include_city_summary=True,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Map results to Pydantic models.
    opt_results = [
        OptimizationResult(**r)
        for r in result["results"]
    ]

    city_summary = None
    if result.get("city_summary"):
        city_summary = CityOptimizationSummary(
            **result["city_summary"]
        )

    return OptimizationResponse(
        total_candidates=result["total_candidates"],
        filtered_candidates=result["filtered_candidates"],
        scoring_weights=result["scoring_weights"],
        city_summary=city_summary,
        results=opt_results,
    )
