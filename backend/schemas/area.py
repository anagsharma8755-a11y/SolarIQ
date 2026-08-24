"""Pydantic schemas for real-world city/area analysis, geocoding, and AI explanations."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class LocationSearchResult(BaseModel):
    location_name: str
    display_name: str
    latitude: float
    longitude: float
    bounding_box: list[float] = Field(default_factory=list)
    category: str = "location"
    importance: float = 0.5
    is_demo: bool = False


class AreaAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Center latitude (WGS84)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Center longitude (WGS84)")
    radius_m: float = Field(default=400.0, ge=50.0, le=5000.0, description="Analysis radius in meters")
    location_name: str | None = Field(default=None, max_length=256, description="Optional location name")
    max_buildings: int = Field(default=50, ge=1, le=200, description="Maximum buildings to analyze")


class AreaSummary(BaseModel):
    building_count: int = Field(ge=0)
    surface_count: int = Field(ge=0)
    total_surface_area_m2: float = Field(ge=0.0)
    total_usable_surface_area_m2: float = Field(ge=0.0)
    total_estimated_capacity_kw: float = Field(ge=0.0)
    total_estimated_annual_energy_kwh: float = Field(ge=0.0)
    high_potential_count: int = Field(ge=0)
    medium_potential_count: int = Field(ge=0)
    low_potential_count: int = Field(ge=0)
    average_solar_score: float = Field(ge=0.0, le=1.0)
    top_performing_building: str | None = None
    top_building_name: str | None = None
    capacity_density_kw_per_m2: float = Field(ge=0.0)


class RankedSurfaceResult(BaseModel):
    rank: int = Field(ge=1)
    building_id: str
    building_name: str | None = None
    surface_id: str
    surface_type: str
    area_m2: float = Field(gt=0.0)
    azimuth_deg: float = Field(ge=0.0, le=360.0)
    tilt_deg: float = Field(ge=0.0, le=90.0)
    solar_score: float = Field(ge=0.0, le=1.0)
    solar_suitability: str
    usable_area_m2: float = Field(ge=0.0)
    estimated_capacity_kw: float = Field(ge=0.0)
    estimated_annual_energy_kwh: float = Field(ge=0.0)
    composite_score: float = Field(ge=0.0, le=1.0)
    recommendation: str


class AreaAnalysisResponse(BaseModel):
    analysis_id: str
    location_name: str
    latitude: float
    longitude: float
    radius_m: float
    data_provenance: dict[str, Any]
    summary: AreaSummary
    buildings: list[dict[str, Any]]
    ranked_surfaces: list[RankedSurfaceResult]
    geojson: dict[str, Any]


class AreaOptimizationRequest(BaseModel):
    analysis_id: str | None = None
    max_capacity_kw: float | None = Field(default=500.0, gt=0.0, description="Target capacity in kW")
    min_solar_score: float = Field(default=0.40, ge=0.0, le=1.0)
    allowed_surface_types: list[str] | None = None
    target_metric: str = "max_energy"


class DeploymentPhase(BaseModel):
    phase: int
    name: str
    surface_count: int
    capacity_kw: float
    annual_energy_kwh: float
    description: str


class AreaOptimizationResponse(BaseModel):
    target_capacity_kw: float | None = None
    selected_capacity_kw: float
    capacity_utilization_pct: float
    selected_annual_energy_kwh: float
    selected_usable_area_m2: float
    annual_co2_offset_tonnes: float
    selected_surfaces_count: int
    unselected_surfaces_count: int
    phases: list[DeploymentPhase]
    selected_surfaces: list[dict[str, Any]]


class AIExplanationRequest(BaseModel):
    analysis_id: str | None = None
    query: str = Field(..., min_length=1, max_length=1000)
    target_capacity_kw: float | None = None
    analysis_data: dict[str, Any] | None = None


class AIInterpretation(BaseModel):
    summary: str
    recommendations: list[str]
    avoidance_guidelines: str
    disclaimer: str


class AIExplanationResponse(BaseModel):
    query: str
    headline: str
    calculated_results: list[str]
    ai_interpretation: AIInterpretation
    optimization_context: dict[str, Any] | None = None
