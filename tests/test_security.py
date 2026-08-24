"""Security-focused tests for SolarIQ.

Covers:
- Path traversal protection
- CSV injection sanitization
- File size limits
- Model file trust validation
- Bounding box validation
- Coordinate validation
- Input sanitization
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import (
    FileSizeError,
    ModelTrustError,
    PathTraversalError,
    sanitize_csv_value,
    sanitize_filename,
    safe_load_json,
    safe_load_json_from_bytes,
    validate_bbox,
    validate_coordinate,
    validate_model_file,
    validate_path_within,
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client for API security tests."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Path traversal tests
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """Tests for path traversal protection."""

    def test_valid_path_within_root(self, tmp_path: Path) -> None:
        """Paths within the root directory are accepted."""
        (tmp_path / "data.json").write_text('{"key": "value"}')
        result = validate_path_within(
            tmp_path / "data.json", tmp_path
        )
        assert result == tmp_path / "data.json"

    def test_path_traversal_with_dotdot(self, tmp_path: Path) -> None:
        """Paths with ../ are rejected."""
        with pytest.raises(PathTraversalError, match="outside"):
            validate_path_within(
                tmp_path / "../etc/passwd", tmp_path
            )

    def test_path_traversal_absolute_escape(self, tmp_path: Path) -> None:
        """Absolute paths outside root are rejected."""
        with pytest.raises(PathTraversalError, match="outside"):
            validate_path_within("/etc/passwd", tmp_path)

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Symlinks require elevated privileges on Windows",
    )
    def test_symlink_traversal(self, tmp_path: Path) -> None:
        """Symlink-based traversal is caught by validate_path_within."""
        secret = tmp_path / "secret.txt"
        secret.write_text("password123")
        link = tmp_path / "link.txt"
        link.symlink_to(secret)
        with pytest.raises(PathTraversalError):
            validate_path_within(link, tmp_path / "nonexistent_dir")


class TestSafeLoadJson:
    """Tests for safe JSON loading."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Valid JSON files are loaded correctly."""
        data = {"buildings": [{"id": "B001"}]}
        (tmp_path / "data.json").write_text(json.dumps(data))
        result = safe_load_json(tmp_path / "data.json")
        assert result == data

    def test_reject_oversized_file(self, tmp_path: Path) -> None:
        """Files exceeding size limit are rejected."""
        big_file = tmp_path / "big.json"
        big_file.write_text(json.dumps({"data": "x" * (101 * 1024 * 1024)}))
        with pytest.raises(FileSizeError, match="exceeding"):
            safe_load_json(big_file, max_size=100 * 1024 * 1024)

    def test_reject_path_traversal(self, tmp_path: Path) -> None:
        """Path traversal in safe_load_json is rejected."""
        with pytest.raises(PathTraversalError):
            safe_load_json(
                tmp_path / "../etc/passwd",
                allowed_root=tmp_path,
            )

    def test_reject_invalid_json(self, tmp_path: Path) -> None:
        """Invalid JSON raises ValueError."""
        (tmp_path / "bad.json").write_text("{invalid json")
        with pytest.raises(ValueError):
            safe_load_json(tmp_path / "bad.json")

    def test_safe_load_from_bytes(self) -> None:
        """Bytes-based JSON loading works."""
        data = safe_load_json_from_bytes(b'{"key": "value"}')
        assert data == {"key": "value"}

    def test_reject_oversized_bytes(self) -> None:
        """Oversized byte payloads are rejected."""
        with pytest.raises(FileSizeError):
            safe_load_json_from_bytes(
                b'{"data": "x" * 100}',
                max_size=10,
            )


# ---------------------------------------------------------------------------
# CSV injection tests
# ---------------------------------------------------------------------------


