"""Tests for coordinate transformation utilities."""

from __future__ import annotations

import pytest

from data_pipeline.geo.coordinates import (
    get_utm_crs,
    get_utm_zone,
    latlon_to_utm,
    round_trip_accuracy,
    transform_coordinates,
    utm_to_latlon,
    validate_coordinates,
    validate_latitude,
    validate_longitude,
)


# ---------------------------------------------------------------------------
# UTM zone detection
# ---------------------------------------------------------------------------


class TestUTMZoneDetection:
    """Tests for automatic UTM zone detection."""

    def test_mumbai(self) -> None:
        """Mumbai (72.878°E) should be in UTM zone 43."""
        assert get_utm_zone(72.878) == 43

    def test_new_york(self) -> None:
        """New York (-73.986°E) should be in UTM zone 18."""
        assert get_utm_zone(-73.986) == 18

    def test_london(self) -> None:
        """London (-0.128°E) should be in UTM zone 30."""
        assert get_utm_zone(-0.128) == 30

    def test_tokyo(self) -> None:
        """Tokyo (139.692°E) should be in UTM zone 54."""
        assert get_utm_zone(139.692) == 54

    def test_sydney(self) -> None:
        """Sydney (151.209°E) should be in UTM zone 56."""
        assert get_utm_zone(151.209) == 56

    def test_antimeridian_east(self) -> None:
        """Just west of the antimeridian (179°E) → zone 60."""
        assert get_utm_zone(179.0) == 60

    def test_antimeridian_west(self) -> None:
        """Just east of the antimeridian (-179°W) → zone 1."""
        assert get_utm_zone(-179.0) == 1


# ---------------------------------------------------------------------------
# UTM CRS creation
# ---------------------------------------------------------------------------


class TestUTMCRS:
    """Tests for UTM CRS generation."""

    def test_northern_hemisphere(self) -> None:
        """Positive latitude → northern hemisphere EPSG."""
        crs = get_utm_crs(19.076, 72.878)
        assert crs.to_epsg() == 32643

    def test_southern_hemisphere(self) -> None:
        """Negative latitude → southern hemisphere EPSG."""
        crs = get_utm_crs(-33.869, 151.209)
        assert crs.to_epsg() == 32756


# ---------------------------------------------------------------------------
# latlon_to_utm
# ---------------------------------------------------------------------------


class TestLatLonToUTM:
    """Tests for WGS84 → UTM conversion."""

    def test_mumbai(self) -> None:
        """Convert Mumbai coordinates to UTM."""
        easting, northing, elev, zone, hemi = latlon_to_utm(
            19.076, 72.878
        )
        assert zone == 43
        assert hemi == "N"
        assert easting > 0
        assert northing > 0
        assert elev == 0.0

    def test_southern_hemisphere(self) -> None:
        """Convert Sydney coordinates to UTM."""
        easting, northing, elev, zone, hemi = latlon_to_utm(
            -33.869, 151.209
        )
        assert zone == 56
        assert hemi == "S"

    def test_with_elevation(self) -> None:
        """Elevation should be preserved."""
        _, _, elev, _, _ = latlon_to_utm(19.076, 72.878, 42.5)
        assert elev == 42.5


# ---------------------------------------------------------------------------
# utm_to_latlon
# ---------------------------------------------------------------------------


class TestUTMToLatLon:
    """Tests for UTM → WGS84 conversion."""

    def test_northern_hemisphere(self) -> None:
        """Convert UTM zone 43N back to lat/lon."""
        lat, lon, elev = utm_to_latlon(
            easting=276720.9059,
            northing=2110588.4563,
            zone=43,
            hemisphere="N",
        )
        assert abs(lat - 19.076) < 0.01
        assert abs(lon - 72.878) < 0.01

    def test_southern_hemisphere(self) -> None:
        """Convert UTM zone 56S back to lat/lon."""
        lat, lon, elev = utm_to_latlon(
            easting=335000.0,
            northing=6250000.0,
            zone=56,
            hemisphere="S",
        )
        # Should be near Sydney
        assert -35.0 < lat < -33.0
        assert 150.0 < lon < 152.0

    def test_invalid_zone(self) -> None:
        """Invalid UTM zone should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UTM zone"):
            utm_to_latlon(0, 0, 0, "N")

    def test_invalid_hemisphere(self) -> None:
        """Invalid hemisphere should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid hemisphere"):
            utm_to_latlon(0, 0, 18, "X")


