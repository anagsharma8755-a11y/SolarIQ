"""SQLAlchemy ORM models for SolarIQ persistence.

Tables:
    buildings           – building metadata and geometry summary
    surfaces            – individual surface geometry and type
    analysis_results    – per-surface solar analysis output
    solar_predictions   – ML or heuristic predictions
    pipeline_runs       – data pipeline execution metadata
    model_metadata      – ML model registry

Geometry is stored as compact JSON blobs (vertices) rather
than individual coordinate columns, keeping the schema clean
while preserving full reconstruction capability.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.db.database import Base


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


class BuildingModel(Base):
    """A single building record."""

    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    building_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
    )
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    # Relationships
    surfaces: Mapped[list["SurfaceModel"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BuildingModel building_id={self.building_id!r}>"


# ---------------------------------------------------------------------------
# Surface
# ---------------------------------------------------------------------------


class SurfaceModel(Base):
    """A single surface belonging to a building."""

    __tablename__ = "surfaces"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    surface_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
    )
    building_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("buildings.building_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Geometry
    vertices: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False,
        comment="List of [x, y, z] vertex coordinates.",
    )
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    surface_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="roof | facade | ground",
    )

    # Orientation
    azimuth_deg: Mapped[float] = mapped_column(Float, nullable=False)
    tilt_deg: Mapped[float] = mapped_column(Float, nullable=False)

    # Normal vector (stored as JSON for simplicity)
    normal: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False,
        comment="Unit normal {x, y, z}.",
    )

    # Optional geospatial metadata
    centroid: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    bounding_box: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    # Relationships
    building: Mapped["BuildingModel"] = relationship(
        back_populates="surfaces",
    )
    analysis: Mapped["AnalysisResultModel | None"] = relationship(
        back_populates="surface",
        uselist=False,
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["SolarPredictionModel"]] = relationship(
        back_populates="surface",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SurfaceModel surface_id={self.surface_id!r} "
            f"type={self.surface_type!r}>"
        )


# ---------------------------------------------------------------------------
# Analysis result
# ---------------------------------------------------------------------------


class AnalysisResultModel(Base):
    """Solar analysis result for a surface."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    surface_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("surfaces.surface_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    building_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )

    # Solar scores
    solar_score: Mapped[float] = mapped_column(Float, nullable=False)
    solar_suitability: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="high | medium | low",
    )

    # Energy potential
    usable_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_capacity_kw: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    estimated_annual_energy_kwh: Mapped[float] = mapped_column(
        Float, nullable=False,
    )

    # ML prediction (nullable)
    ml_prediction: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # Composite score (from optimization, nullable)
    composite_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    # Relationships
    surface: Mapped["SurfaceModel"] = relationship(
        back_populates="analysis",
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisResultModel surface_id={self.surface_id!r} "
            f"score={self.solar_score}>"
        )


# ---------------------------------------------------------------------------
# Solar prediction
# ---------------------------------------------------------------------------


class SolarPredictionModel(Base):
    """ML or heuristic solar prediction for a surface."""

    __tablename__ = "solar_predictions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    surface_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("surfaces.surface_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[str] = mapped_column(
        String(128), nullable=False,
    )

    available: Mapped[bool] = mapped_column(nullable=False)
    prediction: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    fallback_score: Mapped[float] = mapped_column(Float, nullable=False)
    fallback_suitability: Mapped[str] = mapped_column(
        String(16), nullable=False,
    )
    fallback_energy: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    # Relationships
    surface: Mapped["SurfaceModel"] = relationship(
        back_populates="predictions",
    )

    def __repr__(self) -> str:
        return (
            f"<SolarPredictionModel surface_id={self.surface_id!r} "
            f"available={self.available}>"
        )


# ---------------------------------------------------------------------------
# Pipeline run metadata
# ---------------------------------------------------------------------------


class PipelineRunModel(Base):
    """Record of a data pipeline execution."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    pipeline_name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="running | success | failed",
    )
    records_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime, nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineRunModel name={self.pipeline_name!r} "
            f"status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Model metadata (ML model registry)
# ---------------------------------------------------------------------------


class ModelMetadataModel(Base):
    """Registry of trained ML models."""

    __tablename__ = "model_metadata"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )
    version: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    model_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. solar_prediction, irradiance_forecast",
    )
    model_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
    )
    metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
        comment="Training/evaluation metrics.",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="registered",
        comment="registered | active | archived",
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ModelMetadataModel name={self.model_name!r} "
            f"version={self.version!r}>"
        )
