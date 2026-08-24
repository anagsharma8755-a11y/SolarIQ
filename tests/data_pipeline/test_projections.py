"""Tests for projection helpers."""

from __future__ import annotations

import pytest

from data_pipeline.geo.projections import (
    auto_utm_crs_for_points,
    detect_crs,
    epsg_to_utm,
    get_epsg_for_utm,
    project_points,
    utm_to_epsg,
)


class TestDetectCRS:
    """Tests for CRS detection."""

    def test_string_crs(self) -> None:
        crs = detect_crs("EPSG:4326")
        assert crs.to_epsg() == 4326

    def test_crs_object(self) -> None:
        from pyproj import CRS
        crs_in = CRS.from_epsg(32643)
        crs = detect_crs(crs_in)
        assert crs.to_epsg() == 32643


class TestAutoUTMCRS:
    """Tests for automatic UTM CRS detection."""

    def test_single_point(self) -> None:
        """Single point should detect correct UTM zone."""
        crs = auto_utm_crs_for_points([(72.878, 19.076)])
        assert crs.to_epsg() == 32643

    def test_multiple_points(self) -> None:
        """Multiple points should use mean location."""
        points = [
            (72.878, 19.076),
            (72.880, 19.078),
        ]
        crs = auto_utm_crs_for_points(points)
        assert crs.to_epsg() == 32643

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            auto_utm_crs_for_points([])


class TestProjectPoints:
    """Tests for point projection."""

    def test_wgs84_to_utm(self) -> None:
        results = project_points(
            [(72.878, 19.076)],
            "EPSG:4326",
            "EPSG:32643",
        )
        assert len(results) == 1
        assert results[0][0] > 0  # easting
        assert results[0][1] > 0  # northing

    def test_utm_to_wgs84(self) -> None:
        results = project_points(
            [(276720.9059, 2110588.4563)],
            "EPSG:32643",
            "EPSG:4326",
        )
        assert len(results) == 1
        lat, lon = results[0][1], results[0][0]
        assert abs(lat - 19.076) < 0.01
        assert abs(lon - 72.878) < 0.01

    def test_3d_preserves_z(self) -> None:
        results = project_points(
            [(72.878, 19.076, 42.0)],
            "EPSG:4326",
            "EPSG:32643",
        )
        assert len(results[0]) == 3
        assert results[0][2] == 42.0


class TestEPSGConversion:
    """Tests for EPSG ↔ UTM zone conversion."""

    def test_get_epsg_northern(self) -> None:
        epsg = get_epsg_for_utm(19.076, 72.878)
        assert epsg == 32643

    def test_get_epsg_southern(self) -> None:
        epsg = get_epsg_for_utm(-33.869, 151.209)
        assert epsg == 32756

    def test_utm_to_epsg_north(self) -> None:
        assert utm_to_epsg(43, "N") == 32643

    def test_utm_to_epsg_south(self) -> None:
        assert utm_to_epsg(56, "S") == 32756

    def test_epsg_to_utm_north(self) -> None:
        zone, hemi = epsg_to_utm(32643)
        assert zone == 43
        assert hemi == "N"

    def test_epsg_to_utm_south(self) -> None:
        zone, hemi = epsg_to_utm(32756)
        assert zone == 56
        assert hemi == "S"

    def test_epsg_to_utm_invalid(self) -> None:
        with pytest.raises(ValueError, match="not a valid UTM code"):
            epsg_to_utm(4326)