# ---------------------------------------------------------------------------
# Round-trip accuracy
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Tests for round-trip coordinate conversion accuracy."""

    def test_round_trip_mumbai(self) -> None:
        """Round-trip accuracy for Mumbai coordinates."""
        result = round_trip_accuracy(19.076, 72.878)
        assert result["lat_error"] < 0.001
        assert result["lon_error"] < 0.001

    def test_round_trip_new_york(self) -> None:
        """Round-trip accuracy for New York coordinates."""
        result = round_trip_accuracy(40.7128, -74.0060)
        assert result["lat_error"] < 0.001
        assert result["lon_error"] < 0.001

    def test_round_trip_southern(self) -> None:
        """Round-trip accuracy for Sydney coordinates."""
        result = round_trip_accuracy(-33.869, 151.209)
        assert result["lat_error"] < 0.001
        assert result["lon_error"] < 0.001

    def test_round_trip_with_elevation(self) -> None:
        """Round-trip preserves elevation."""
        result = round_trip_accuracy(19.076, 72.878, 100.0)
        assert result["elev_error"] == 0.0


# ---------------------------------------------------------------------------
# transform_coordinates
# ---------------------------------------------------------------------------


class TestTransformCoordinates:
    """Tests for generic coordinate transformation."""

    def test_wgs84_to_utm(self) -> None:
        """Transform a point from WGS84 to UTM."""
        results = transform_coordinates(
            [(72.878, 19.076)],
            "EPSG:4326",
            "EPSG:32643",
        )
        assert len(results) == 1
        easting, northing = results[0]
        assert easting > 0
        assert northing > 0

    def test_utm_to_wgs84(self) -> None:
        """Transform a point from UTM to WGS84."""
        results = transform_coordinates(
            [(276720.9059, 2110588.4563)],
            "EPSG:32643",
            "EPSG:4326",
        )
        assert len(results) == 1
        lon, lat = results[0]
        assert abs(lat - 19.076) < 0.01
        assert abs(lon - 72.878) < 0.01

    def test_3d_points(self) -> None:
        """3D points should have Z preserved."""
        results = transform_coordinates(
            [(72.878, 19.076, 42.0)],
            "EPSG:4326",
            "EPSG:32643",
        )
        assert len(results) == 1
        assert len(results[0]) == 3
        assert results[0][2] == 42.0

    def test_multiple_points(self) -> None:
        """Transform multiple points."""
        points = [
            (72.878, 19.076),
            (72.880, 19.078),
        ]
        results = transform_coordinates(
            points, "EPSG:4326", "EPSG:32643"
        )
        assert len(results) == 2

    def test_invalid_points(self) -> None:
        """Points with wrong dimensions should raise."""
        with pytest.raises(ValueError, match="2D or 3D"):
            transform_coordinates(
                [(1.0, 2.0, 3.0, 4.0)],
                "EPSG:4326",
                "EPSG:32643",
            )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestCoordinateValidation:
    """Tests for coordinate validation."""

    def test_valid_latitude(self) -> None:
        validate_latitude(19.076)

    def test_valid_longitude(self) -> None:
        validate_longitude(72.878)

    def test_valid_coordinates(self) -> None:
        validate_coordinates(19.076, 72.878)

    def test_invalid_latitude_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_latitude(91.0)

    def test_invalid_latitude_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_latitude(-91.0)

    def test_invalid_longitude_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_longitude(181.0)

    def test_invalid_longitude_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_longitude(-181.0)

    def test_nan_latitude(self) -> None:
        with pytest.raises(ValueError, match="NaN"):
            validate_latitude(float("nan"))

    def test_inf_longitude(self) -> None:
        with pytest.raises(ValueError, match="Infinity"):
            validate_longitude(float("inf"))

    def test_non_numeric_latitude(self) -> None:
        with pytest.raises(TypeError, match="number"):
            validate_latitude("not_a_number")  # type: ignore

    def test_boundary_latitude(self) -> None:
        """Boundary values should be valid."""
        validate_latitude(90.0)
        validate_latitude(-90.0)

    def test_boundary_longitude(self) -> None:
        """Boundary values should be valid."""
        validate_longitude(180.0)
        validate_longitude(-180.0)