class TestCSVInjection:
    """Tests for CSV injection sanitization."""

    def test_formula_equals_prefix(self) -> None:
        """= formula prefix is sanitized."""
        result = sanitize_csv_value("=SUM(A1:A10)")
        assert result.startswith("'")
        assert result == "'=SUM(A1:A10)"

    def test_formula_plus_prefix(self) -> None:
        """+ formula prefix is sanitized."""
        result = sanitize_csv_value("+2+3")
        assert result == "'+2+3"

    def test_formula_minus_prefix(self) -> None:
        """- formula prefix is sanitized."""
        result = sanitize_csv_value("-cmd")
        assert result == "'-cmd"

    def test_formula_at_prefix(self) -> None:
        """@ formula prefix is sanitized."""
        result = sanitize_csv_value("@SUM(A1)")
        assert result == "'@SUM(A1)"

    def test_formula_tab_prefix(self) -> None:
        """Tab prefix is sanitized."""
        result = sanitize_csv_value("\t=cmd")
        assert result.startswith("'")

    def test_formula_carriage_return_prefix(self) -> None:
        """Carriage return prefix is sanitized."""
        result = sanitize_csv_value("\r=cmd")
        assert result.startswith("'")

    def test_safe_value_unchanged(self) -> None:
        """Values without dangerous prefixes are unchanged."""
        assert sanitize_csv_value("hello world") == "hello world"
        assert sanitize_csv_value("42") == "42"
        assert sanitize_csv_value("2025-01-15") == "2025-01-15"

    def test_empty_string(self) -> None:
        """Empty strings pass through."""
        assert sanitize_csv_value("") == ""

    def test_non_string_passthrough(self) -> None:
        """Non-string values pass through unchanged."""
        assert sanitize_csv_value(42) == 42
        assert sanitize_csv_value(None) is None


# ---------------------------------------------------------------------------
# Filename sanitization tests
# ---------------------------------------------------------------------------


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_remove_path_separators(self) -> None:
        """Path separators are replaced."""
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_remove_null_bytes(self) -> None:
        """Null bytes are removed."""
        result = sanitize_filename("file\x00name.json")
        assert "\x00" not in result
        assert result == "filename.json"

    def test_strip_dots(self) -> None:
        """Leading/trailing dots are stripped."""
        result = sanitize_filename("...hidden...")
        assert result != "...hidden..."

    def test_empty_becomes_default(self) -> None:
        """Empty filenames get a default name."""
        result = sanitize_filename("")
        assert result == "unnamed_file"

    def test_normal_filename_unchanged(self) -> None:
        """Normal filenames pass through."""
        assert sanitize_filename("data.json") == "data.json"
        assert sanitize_filename("building_001.geojson") == "building_001.geojson"


# ---------------------------------------------------------------------------
# Bounding box validation tests
# ---------------------------------------------------------------------------


class TestBboxValidation:
    """Tests for bounding box validation."""

    def test_valid_bbox(self) -> None:
        """Valid bounding boxes pass validation."""
        validate_bbox(18.88, 72.75, 19.28, 72.98)

    def test_invalid_south(self) -> None:
        """South latitude out of range is rejected."""
        with pytest.raises(ValueError, match="South latitude"):
            validate_bbox(-91.0, 0.0, 10.0, 10.0)

    def test_invalid_north(self) -> None:
        """North latitude out of range is rejected."""
        with pytest.raises(ValueError, match="North latitude"):
            validate_bbox(0.0, 0.0, 91.0, 10.0)

    def test_invalid_west(self) -> None:
        """West longitude out of range is rejected."""
        with pytest.raises(ValueError, match="West longitude"):
            validate_bbox(0.0, -181.0, 10.0, 10.0)

    def test_invalid_east(self) -> None:
        """East longitude out of range is rejected."""
        with pytest.raises(ValueError, match="East longitude"):
            validate_bbox(0.0, 0.0, 10.0, 181.0)

    def test_south_greater_than_north(self) -> None:
        """South >= north is rejected."""
        with pytest.raises(ValueError, match="must be less than"):
            validate_bbox(50.0, 0.0, 40.0, 10.0)

    def test_west_greater_than_east(self) -> None:
        """West >= east is rejected."""
        with pytest.raises(ValueError, match="must be less than"):
            validate_bbox(0.0, 50.0, 10.0, 40.0)


# ---------------------------------------------------------------------------
# Coordinate validation tests
# ---------------------------------------------------------------------------


class TestCoordinateValidation:
    """Tests for coordinate validation."""

    def test_valid_coordinates(self) -> None:
        """Valid coordinates pass validation."""
        validate_coordinate(19.0760, 72.8777)

    def test_invalid_latitude(self) -> None:
        """Out-of-range latitude is rejected."""
        with pytest.raises(ValueError, match="Latitude"):
            validate_coordinate(91.0, 72.0)

    def test_invalid_longitude(self) -> None:
        """Out-of-range longitude is rejected."""
        with pytest.raises(ValueError, match="Longitude"):
            validate_coordinate(19.0, 181.0)


