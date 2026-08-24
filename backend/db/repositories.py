"""Repository pattern for SolarIQ database access.

Each function accepts a ``Session`` and performs a single
unit of work.  The caller is responsible for transaction
management (commit / rollback).

Functions raise ``ValueError`` for not-found cases so that
API layers can translate them into appropriate HTTP errors.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.models import (
    AnalysisResultModel,
    BuildingModel,
    ModelMetadataModel,
    PipelineRunModel,
    SolarPredictionModel,
    SurfaceModel,
)


# ===================================================================
# Buildings
# ===================================================================


def create_building(
    session: Session,
    building_id: str,
    name: str | None = None,
) -> BuildingModel:
    """Create and persist a new building record.

    Raises:
        ValueError: If a building with *building_id* already exists.
    """
    existing = (
        session.query(BuildingModel)
        .filter(BuildingModel.building_id == building_id)
        .first()
    )
    if existing is not None:
        raise ValueError(
            f"Building {building_id!r} already exists."
        )

    building = BuildingModel(building_id=building_id, name=name)
    session.add(building)
    session.flush()
    return building


def get_building(
    session: Session,
    building_id: str,
) -> BuildingModel:
    """Retrieve a building by its external ID.

    Raises:
        ValueError: If the building is not found.
    """
    building = (
        session.query(BuildingModel)
        .filter(BuildingModel.building_id == building_id)
        .first()
    )
    if building is None:
        raise ValueError(
            f"Building {building_id!r} not found."
        )
    return building


def list_buildings(
    session: Session,
    offset: int = 0,
    limit: int = 100,
) -> list[BuildingModel]:
    """Return a paginated list of buildings."""
    return (
        session.query(BuildingModel)
        .order_by(desc(BuildingModel.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


def delete_building(
    session: Session,
    building_id: str,
) -> None:
    """Delete a building and all its child records.

    Raises:
        ValueError: If the building is not found.
    """
    building = get_building(session, building_id)
    session.delete(building)
    session.flush()


def count_buildings(session: Session) -> int:
    """Return the total number of buildings."""
    return session.query(BuildingModel).count()  # type: ignore[return-value]


# ===================================================================
# Surfaces
# ===================================================================


def create_surface(
    session: Session,
    surface_id: str,
    building_id: str,
    vertices: list[list[float]],
    area_m2: float,
    surface_type: str,
    azimuth_deg: float,
    tilt_deg: float,
    normal: dict[str, float],
    centroid: list[float] | None = None,
    bounding_box: dict[str, float] | None = None,
) -> SurfaceModel:
    """Create and persist a surface record.

    Raises:
        ValueError: If the parent building does not exist
                    or the surface_id already exists.
    """
    # Verify parent exists.
    get_building(session, building_id)

    existing = (
        session.query(SurfaceModel)
        .filter(SurfaceModel.surface_id == surface_id)
        .first()
    )
    if existing is not None:
        raise ValueError(
            f"Surface {surface_id!r} already exists."
        )

    surface = SurfaceModel(
        surface_id=surface_id,
        building_id=building_id,
        vertices={"coordinates": vertices},
        area_m2=area_m2,
        surface_type=surface_type,
        azimuth_deg=azimuth_deg,
        tilt_deg=tilt_deg,
        normal=normal,
        centroid=centroid,
        bounding_box=bounding_box,
    )
    session.add(surface)
    session.flush()
    return surface


def get_surface(
    session: Session,
    surface_id: str,
) -> SurfaceModel:
    """Retrieve a surface by ID.

    Raises:
        ValueError: If the surface is not found.
    """
    surface = (
        session.query(SurfaceModel)
        .filter(SurfaceModel.surface_id == surface_id)
        .first()
    )
    if surface is None:
        raise ValueError(
            f"Surface {surface_id!r} not found."
        )
    return surface


def list_surfaces_for_building(
    session: Session,
    building_id: str,
) -> list[SurfaceModel]:
    """Return all surfaces belonging to a building."""
    return (
        session.query(SurfaceModel)
        .filter(SurfaceModel.building_id == building_id)
        .order_by(SurfaceModel.surface_id)
        .all()
    )


# ===================================================================
# Analysis results
# ===================================================================


def save_analysis(
    session: Session,
    surface_id: str,
    building_id: str,
    solar_score: float,
    solar_suitability: str,
    usable_area_m2: float,
    estimated_capacity_kw: float,
    estimated_annual_energy_kwh: float,
    ml_prediction: dict[str, Any] | None = None,
    composite_score: float | None = None,
    recommendation: str | None = None,
) -> AnalysisResultModel:
    """Save (insert or update) an analysis result.

    If an analysis result already exists for *surface_id*,
    it is replaced.
    """
    existing = (
        session.query(AnalysisResultModel)
        .filter(AnalysisResultModel.surface_id == surface_id)
        .first()
    )
    if existing is not None:
        existing.solar_score = solar_score
        existing.solar_suitability = solar_suitability
        existing.usable_area_m2 = usable_area_m2
        existing.estimated_capacity_kw = estimated_capacity_kw
        existing.estimated_annual_energy_kwh = estimated_annual_energy_kwh
        existing.ml_prediction = ml_prediction
        existing.composite_score = composite_score
        existing.recommendation = recommendation
        session.flush()
        return existing

    result = AnalysisResultModel(
        surface_id=surface_id,
        building_id=building_id,
        solar_score=solar_score,
        solar_suitability=solar_suitability,
        usable_area_m2=usable_area_m2,
        estimated_capacity_kw=estimated_capacity_kw,
        estimated_annual_energy_kwh=estimated_annual_energy_kwh,
        ml_prediction=ml_prediction,
        composite_score=composite_score,
        recommendation=recommendation,
    )
    session.add(result)
    session.flush()
    return result


def get_analysis(
    session: Session,
    surface_id: str,
) -> AnalysisResultModel:
    """Retrieve an analysis result by surface ID.

    Raises:
        ValueError: If not found.
    """
    result = (
        session.query(AnalysisResultModel)
        .filter(AnalysisResultModel.surface_id == surface_id)
        .first()
    )
    if result is None:
        raise ValueError(
            f"Analysis result for surface {surface_id!r} not found."
        )
    return result


def list_analyses(
    session: Session,
    building_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[AnalysisResultModel]:
    """Return paginated analysis results, optionally filtered."""
    query = session.query(AnalysisResultModel)
    if building_id is not None:
        query = query.filter(
            AnalysisResultModel.building_id == building_id
        )
    return (
        query.order_by(desc(AnalysisResultModel.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


# ===================================================================
# Solar predictions
# ===================================================================


def save_prediction(
    session: Session,
    surface_id: str,
    building_id: str,
    available: bool,
    prediction: dict[str, Any] | None,
    fallback_score: float,
    fallback_suitability: str,
    fallback_energy: dict[str, float],
) -> SolarPredictionModel:
    """Persist a solar prediction record."""
    record = SolarPredictionModel(
        surface_id=surface_id,
        building_id=building_id,
        available=available,
        prediction=prediction,
        fallback_score=fallback_score,
        fallback_suitability=fallback_suitability,
        fallback_energy=fallback_energy,
    )
    session.add(record)
    session.flush()
    return record


def list_predictions(
    session: Session,
    surface_id: str | None = None,
    building_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[SolarPredictionModel]:
    """Return paginated predictions, optionally filtered."""
    query = session.query(SolarPredictionModel)
    if surface_id is not None:
        query = query.filter(
            SolarPredictionModel.surface_id == surface_id
        )
    if building_id is not None:
        query = query.filter(
            SolarPredictionModel.building_id == building_id
        )
    return (
        query.order_by(desc(SolarPredictionModel.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


# ===================================================================
# Pipeline run metadata
# ===================================================================


def create_pipeline_run(
    session: Session,
    pipeline_name: str,
    status: str = "running",
    metadata_json: dict[str, Any] | None = None,
) -> PipelineRunModel:
    """Record the start of a pipeline execution."""
    run = PipelineRunModel(
        pipeline_name=pipeline_name,
        status=status,
        metadata_json=metadata_json,
    )
    session.add(run)
    session.flush()
    return run


def update_pipeline_run(
    session: Session,
    run_id: int,
    status: str,
    records_processed: int = 0,
    error_message: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> PipelineRunModel:
    """Update an existing pipeline run record.

    Raises:
        ValueError: If the run is not found.
    """
    run = (
        session.query(PipelineRunModel)
        .filter(PipelineRunModel.id == run_id)
        .first()
    )
    if run is None:
        raise ValueError(f"Pipeline run {run_id} not found.")

    run.status = status
    run.records_processed = records_processed
    run.error_message = error_message
    run.finished_at = dt.datetime.utcnow()
    if metadata_json is not None:
        run.metadata_json = metadata_json

    session.flush()
    return run


def list_pipeline_runs(
    session: Session,
    pipeline_name: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[PipelineRunModel]:
    """Return paginated pipeline runs."""
    query = session.query(PipelineRunModel)
    if pipeline_name is not None:
        query = query.filter(
            PipelineRunModel.pipeline_name == pipeline_name
        )
    return (
        query.order_by(desc(PipelineRunModel.started_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


# ===================================================================
# Model metadata
# ===================================================================


def register_model(
    session: Session,
    model_name: str,
    version: str,
    model_type: str,
    model_path: str | None = None,
    metrics: dict[str, Any] | None = None,
    status: str = "registered",
) -> ModelMetadataModel:
    """Register a new ML model version."""
    record = ModelMetadataModel(
        model_name=model_name,
        version=version,
        model_type=model_type,
        model_path=model_path,
        metrics=metrics,
        status=status,
    )
    session.add(record)
    session.flush()
    return record


def get_model_metadata(
    session: Session,
    model_name: str,
    version: str | None = None,
) -> ModelMetadataModel | None:
    """Retrieve the latest (or specific) version of a model.

    Returns ``None`` if not found (does not raise).
    """
    query = (
        session.query(ModelMetadataModel)
        .filter(ModelMetadataModel.model_name == model_name)
    )
    if version is not None:
        query = query.filter(ModelMetadataModel.version == version)
    return query.order_by(desc(ModelMetadataModel.created_at)).first()


def list_models(
    session: Session,
    model_type: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[ModelMetadataModel]:
    """Return paginated model metadata records."""
    query = session.query(ModelMetadataModel)
    if model_type is not None:
        query = query.filter(
            ModelMetadataModel.model_type == model_type
        )
    return (
        query.order_by(desc(ModelMetadataModel.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
