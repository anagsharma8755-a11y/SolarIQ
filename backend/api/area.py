"""Real-world urban area analysis and optimization endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Path, Query

from backend.schemas.area import (
    AreaAnalysisRequest,
    AreaAnalysisResponse,
    AreaOptimizationRequest,
    AreaOptimizationResponse,
)
from backend.services.area_analysis_service import area_analysis_service
from backend.services.area_optimization_service import area_optimization_service

router = APIRouter(
    tags=["Real-World Area Analysis"],
)


@router.post(
    "/area/analyze",
    response_model=AreaAnalysisResponse,
    summary="Analyze real-world area using OpenStreetMap building data and weather",
)
def analyze_area(
    request: AreaAnalysisRequest,
) -> dict[str, Any]:
    """Execute complete real-world city analysis for given lat/lon and radius."""
    try:
        result = area_analysis_service.analyze_area(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_m=request.radius_m,
            location_name=request.location_name,
            max_buildings=request.max_buildings,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze area: {exc}",
        ) from exc


@router.post(
    "/location/analyze",
    response_model=AreaAnalysisResponse,
    summary="Alias for /area/analyze",
)
def analyze_location(
    request: AreaAnalysisRequest,
) -> dict[str, Any]:
    """Convenience alias for area analysis endpoint."""
    return analyze_area(request)


@router.get(
    "/area/{analysis_id}",
    response_model=AreaAnalysisResponse,
    summary="Retrieve previously computed area analysis by ID",
)
def get_area_analysis(
    analysis_id: str = Path(..., min_length=1, max_length=128),
) -> dict[str, Any]:
    """Retrieve cached/stored area analysis."""
    result = area_analysis_service.get_analysis_by_id(analysis_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Area analysis {analysis_id} not found.",
        )
    return result


@router.get(
    "/area/{analysis_id}/map",
    summary="Get GeoJSON feature collection for map visualization",
)
def get_area_map_geojson(
    analysis_id: str = Path(..., min_length=1, max_length=128),
) -> dict[str, Any]:
    """Get GeoJSON feature collection with solar scores and suitability colors."""
    result = area_analysis_service.get_analysis_by_id(analysis_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Area analysis {analysis_id} not found.",
        )
    return result.get("geojson", {"type": "FeatureCollection", "features": []})


@router.post(
    "/area/optimize",
    response_model=AreaOptimizationResponse,
    summary="Run capacity-constrained deployment optimization across area surfaces",
)
def optimize_area_deployment(
    request: AreaOptimizationRequest,
) -> dict[str, Any]:
    """Calculate optimal surface selection subject to capacity ceiling."""
    if not request.analysis_id:
        raise HTTPException(
            status_code=400,
            detail="analysis_id is required to optimize area deployment.",
        )

    analysis = area_analysis_service.get_analysis_by_id(request.analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Area analysis {request.analysis_id} not found.",
        )

    ranked_surfaces = analysis.get("ranked_surfaces", [])

    return area_optimization_service.optimize_deployment(
        ranked_surfaces=ranked_surfaces,
        max_capacity_kw=request.max_capacity_kw,
        min_solar_score=request.min_solar_score,
        allowed_surface_types=request.allowed_surface_types,
        target_metric=request.target_metric,
    )
