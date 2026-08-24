from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

from backend.schemas.building import (
    SolarPredictionRequest,
    SolarPredictionResponse,
)
from backend.services.ml_service import ml_service
from backend.services.solar_service import (
    calculate_solar_score,
    estimate_energy_potential,
    suitability_label,
)


router = APIRouter(
    prefix="/predict-solar",
    tags=["Solar Prediction"],
)


@router.post(
    "",
    response_model=SolarPredictionResponse,
)
def predict_solar(
    request: SolarPredictionRequest,
) -> SolarPredictionResponse:
    """
    Predict solar potential for a surface.

    If an ML model is connected, it is used for prediction.
    Otherwise, the heuristic solar score and energy estimation
    are returned as fallback.
    """

    features: dict[str, Any] = {
        "area_m2": request.area_m2,
        "azimuth_deg": request.azimuth_deg,
        "tilt_deg": request.tilt_deg,
        "surface_type": request.surface_type,
    }

    if request.latitude is not None:
        features["latitude"] = request.latitude

    if request.longitude is not None:
        features["longitude"] = request.longitude

    # Heuristic fallback
    score = calculate_solar_score(features)

    if request.surface_type == "ground":
        energy = {
            "usable_area_m2": 0.0,
            "estimated_capacity_kw": 0.0,
            "estimated_annual_energy_kwh": 0.0,
        }
    else:
        energy = estimate_energy_potential(features)

    # ML prediction (if available)
    prediction: dict[str, Any] | None = None
    ml_available = ml_service.available

    if ml_available:
        try:
            prediction = ml_service.predict(features)
        except (RuntimeError, ValueError) as exc:
            # Never expose internal model details to clients.
            logger.error("ML prediction failed: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="ML prediction failed.",
            ) from exc

    return SolarPredictionResponse(
        surface_id=request.surface_id,
        building_id=request.building_id,
        available=ml_available,
        prediction=prediction,
        fallback_score=score,
        fallback_suitability=suitability_label(score),
        fallback_energy=energy,
    )
