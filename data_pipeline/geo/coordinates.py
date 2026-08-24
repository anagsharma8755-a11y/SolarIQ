"""Coordinate transformation utilities.

Supports:
- WGS84 (EPSG:4326) latitude/longitude
- UTM with automatic zone detection
- Arbitrary CRS transformations via pyproj
- Validation of coordinates
"""

from __future__ import annotations

import math
from typing import Sequence

import pyproj
from pyproj import CRS, Transformer

from data_pipeline.config import LATITUDE_MAX, LATITUDE_MIN, LONGITUDE_MAX, LONGITUDE_MIN


def validate_latitude(value: float) -> None:
    """Raise ValueError if latitude is out of valid range."""
    if not isinstance(value, (int, float)):
        raise TypeError("Latitude must be a number.")
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Latitude must not be NaN or Infinity.")
    if not (LATITUDE_MIN <= value <= LATITUDE_MAX):
        raise ValueError(
            f"Latitude {value} is out of range "
            f"[{LATITUDE_MIN}, {LATITUDE_MAX}]."
        )


def validate_longitude(value: float) -> None:
    """Raise ValueError if longitude is out of valid range."""
    if not isinstance(value, (int, float)):
        raise TypeError("Longitude must be a number.")
    if math.isnan(value) or math.isinf(value):
        raise ValueError("Longitude must not be NaN or Infinity.")
    if not (LONGITUDE_MIN <= value <= LONGITUDE_MAX):
        raise ValueError(
            f"Longitude {value} is out of range "
            f"[{LONGITUDE_MIN}, {LONGITUDE_MAX}]."
        )


def validate_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    """Validate both latitude and longitude."""
    validate_latitude(latitude)
    validate_longitude(longitude)


def get_utm_zone(longitude: float) -> int:
    """Return the UTM zone number for a given longitude.

    UTM zones span 6° of longitude, starting at 180°W as zone 1.

    Examples:
        >>> get_utm_zone(72.8777)
        43
        >>> get_utm_zone(-73.9857)
        18
    """
    validate_longitude(longitude)
    zone = int(math.floor((longitude + 180.0) / 6.0)) + 1
    return max(1, min(60, zone))


def get_utm_crs(latitude: float, longitude: float) -> CRS:
    """Return the pyproj CRS for the UTM zone containing this point.

    Automatically selects the correct hemisphere.
    """
    validate_coordinates(latitude, longitude)

    zone = get_utm_zone(longitude)

    if latitude >= 0:
        epsg = 32600 + zone  # Northern hemisphere
    else:
        epsg = 32700 + zone  # Southern hemisphere

    return CRS.from_epsg(epsg)


def latlon_to_utm(
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
) -> tuple[float, float, float, int, str]:
    """Convert WGS84 latitude/longitude to UTM coordinates.

    Returns:
        (easting, northing, elevation, zone, hemisphere)
        where hemisphere is "N" or "S".
    """
    validate_coordinates(latitude, longitude)

    zone = get_utm_zone(longitude)
    hemisphere = "N" if latitude >= 0 else "S"
    crs = get_utm_crs(latitude, longitude)

    transformer = Transformer.from_crs(
        CRS.from_epsg(4326),
        crs,
        always_xy=True,
    )

    easting, northing = transformer.transform(longitude, latitude)

    return (easting, northing, elevation, zone, hemisphere)


def utm_to_latlon(
    easting: float,
    northing: float,
    zone: int,
    hemisphere: str,
    elevation: float = 0.0,
) -> tuple[float, float, float]:
    """Convert UTM coordinates to WGS84 latitude/longitude.

    Args:
        easting: UTM easting in meters.
        northing: UTM northing in meters.
        zone: UTM zone number (1-60).
        hemisphere: "N" for northern, "S" for southern.
        elevation: Elevation in meters (passed through).

    Returns:
        (latitude, longitude, elevation) in WGS84.
    """
    if not isinstance(zone, int) or not (1 <= zone <= 60):
        raise ValueError(f"Invalid UTM zone: {zone}")

    h = hemisphere.upper()
    if h not in ("N", "S"):
        raise ValueError(
            f"Invalid hemisphere: {hemisphere}. Must be 'N' or 'S'."
        )

    if h == "N":
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    source_crs = CRS.from_epsg(epsg)
    target_crs = CRS.from_epsg(4326)

    transformer = Transformer.from_crs(
        source_crs,
        target_crs,
        always_xy=True,
    )

    lon, lat = transformer.transform(easting, northing)

    return (lat, lon, elevation)


def transform_coordinates(
    points: Sequence[tuple[float, float] | Sequence[float]],
    source_crs: str | CRS,
    target_crs: str | CRS,
) -> list[tuple[float, ...]]:
    """Transform a list of 2D or 3D points between CRS.

    Args:
        points: List of (x, y) or (x, y, z) tuples.
        source_crs: Source CRS as string (e.g. "EPSG:4326") or pyproj CRS.
        target_crs: Target CRS as string or pyproj CRS.

    Returns:
        List of transformed (x, y) or (x, y, z) tuples.
    """
    if isinstance(source_crs, str):
        source_crs = CRS.from_user_input(source_crs)
    if isinstance(target_crs, str):
        target_crs = CRS.from_user_input(target_crs)

    always_xy = True
    transformer = Transformer.from_crs(
        source_crs,
        target_crs,
        always_xy=always_xy,
    )

    results: list[tuple[float, ...]] = []

    for point in points:
        x, y = float(point[0]), float(point[1])

        if len(point) == 3:
            z = float(point[2])
            # pyproj doesn't handle Z well for all CRS, so we transform
            # x,y and pass z through.
            new_x, new_y = transformer.transform(x, y)
            results.append((new_x, new_y, z))
        elif len(point) == 2:
            new_x, new_y = transformer.transform(x, y)
            results.append((new_x, new_y))
        else:
            raise ValueError(
                f"Points must be 2D or 3D, got {len(point)}D."
            )

    return results


def round_trip_accuracy(
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
) -> dict[str, float]:
    """Verify round-trip accuracy: WGS84 → UTM → WGS84.

    Returns a dict with the original and recovered coordinates
    plus the errors in latitude, longitude, and elevation.
    """
    validate_coordinates(latitude, longitude)

    easting, northing, elev, zone, hemi = latlon_to_utm(
        latitude, longitude, elevation
    )
    lat2, lon2, elev2 = utm_to_latlon(
        easting, northing, zone, hemi, elevation
    )

    return {
        "original_lat": latitude,
        "original_lon": longitude,
        "recovered_lat": lat2,
        "recovered_lon": lon2,
        "lat_error": abs(lat2 - latitude),
        "lon_error": abs(lon2 - longitude),
        "elev_error": abs(elev2 - elevation),
    }