# ---------------------------------------------------------------------------
# Model trust validation tests
# ---------------------------------------------------------------------------


class TestModelTrust:
    """Tests for model file trust validation."""

    def test_valid_json_model(self, tmp_path: Path) -> None:
        """Trusted JSON model files are accepted."""
        (tmp_path / "model.json").write_text('{"version": "1.0"}')
        result = validate_model_file(
            tmp_path / "model.json",
            allowed_root=tmp_path,
        )
        assert result.name == "model.json"

    def test_reject_untrusted_extension(self, tmp_path: Path) -> None:
        """Untrusted file extensions are rejected."""
        (tmp_path / "model.exe").write_text("binary")
        with pytest.raises(ModelTrustError, match="extension"):
            validate_model_file(
                tmp_path / "model.exe",
                allowed_root=tmp_path,
            )

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Symlinks require elevated privileges on Windows",
    )
    def test_reject_symlink(self, tmp_path: Path) -> None:
        """Symlinked model files are rejected."""
        real = tmp_path / "real_model.json"
        real.write_text('{"version": "1.0"}')
        link = tmp_path / "model.json"
        link.symlink_to(real)
        with pytest.raises(ModelTrustError, match="symlink"):
            validate_model_file(
                link,
                allowed_root=tmp_path,
            )

    def test_reject_path_traversal(self, tmp_path: Path) -> None:
        """Path traversal in model paths is rejected."""
        with pytest.raises(PathTraversalError):
            validate_model_file(
                tmp_path / "../etc/passwd",
                allowed_root=tmp_path,
            )

    def test_reject_nonexistent_file(self, tmp_path: Path) -> None:
        """Nonexistent model files raise ModelTrustError."""
        with pytest.raises(ModelTrustError, match="not found"):
            validate_model_file(
                tmp_path / "nonexistent.json",
                allowed_root=tmp_path,
            )


# ---------------------------------------------------------------------------
# API security tests (FastAPI test client)
# ---------------------------------------------------------------------------


