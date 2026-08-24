"""Tests for validation utilities."""

from __future__ import annotations

import pytest

from data_pipeline.validation import (
    build_validation_result,
    validate_building,
    validate_latitude,
    validate_longitude,
    validate_range,
    validate_solar_record,
    validate_timestamp,
    validate_weather_record,
)


class TestLatitudeValidation:
    """Tests for latitude validation."""

    def test_valid(self) -> None:
        assert validate_latitude(19.076) is None

    def test_boundary_north(self) -> None:
        assert validate_latitude(90.0) is None

    def test_boundary_south(self) -> None:
        assert validate_latitude(-90.0) is None

    def test_out_of_range_high(self) -> None:
        err = validate_latitude(91.0)
        assert err is not None
        assert "out of range" in err

    def test_out_of_range_low(self) -> None:
        err = validate_latitude(-91.0)
        assert err is not None

    def test_nan(self) -> None:
        err = validate_latitude(float("nan"))
        assert err is not None
        assert "NaN" in err

    def test_inf(self) -> None:
        err = validate_latitude(float("inf"))
        assert err is not None
        assert "Infinity" in err

    def test_non_numeric(self) -> None:
        err = validate_latitude("abc")  # type: ignore
        assert err is not None
        assert "numeric" in err


class TestLongitudeValidation:
    """Tests for longitude validation."""

    def test_valid(self) -> None:
        assert validate_longitude(72.878) is None

    def test_boundary_east(self) -> None:
        assert validate_longitude(180.0) is None

    def test_boundary_west(self) -> None:
        assert validate_longitude(-180.0) is None

    def test_out_of_range(self) -> None:
        err = validate_longitude(181.0)
        assert err is not None

    def test_nan(self) -> None:
        err = validate_longitude(float("nan"))
        assert err is not None


class TestTimestampValidation:
    """Tests for timestamp validation."""

    def test_valid_iso8601(self) -> None:
        assert validate_timestamp("2024-01-15T08:00:00Z") is None

    def test_valid_date_only(self) -> None:
        assert validate_timestamp("2024-01-15") is None

    def test_empty_string(self) -> None:
        err = validate_timestamp("")
        assert err is not None

    def test_non_string(self) -> None:
        err = validate_timestamp(12345)  # type: ignore
        assert err is not None


class TestRangeValidation:
    """Tests for generic range validation."""

    def test_in_range(self) -> None:
        assert validate_range(50.0, 0.0, 100.0, "test") is None

    def test_below_range(self) -> None:
        err = validate_range(-1.0, 0.0, 100.0, "test")
        assert err is not None

    def test_above_range(self) -> None:
        err = validate_range(101.0, 0.0, 100.0, "test")
        assert err is not None

    def test_boundary(self) -> None:
        assert validate_range(0.0, 0.0, 100.0, "test") is None
        assert validate_range(100.0, 0.0, 100.0, "test") is None

    def test_non_numeric(self) -> None:
        err = validate_range("abc", 0.0, 100.0, "test")  # type: ignore
        assert err is not None


class TestWeatherRecordValidation:
    """Tests for weather record validation."""

    def test_valid_record(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 19.076,
            "longitude": 72.878,
            "temperature": 25.0,
            "humidity": 70.0,
            "wind_speed": 5.0,
            "cloud_cover": 30.0,
            "precipitation": 0.0,
        }
        errors = validate_weather_record(record, 0)
        assert len(errors) == 0

    def test_missing_timestamp(self) -> None:
        record = {
            "latitude": 19.076,
            "longitude": 72.878,
        }
        errors = validate_weather_record(record, 0)
        assert any(e.field == "timestamp" for e in errors)

    def test_invalid_latitude(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 999.0,
            "longitude": 72.878,
        }
        errors = validate_weather_record(record, 0)
        assert any(e.field == "latitude" for e in errors)

    def test_humidity_out_of_range(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 19.076,
            "longitude": 72.878,
            "humidity": 150.0,
        }
        errors = validate_weather_record(record, 0)
        assert any(e.field == "humidity" for e in errors)


class TestSolarRecordValidation:
    """Tests for solar record validation."""

    def test_valid_record(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 19.076,
            "longitude": 72.878,
            "ghi": 500.0,
            "dni": 700.0,
            "dhi": 200.0,
            "solar_irradiance": 500.0,
        }
        errors = validate_solar_record(record, 0)
        assert len(errors) == 0

    def test_negative_irradiance(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 19.076,
            "longitude": 72.878,
            "ghi": -100.0,
        }
        errors = validate_solar_record(record, 0)
        assert any(e.field == "ghi" for e in errors)

    def test_excessive_irradiance(self) -> None:
        record = {
            "timestamp": "2024-01-15T08:00:00Z",
            "latitude": 19.076,
            "longitude": 72.878,
            "ghi": 2000.0,
        }
        errors = validate_solar_record(record, 0)
        assert any(e.field == "ghi" for e in errors)


class TestBuildingValidation:
    """Tests for building validation."""

    def test_valid_building(self) -> None:
        building = {
            "building_id": "B001",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0]],
                }
            ],
        }
        errors = validate_building(building, 0)
        assert len(errors) == 0

    def test_missing_building_id(self) -> None:
        building = {
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0]],
                }
            ],
        }
        errors = validate_building(building, 0)
        assert any(e.field == "building_id" for e in errors)

    def test_no_surfaces(self) -> None:
        building = {
            "building_id": "B001",
            "surfaces": [],
        }
        errors = validate_building(building, 0)
        assert any(e.field == "surfaces" for e in errors)

    def test_too_few_vertices(self) -> None:
        building = {
            "building_id": "B001",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [[0, 0, 0], [10, 0, 0]],
                }
            ],
        }
        errors = validate_building(building, 0)
        assert any("vertices" in e.field for e in errors)

    def test_invalid_coordinates(self) -> None:
        building = {
            "building_id": "B001",
            "coordinates": {
                "latitude": 999.0,
                "longitude": 72.878,
            },
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0]],
                }
            ],
        }
        errors = validate_building(building, 0)
        assert any("latitude" in e.field for e in errors)


class TestValidationResult:
    """Tests for ValidationResult construction."""

    def test_no_errors(self) -> None:
        result = build_validation_result(100, [])
        assert result.valid is True
        assert result.records_total == 100
        assert result.records_valid == 100
        assert result.records_invalid == 0

    def test_with_errors(self) -> None:
        from data_pipeline.schemas import ValidationError

        errors = [
            ValidationError(
                record_index=0,
                field="latitude",
                error="out of range",
            ),
            ValidationError(
                record_index=5,
                field="longitude",
                error="out of range",
            ),
        ]
        result = build_validation_result(100, errors)
        assert result.valid is False
        assert result.records_total == 100
        assert result.records_valid == 98
        assert result.records_invalid == 2
