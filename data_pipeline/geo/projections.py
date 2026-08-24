"""Projection helpers for common geospatial transformations.

Provides a simplified interface over pyproj for
CRS detection, creation, and coordinate re-projection.
"""

from __future__ import annotations

from typing import Sequence

import pyproj
from pyproj import CRS, Transformer

from data_pipeline.geo.coordinates import (
    get_utm_crs,
    get_utm_zone,
    validate_coordinates,
)


def detect_crs(crs_input: str | CRS) -> CRS:
    """Accept a CRS string or object and return a pyproj CRS."""
    if isinstance(crs_input, CRS):
        return crs_input
    return CRS.from_user_input(crs_input)


def auto_utm_crs_for_points(
    points: Sequence[Sequence[float]],
) -> CRS:
    """Detect the best-fit UTM CRS for a set of points.

    Points must be in (longitude, latitude) order (standard for
    geographic data in pyproj when always_xy=True).
    """
    if not points:
        raise ValueError("Cannot detect UTM CRS for empty point set.")

    lons = [float(p[0]) for p in points]
    lats = [float(p[1]) for p in points]

    mean_lon = sum(lons) / len(lons)
    mean_lat = sum(lats) / len(lats)

    return get_utm_crs(mean_lat, mean_lon)


def project_points(
    points: Sequence[Sequence[float]],
    source_crs: str | CRS,
    target_crs: str | CRS,
) -> list[tuple[float, ...]]:
    """Project a list of (x, y) or (x, y, z) points.

    Uses ``always_xy=True`` so that source CRS is treated as
    (longitude, latitude) for geographic systems.
    """
    src = detect_crs(source_crs)
    tgt = detect_crs(target_crs)

    transformer = Transformer.from_crs(src, tgt, always_xy=True)

    results: list[tuple[float, ...]] = []
    for point in points:
        x, y = float(point[0]), float(point[1])
        new_x, new_y = transformer.transform(x, y)

        if len(point) >= 3:
            results.append((new_x, new_y, float(point[2])))
        else:
            results.append((new_x, new_y))

    return results


def get_epsg_for_utm(
    latitude: float,
    longitude: float,
) -> int:
    """Return the EPSG code for the UTM zone containing this point.

    Examples:
        >>> get_epsg_for_utm(19.076, 72.878)
        32643
    """
    validate_coordinates(latitude, longitude)
    zone = get_utm_zone(longitude)

    if latitude >= 0:
        return 32600 + zone
    return 32700 + zone


def utm_to_epsg(zone: int, hemisphere: str = "N") -> int:
    """Convert a UTM zone and hemisphere to an EPSG code."""
    h = hemisphere.upper()
    if h == "N":
        return 32600 + zone
    return 32700 + zone


def epsg_to_utm(epsg: int) -> tuple[int, str]:
    """Convert a UTM EPSG code to (zone, hemisphere)."""
    if 32601 <= epsg <= 32660:
        return (epsg - 32600, "N")
    if 32701 <= epsg <= 32760:
        return (epsg - 32700, "S")
    raise ValueError(f"EPSG {epsg} is not a valid UTM code.")