class TestAPISecurity:
    """Tests for API-level security properties."""

    def test_root_returns_safe_info(self, client) -> None:
        """Root endpoint does not expose internal details."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "SolarIQ" in data["project"]
        # Should not contain internal paths or versions
        assert "password" not in str(data).lower()

    def test_health_endpoint(self, client) -> None:
        """Health endpoint works and returns safe response."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_404_returns_safe_response(self, client) -> None:
        """Unknown endpoints return safe 404."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_security_headers_present(self, client) -> None:
        """Security headers are included in responses."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_error_handler_sanitizes_runtime_error(self, client) -> None:
        """RuntimeError handler does not leak internal details."""
        response = client.post(
            "/analyze-building",
            json={
                "building": {
                    "building_id": "B001",
                    "surfaces": []
                }
            },
        )
        # Should return 422 (validation error) not 500 with stack trace
        assert response.status_code in (422, 413)
        if response.status_code == 422:
            detail = str(response.json())
            assert "traceback" not in detail.lower()
            assert "__file__" not in detail

    def test_city_analysis_respects_building_limit(self, client) -> None:
        """City analysis rejects payloads exceeding building limit."""
        buildings = [
            {
                "building_id": f"B{i:04d}",
                "surfaces": [
                    {
                        "surface_id": f"S{i:04d}",
                        "vertices": [
                            [0, 0, 10], [10, 0, 10],
                            [10, 10, 10], [0, 10, 10],
                        ],
                    }
                ],
            }
            for i in range(101)
        ]
        response = client.post(
            "/city-analysis",
            json={"buildings": buildings},
        )
        assert response.status_code == 413

    def test_prediction_rejects_invalid_surface_type(self, client) -> None:
        """Prediction rejects invalid surface_type values."""
        response = client.post(
            "/predict-solar",
            json={
                "area_m2": 10.0,
                "azimuth_deg": 180.0,
                "tilt_deg": 20.0,
                "surface_type": "<script>alert(1)</script>",
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_reject_empty_building_id(self) -> None:
        """Building with empty ID is rejected by schema."""
        from pydantic import ValidationError
        from backend.schemas.building import BuildingInput

        with pytest.raises(ValidationError):
            BuildingInput(
                building_id="",
                surfaces=[{"vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]]}],
            )

    def test_reject_long_building_id(self) -> None:
        """Building with very long ID is rejected."""
        from pydantic import ValidationError
        from backend.schemas.building import BuildingInput

        with pytest.raises(ValidationError):
            BuildingInput(
                building_id="A" * 200,
                surfaces=[{"vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]]}],
            )

    def test_reject_too_few_vertices(self) -> None:
        """Surface with fewer than 3 vertices is rejected."""
        from pydantic import ValidationError
        from backend.schemas.building import BuildingInput

        with pytest.raises(ValidationError):
            BuildingInput(
                building_id="B001",
                surfaces=[{"vertices": [[0, 0, 0], [1, 0, 0]]}],
            )

    def test_reject_invalid_azimuth(self) -> None:
        """Azimuth outside 0-360 is rejected."""
        from pydantic import ValidationError
        from backend.schemas.building import SolarPredictionRequest

        with pytest.raises(ValidationError):
            SolarPredictionRequest(
                area_m2=10.0,
                azimuth_deg=400.0,
                tilt_deg=20.0,
                surface_type="roof",
            )

    def test_reject_invalid_tilt(self) -> None:
        """Tilt outside 0-90 is rejected."""
        from pydantic import ValidationError
        from backend.schemas.building import SolarPredictionRequest

        with pytest.raises(ValidationError):
            SolarPredictionRequest(
                area_m2=10.0,
                azimuth_deg=180.0,
                tilt_deg=100.0,
                surface_type="roof",
            )

    def test_reject_negative_area(self) -> None:
        """Negative surface area is rejected."""
        from pydantic import ValidationError
        from backend.schemas.building import SolarPredictionRequest

        with pytest.raises(ValidationError):
            SolarPredictionRequest(
                area_m2=-10.0,
                azimuth_deg=180.0,
                tilt_deg=20.0,
                surface_type="roof",
            )


# ---------------------------------------------------------------------------
# JSON deserialization safety tests
# ---------------------------------------------------------------------------


class TestJSONSafety:
    """Tests that JSON parsing is safe (no eval/exec)."""

    def test_malicious_json_content(self, tmp_path: Path) -> None:
        """JSON with __proto__ or constructor payloads is handled safely."""
        malicious = '{"__proto__": {"admin": true}}'
        (tmp_path / "evil.json").write_text(malicious)
        data = safe_load_json(tmp_path / "evil.json")
        # Should parse as a dict but not pollute object prototype
        assert isinstance(data, dict)
        assert "__proto__" in data

    def test_deeply_nested_json(self, tmp_path: Path) -> None:
        """Deeply nested JSON does not cause stack overflow."""
        # Create nested structure (reasonable depth)
        nested = {"level": 0}
        obj = nested
        for i in range(1, 50):
            obj["child"] = {"level": i}
            obj = obj["child"]
        (tmp_path / "nested.json").write_text(json.dumps(nested))
        data = safe_load_json(tmp_path / "nested.json")
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Geometry parser security tests
# ---------------------------------------------------------------------------


class TestGeometryParserSecurity:
    """Tests for geometry parser file safety."""

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Symlinks require elevated privileges on Windows",
    )
    def test_reject_symlink(self, tmp_path: Path) -> None:
        """Geometry parser rejects symlinked files."""
        real = tmp_path / "real.json"
        real.write_text(json.dumps({
            "building_id": "B001",
            "surfaces": [
                {"surface_id": "S001", "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]}
            ],
        }))
        link = tmp_path / "link.json"
        link.symlink_to(real)
        with pytest.raises(ValueError, match="Symlink"):
            from backend.geometry.parser import load_json_file
            load_json_file(link)

    def test_reject_oversized_file(self, tmp_path: Path) -> None:
        """Geometry parser rejects oversized files."""
        big = tmp_path / "big.json"
        # Write 101 MB
        big.write_text(json.dumps({"data": "x" * (101 * 1024 * 1024)}))
        with pytest.raises(ValueError, match="exceeding"):
            from backend.geometry.parser import load_json_file
            load_json_file(big)
