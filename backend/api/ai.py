"""AI Explanation and Recommendation API endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException

from backend.schemas.area import AIExplanationRequest, AIExplanationResponse
from backend.services.ai_service import ai_service
from backend.services.area_analysis_service import area_analysis_service

router = APIRouter(
    tags=["AI Explanation Layer"],
)


@router.post(
    "/ai/explain",
    response_model=AIExplanationResponse,
    summary="Ask AI to interpret and explain SolarIQ analysis results",
)
def explain_analysis(
    request: AIExplanationRequest,
) -> dict[str, Any]:
    """Provide AI-interpreted strategic recommendations strictly grounded in calculated data."""
    analysis_data = request.analysis_data

    # If analysis_id provided, look up stored analysis
    if request.analysis_id and not analysis_data:
        analysis_data = area_analysis_service.get_analysis_by_id(request.analysis_id)
        if not analysis_data:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis ID {request.analysis_id} not found.",
            )

    if not analysis_data:
        # Provide sample context if called directly without an active analysis
        sample_loc = {"latitude": 19.0596, "longitude": 72.8295}
        analysis_data = area_analysis_service.analyze_area(
            latitude=sample_loc["latitude"],
            longitude=sample_loc["longitude"],
            radius_m=400.0,
            location_name="Bandra West, Mumbai",
        )

    return ai_service.explain(
        analysis_data=analysis_data,
        user_prompt=request.query,
        target_capacity_kw=request.target_capacity_kw,
    )
