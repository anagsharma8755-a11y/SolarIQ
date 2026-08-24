from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Vertex(BaseModel):
    x: float
    y: float
    z: float


class SurfaceInput(BaseModel):
    surface_id: str | None = None

    vertices: list[
        list[float]
    ] = Field(
        min_length=3
    )


class BuildingInput(BaseModel):
    building_id: str = Field(
        min_length=1,
        max_length=128,
    )

    name: str | None = Field(
        default=None,
        max_length=256,
    )

    surfaces: list[
        SurfaceInput
    ] = Field(
        min_length=1
    )


class BuildingAnalysisRequest(BaseModel):
    building: BuildingInput


class CityAnalysisRequest(BaseModel):
    buildings: list[
        BuildingInput
    ] = Field(
        min_length=1
    )


class SurfaceNormal(BaseModel):
    x: float
    y: float
    z: float


class EnergyPotential(BaseModel):
    usable_area_m2: float = Field(ge=0.0)
    estimated_capacity_kw: float = Field(ge=0.0)
    estimated_annual_energy_kwh: float = Field(ge=0.0)


class AnalyzedSurface(BaseModel):
    surface_id: str
    building_id: str

    area_m2: float = Field(gt=0.0)

    normal: SurfaceNormal

    azimuth_deg: float = Field(ge=0.0, le=360.0)
    tilt_deg: float = Field(ge=0.0, le=90.0)

    surface_type: str

    vertices: list[
        list[float]
    ]

    solar_score: float = Field(ge=0.0, le=1.0)

    solar_suitability: str

    energy_potential: EnergyPotential

    ml_prediction: dict[str, Any] | None = None

    # --- geospatial metadata (optional, backward-compatible) ---
    centroid: list[float] | None = None
    bounding_box: dict[str, float] | None = None
    reversed_winding_corrected: bool = False
    crs: dict[str, Any] | None = None
    projected_area_m2: float | None = None


class BuildingAnalysisResponse(BaseModel):
    building_id: str
    name: str | None = None

    surface_count: int = Field(ge=0)

    total_surface_area_m2: float = Field(ge=0.0)
    usable_surface_area_m2: float = Field(ge=0.0)

    estimated_capacity_kw: float = Field(ge=0.0)
    estimated_annual_energy_kwh: float = Field(ge=0.0)

    surfaces: list[
        AnalyzedSurface
    ]


class CitySummary(BaseModel):
    building_count: int = Field(ge=0)
    surface_count: int = Field(ge=0)

    total_surface_area_m2: float = Field(ge=0.0)
    total_usable_surface_area_m2: float = Field(ge=0.0)

    total_estimated_capacity_kw: float = Field(ge=0.0)
    total_estimated_annual_energy_kwh: float = Field(ge=0.0)


class CityAnalysisResponse(BaseModel):
    summary: CitySummary

    buildings: list[
        BuildingAnalysisResponse
    ]


class OptimizationResult(BaseModel):
    rank: int = Field(ge=1)

    building_id: str
    surface_id: str

    area_m2: float = Field(gt=0.0)

    surface_type: str

    azimuth_deg: float = Field(ge=0.0, le=360.0)
    tilt_deg: float = Field(ge=0.0, le=90.0)

    solar_score: float = Field(ge=0.0, le=1.0)
    solar_suitability: str

    usable_area_m2: float = Field(ge=0.0)
    estimated_capacity_kw: float = Field(ge=0.0)
    estimated_annual_energy_kwh: float = Field(ge=0.0)

    composite_score: float = Field(
        ge=0.0, le=1.0,
        description="Weighted composite ranking score.",
    )

    recommendation: str = Field(
        default="",
        description="Human-readable explanation of ranking.",
    )


class OptimizationConstraints(BaseModel):
    """Optional filtering constraints for optimization."""

    min_solar_score: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Minimum solar score to include.",
    )
    min_usable_area_m2: float | None = Field(
        default=None, gt=0.0,
        description="Minimum usable area in square metres.",
    )
    max_surfaces: int | None = Field(
        default=None, gt=0,
        description="Maximum number of surfaces to return.",
    )
    max_total_capacity_kw: float | None = Field(
        default=None, gt=0.0,
        description="Maximum cumulative capacity in kW.",
    )
    surface_types: list[str] | None = Field(
        default=None,
        description="Restrict to these surface types.",
    )


class CityOptimizationSummary(BaseModel):
    """Aggregated city-level optimization metrics."""

    total_suitable_area_m2: float = Field(ge=0.0)
    total_potential_capacity_kw: float = Field(ge=0.0)
    total_annual_energy_kwh: float = Field(ge=0.0)
    top_buildings: list[str] = Field(
        default_factory=list,
        description="Building IDs ranked by total capacity.",
    )
    top_surfaces: list[str] = Field(
        default_factory=list,
        description="Surface IDs of the top-ranked surfaces.",
    )


class OptimizationResponse(BaseModel):
    total_candidates: int = Field(ge=0)
    filtered_candidates: int = Field(ge=0)
    scoring_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Transparent scoring weights used.",
    )
    city_summary: CityOptimizationSummary | None = None
    results: list[
        OptimizationResult
    ]


# ------------------------------------------------------------------
# ML Prediction schemas
# ------------------------------------------------------------------


class SolarPredictionRequest(BaseModel):
    """Input features for ML-based solar prediction."""

    surface_id: str | None = Field(
        default=None,
        max_length=128,
    )
    building_id: str | None = Field(
        default=None,
        max_length=128,
    )

    area_m2: float = Field(
        gt=0.0,
        description="Surface area in square metres.",
    )

    azimuth_deg: float = Field(
        ge=0.0,
        le=360.0,
        description="Surface azimuth in degrees.",
    )

    tilt_deg: float = Field(
        ge=0.0,
        le=90.0,
        description="Surface tilt in degrees.",
    )

    surface_type: str = Field(
        pattern=r"^(roof|facade|ground)$",
        description="Surface classification.",
    )

    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Optional site latitude.",
    )

    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Optional site longitude.",
    )


class SolarPredictionResponse(BaseModel):
    """Result returned by the ML prediction endpoint."""

    surface_id: str | None = None
    building_id: str | None = None

    available: bool = Field(
        description="Whether the ML model is connected.",
    )

    prediction: dict[str, Any] | None = Field(
        default=None,
        description="ML prediction output, or None if unavailable.",
    )

    fallback_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Heuristic solar score used when ML is unavailable."
        ),
    )

    fallback_suitability: str = Field(
        description=(
            "Suitability label derived from the heuristic score."
        ),
    )

    fallback_energy: dict[str, float] = Field(
        description="Baseline energy estimation.",
    )
