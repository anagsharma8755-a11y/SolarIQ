"""Tests for the SolarIQ persistence layer.

All tests use a temporary in-memory SQLite database to avoid
dependency on any user's local database.
"""

from __future__ import annotations

import datetime as dt
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from backend.db import Base, get_db_session, get_engine, init_db, reset_engine
from backend.db.repositories import (
    count_buildings,
    create_building,
    create_pipeline_run,
    create_surface,
    delete_building,
    get_analysis,
    get_building,
    get_model_metadata,
    get_surface,
    list_analyses,
    list_buildings,
    list_models,
    list_pipeline_runs,
    list_predictions,
    list_surfaces_for_building,
    register_model,
    save_analysis,
    save_prediction,
    update_pipeline_run,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _setup_db() -> Generator[None, None, None]:
    """Create a fresh in-memory database for each test."""
    reset_engine()
    init_db(url="sqlite://")
    yield
    reset_engine()


def _session() -> Session:
    """Return a fresh session from the current engine."""
    factory = get_session_factory()
    return factory()


# ---------------------------------------------------------------------------
# Building repository tests
# ---------------------------------------------------------------------------


class TestBuildingRepository:
    def test_create_and_get_building(self):
        with get_db_session() as s:
            b = create_building(s, "B001", name="Main Hall")
            assert b.building_id == "B001"
            assert b.name == "Main Hall"
            assert b.id is not None

        with get_db_session() as s:
            fetched = get_building(s, "B001")
            assert fetched.building_id == "B001"
            assert fetched.name == "Main Hall"

    def test_create_duplicate_raises(self):
        with get_db_session() as s:
            create_building(s, "B001")
        with get_db_session() as s:
            with pytest.raises(ValueError, match="already exists"):
                create_building(s, "B001")

    def test_get_nonexistent_raises(self):
        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                get_building(s, "MISSING")

    def test_list_buildings(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_building(s, "B002")
            create_building(s, "B003")

        with get_db_session() as s:
            all_b = list_buildings(s)
            assert len(all_b) == 3

    def test_list_buildings_pagination(self):
        with get_db_session() as s:
            for i in range(10):
                create_building(s, f"B{i:03d}")

        with get_db_session() as s:
            page1 = list_buildings(s, offset=0, limit=3)
            assert len(page1) == 3
            page2 = list_buildings(s, offset=3, limit=3)
            assert len(page2) == 3
            page_end = list_buildings(s, offset=9, limit=3)
            assert len(page_end) == 1

    def test_delete_building(self):
        with get_db_session() as s:
            create_building(s, "B001")

        with get_db_session() as s:
            delete_building(s, "B001")

        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                get_building(s, "B001")

    def test_delete_nonexistent_raises(self):
        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                delete_building(s, "MISSING")

    def test_count_buildings(self):
        with get_db_session() as s:
            assert count_buildings(s) == 0
            create_building(s, "B001")
            assert count_buildings(s) == 1
            create_building(s, "B002")
            assert count_buildings(s) == 2

    def test_building_timestamps(self):
        with get_db_session() as s:
            b = create_building(s, "B001")
            assert isinstance(b.created_at, dt.datetime)
            assert isinstance(b.updated_at, dt.datetime)


# ---------------------------------------------------------------------------
# Surface repository tests
# ---------------------------------------------------------------------------


class TestSurfaceRepository:
    def _make_vertices(self) -> list[list[float]]:
        return [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]]

    def test_create_and_get_surface(self):
        with get_db_session() as s:
            create_building(s, "B001")
            surf = create_surface(
                s,
                surface_id="S001",
                building_id="B001",
                vertices=self._make_vertices(),
                area_m2=400.0,
                surface_type="roof",
                azimuth_deg=180.0,
                tilt_deg=0.0,
                normal={"x": 0.0, "y": 0.0, "z": 1.0},
            )
            assert surf.surface_id == "S001"

        with get_db_session() as s:
            fetched = get_surface(s, "S001")
            assert fetched.area_m2 == 400.0
            assert fetched.surface_type == "roof"

    def test_create_surface_no_building_raises(self):
        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                create_surface(
                    s,
                    surface_id="S001",
                    building_id="MISSING",
                    vertices=self._make_vertices(),
                    area_m2=400.0,
                    surface_type="roof",
                    azimuth_deg=180.0,
                    tilt_deg=0.0,
                    normal={"x": 0.0, "y": 0.0, "z": 1.0},
                )

    def test_create_duplicate_surface_raises(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001", self._make_vertices(),
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
        with get_db_session() as s:
            with pytest.raises(ValueError, match="already exists"):
                create_surface(
                    s, "S001", "B001", self._make_vertices(),
                    400.0, "roof", 180.0, 0.0,
                    {"x": 0, "y": 0, "z": 1},
                )

    def test_list_surfaces_for_building(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001", self._make_vertices(),
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            create_surface(
                s, "S002", "B001", self._make_vertices(),
                200.0, "facade", 90.0, 90.0,
                {"x": 1, "y": 0, "z": 0},
            )

        with get_db_session() as s:
            surfaces = list_surfaces_for_building(s, "B001")
            assert len(surfaces) == 2

    def test_surface_vertices_stored_as_json(self):
        verts = [[0, 0, 10], [10, 0, 10], [5, 8.66, 10]]
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001", verts,
                50.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )

        with get_db_session() as s:
            surf = get_surface(s, "S001")
            assert surf.vertices["coordinates"] == verts

    def test_surface_with_optional_metadata(self):
        with get_db_session() as s:
            create_building(s, "B001")
            surf = create_surface(
                s, "S001", "B001", self._make_vertices(),
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
                centroid=[10.0, 10.0, 10.0],
                bounding_box={"min_x": 0, "max_x": 20},
            )
            assert surf.centroid == [10.0, 10.0, 10.0]

    def test_cascade_delete_building_removes_surfaces(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001", self._make_vertices(),
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )

        with get_db_session() as s:
            delete_building(s, "B001")

        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                get_surface(s, "S001")


# ---------------------------------------------------------------------------
# Analysis result repository tests
# ---------------------------------------------------------------------------


class TestAnalysisRepository:
    def test_save_and_get_analysis(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            result = save_analysis(
                s,
                surface_id="S001",
                building_id="B001",
                solar_score=0.85,
                solar_suitability="high",
                usable_area_m2=320.0,
                estimated_capacity_kw=64.0,
                estimated_annual_energy_kwh=108800.0,
            )
            assert result.solar_score == 0.85

        with get_db_session() as s:
            fetched = get_analysis(s, "S001")
            assert fetched.solar_suitability == "high"
            assert fetched.estimated_capacity_kw == 64.0

    def test_save_analysis_updates_existing(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            save_analysis(
                s, "S001", "B001",
                0.5, "medium", 200.0, 40.0, 54400.0,
            )
            # Update
            updated = save_analysis(
                s, "S001", "B001",
                0.9, "high", 320.0, 64.0, 108800.0,
                composite_score=0.88,
                recommendation="Top-ranked surface.",
            )
            assert updated.solar_score == 0.9

        with get_db_session() as s:
            fetched = get_analysis(s, "S001")
            assert fetched.solar_score == 0.9
            assert fetched.composite_score == 0.88

    def test_get_nonexistent_analysis_raises(self):
        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                get_analysis(s, "MISSING")

    def test_list_analyses_by_building(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            create_surface(
                s, "S002", "B001",
                [[0, 0, 0], [10, 0, 0], [10, 0, 10], [0, 0, 10]],
                100.0, "facade", 180.0, 90.0,
                {"x": 0, "y": -1, "z": 0},
            )
            save_analysis(s, "S001", "B001", 0.8, "high", 320.0, 64.0, 108800.0)
            save_analysis(s, "S002", "B001", 0.4, "low", 65.0, 13.0, 22100.0)

        with get_db_session() as s:
            results = list_analyses(s, building_id="B001")
            assert len(results) == 2

    def test_analysis_with_ml_prediction(self):
        ml_pred = {"model": "v1", "confidence": 0.92}
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            save_analysis(
                s, "S001", "B001",
                0.9, "high", 320.0, 64.0, 108800.0,
                ml_prediction=ml_pred,
            )

        with get_db_session() as s:
            result = get_analysis(s, "S001")
            assert result.ml_prediction == ml_pred


# ---------------------------------------------------------------------------
# Solar prediction repository tests
# ---------------------------------------------------------------------------


class TestPredictionRepository:
    def test_save_and_list_predictions(self):
        with get_db_session() as s:
            create_building(s, "B001")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            save_prediction(
                s,
                surface_id="S001",
                building_id="B001",
                available=True,
                prediction={"annual_kwh": 108800},
                fallback_score=0.85,
                fallback_suitability="high",
                fallback_energy={
                    "usable_area_m2": 320.0,
                    "estimated_capacity_kw": 64.0,
                    "estimated_annual_energy_kwh": 108800.0,
                },
            )

        with get_db_session() as s:
            preds = list_predictions(s, surface_id="S001")
            assert len(preds) == 1
            assert preds[0].available is True
            assert preds[0].prediction == {"annual_kwh": 108800}

    def test_list_predictions_by_building(self):
        with get_db_session() as s:
            create_building(s, "B001")
            for i in range(3):
                create_surface(
                    s, f"S{i:03d}", "B001",
                    [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
                    100.0, "roof", 180.0, 0.0,
                    {"x": 0, "y": 0, "z": 1},
                )
                save_prediction(
                    s, f"S{i:03d}", "B001",
                    available=False, prediction=None,
                    fallback_score=0.5, fallback_suitability="medium",
                    fallback_energy={
                        "usable_area_m2": 80.0,
                        "estimated_capacity_kw": 16.0,
                        "estimated_annual_energy_kwh": 27200.0,
                    },
                )

        with get_db_session() as s:
            preds = list_predictions(s, building_id="B001")
            assert len(preds) == 3


# ---------------------------------------------------------------------------
# Pipeline run repository tests
# ---------------------------------------------------------------------------


class TestPipelineRunRepository:
    def test_create_and_update_pipeline_run(self):
        with get_db_session() as s:
            run = create_pipeline_run(
                s, "solar_pipeline",
                metadata_json={"source": "test"},
            )
            assert run.status == "running"
            run_id = run.id

        with get_db_session() as s:
            updated = update_pipeline_run(
                s, run_id,
                status="success",
                records_processed=1500,
            )
            assert updated.status == "success"
            assert updated.records_processed == 1500
            assert updated.finished_at is not None

    def test_update_nonexistent_run_raises(self):
        with get_db_session() as s:
            with pytest.raises(ValueError, match="not found"):
                update_pipeline_run(s, 99999, status="failed")

    def test_list_pipeline_runs(self):
        with get_db_session() as s:
            create_pipeline_run(s, "solar")
            create_pipeline_run(s, "weather")
            create_pipeline_run(s, "solar", status="success")

        with get_db_session() as s:
            all_runs = list_pipeline_runs(s)
            assert len(all_runs) == 3

            solar_only = list_pipeline_runs(s, pipeline_name="solar")
            assert len(solar_only) == 2

    def test_pipeline_run_with_error(self):
        with get_db_session() as s:
            run = create_pipeline_run(s, "test_pipeline")
            update_pipeline_run(
                s, run.id,
                status="failed",
                error_message="Connection timeout",
            )

        with get_db_session() as s:
            runs = list_pipeline_runs(s, pipeline_name="test_pipeline")
            assert runs[0].status == "failed"
            assert runs[0].error_message == "Connection timeout"


# ---------------------------------------------------------------------------
# Model metadata repository tests
# ---------------------------------------------------------------------------


class TestModelMetadataRepository:
    def test_register_and_get_model(self):
        with get_db_session() as s:
            record = register_model(
                s,
                model_name="solar_predictor",
                version="1.0.0",
                model_type="solar_prediction",
                model_path="/models/solar_v1.pkl",
                metrics={"rmse": 0.05, "r2": 0.92},
            )
            assert record.status == "registered"

        with get_db_session() as s:
            model = get_model_metadata(s, "solar_predictor")
            assert model is not None
            assert model.version == "1.0.0"
            assert model.metrics["r2"] == 0.92

    def test_get_specific_version(self):
        with get_db_session() as s:
            register_model(s, "m", "1.0", "test")
            register_model(s, "m", "2.0", "test")

        with get_db_session() as s:
            v1 = get_model_metadata(s, "m", version="1.0")
            assert v1 is not None
            assert v1.version == "1.0"

            v2 = get_model_metadata(s, "m", version="2.0")
            assert v2 is not None
            assert v2.version == "2.0"

    def test_get_nonexistent_model_returns_none(self):
        with get_db_session() as s:
            result = get_model_metadata(s, "no_such_model")
            assert result is None

    def test_list_models_by_type(self):
        with get_db_session() as s:
            register_model(s, "a", "1.0", "solar_prediction")
            register_model(s, "b", "1.0", "irradiance_forecast")
            register_model(s, "c", "1.0", "solar_prediction")

        with get_db_session() as s:
            solar = list_models(s, model_type="solar_prediction")
            assert len(solar) == 2

    def test_model_status_transitions(self):
        with get_db_session() as s:
            record = register_model(
                s, "m", "1.0", "test", status="registered",
            )
            assert record.status == "registered"

        with get_db_session() as s:
            model = get_model_metadata(s, "m", version="1.0")
            assert model is not None
            model.status = "active"
            s.flush()

        with get_db_session() as s:
            model = get_model_metadata(s, "m", version="1.0")
            assert model.status == "active"


# ---------------------------------------------------------------------------
# Cross-table integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end tests exercising multiple repository functions."""

    def test_full_building_lifecycle(self):
        """Create building -> surfaces -> analysis -> prediction."""
        with get_db_session() as s:
            create_building(s, "B001", name="Test Building")
            create_surface(
                s, "S001", "B001",
                [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
                400.0, "roof", 180.0, 0.0,
                {"x": 0, "y": 0, "z": 1},
            )
            save_analysis(
                s, "S001", "B001",
                0.85, "high", 320.0, 64.0, 108800.0,
                composite_score=0.9,
                recommendation="Excellent roof surface.",
            )
            save_prediction(
                s, "S001", "B001",
                available=False, prediction=None,
                fallback_score=0.85, fallback_suitability="high",
                fallback_energy={
                    "usable_area_m2": 320.0,
                    "estimated_capacity_kw": 64.0,
                    "estimated_annual_energy_kwh": 108800.0,
                },
            )

        # Verify everything persisted.
        with get_db_session() as s:
            b = get_building(s, "B001")
            assert b.name == "Test Building"
            surfaces = list_surfaces_for_building(s, "B001")
            assert len(surfaces) == 1
            analysis = get_analysis(s, "S001")
            assert analysis.recommendation == "Excellent roof surface."
            preds = list_predictions(s, surface_id="S001")
            assert len(preds) == 1

        # Delete building cascades.
        with get_db_session() as s:
            delete_building(s, "B001")

        with get_db_session() as s:
            assert count_buildings(s) == 0

    def test_pipeline_run_lifecycle(self):
        """Simulate a complete pipeline execution record."""
        with get_db_session() as s:
            run = create_pipeline_run(
                s, "weather_pipeline",
                metadata_json={"source": "open-meteo"},
            )
            run_id = run.id

        with get_db_session() as s:
            update_pipeline_run(
                s, run_id,
                status="success",
                records_processed=8760,
                metadata_json={"source": "open-meteo", "hours": 8760},
            )

        with get_db_session() as s:
            runs = list_pipeline_runs(s, "weather_pipeline")
            assert len(runs) == 1
            assert runs[0].status == "success"
            assert runs[0].records_processed == 8760
            assert runs[0].metadata_json["hours"] == 8760

    def test_multiple_buildings_with_analyses(self):
        """Create multiple buildings and verify aggregation."""
        with get_db_session() as s:
            for bid in ["B001", "B002", "B003"]:
                create_building(s, bid, name=f"Building {bid}")
                create_surface(
                    s, f"{bid}-S1", bid,
                    [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
                    100.0, "roof", 180.0, 0.0,
                    {"x": 0, "y": 0, "z": 1},
                )
                save_analysis(
                    s, f"{bid}-S1", bid,
                    0.7, "medium", 80.0, 16.0, 27200.0,
                )

        with get_db_session() as s:
            assert count_buildings(s) == 3
            all_a = list_analyses(s)
            assert len(all_a) == 3
            total_capacity = sum(a.estimated_capacity_kw for a in all_a)
            assert total_capacity == pytest.approx(48.0)
