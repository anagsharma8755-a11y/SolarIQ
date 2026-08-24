"""Geometry utilities for building footprint data.

Provides lightweight helpers for validating and computing
basic properties of building polygons without duplicating
the full analysis in ``backend.geometry``.
"""

from __future__ import annotations

import math
from typing import Sequence

from shapely.geometry import Polygon, mapping


def compute_footprint_area(
    coordinates: Sequence[tuple[float, float]],
) -> float:
    """Compute the area of a 2D polygon using Shapely.

    ``coordinates`` should be a list of (longitude, latitude) pairs
    forming a closed ring (first point == last point), or an open
    ring that Shapely will close.

    Returns area in square degrees (for geographic coordinates).
    Callers should transform to a projected CRS for square meters.
    """
    if len(coordinates) < 3:
        raise ValueError(
            "Polygon requires at least 3 coordinate pairs."
        )

    # Ensure the ring is closed.
    ring = list(coordinates)
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    try:
        polygon = Polygon(ring)
    except Exception as exc:
        raise ValueError(f"Invalid polygon geometry: {exc}") from exc

    if not polygon.is_valid:
        raise ValueError("Self-intersecting polygon geometry.")

    return float(polygon.area)


def compute_centroid(
    coordinates: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    """Compute the centroid of a 2D polygon.

    Returns (longitude, latitude) for geographic coordinates.
    """
    if len(coordinates) < 3:
        raise ValueError(
            "Polygon requires at least 3 coordinate pairs."
        )

    ring = list(coordinates)
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    try:
        polygon = Polygon(ring)
    except Exception as exc:
        raise ValueError(f"Invalid polygon geometry: {exc}") from exc

    centroid = polygon.centroid
    return (float(centroid.x), float(centroid.y))


def compute_bbox(
    coordinates: Sequence[tuple[float, float]],
) -> dict[str, float]:
    """Compute the bounding box of a set of coordinates.

    Returns a dict with min_lon, min_lat, max_lon, max_lat.
    """
    if not coordinates:
        raise ValueError("Cannot compute bounding box of empty set.")

    lons = [float(c[0]) for c in coordinates]
    lats = [float(c[1]) for c in coordinates]

    return {
        "min_lon": min(lons),
        "min_lat": min(lats),
        "max_lon": max(lons),
        "max_lat": max(lats),
    }


def validate_polygon(
    coordinates: Sequence[tuple[float, float]],
) -> list[str]:
    """Validate a polygon's geometry, returning a list of error strings.

    An empty list means the polygon is valid.
    """
    errors: list[str] = []

    if len(coordinates) < 3:
        errors.append(
            f"Polygon has only {len(coordinates)} points; "
            "minimum is 3."
        )
        return errors

    # Check for NaN / Inf
    for i, coord in enumerate(coordinates):
        if math.isnan(coord[0]) or math.isinf(coord[0]):
            errors.append(f"Point {i} has invalid longitude: {coord[0]}")
        if math.isnan(coord[1]) or math.isinf(coord[1]):
            errors.append(f"Point {i} has invalid latitude: {coord[1]}")

    if errors:
        return errors

    ring = list(coordinates)
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    try:
        polygon = Polygon(ring)
    except Exception as exc:
        errors.append(f"Polygon construction failed: {exc}")
        return errors

    if not polygon.is_valid:
        errors.append("Polygon is self-intersecting or invalid.")

    return errors


def building_footprint_to_geojson(
    building_id: str,
    coordinates: Sequence[tuple[float, float]],
    properties: dict | None = None,
) -> dict:
    """Convert a building footprint to a GeoJSON Feature.

    Args:
        building_id: Unique identifier for the building.
        coordinates: List of (longitude, latitude) pairs.
        properties: Optional additional properties.

    Returns:
        A GeoJSON Feature dict.
    """
    ring = list(coordinates)
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    props = {"building_id": building_id}
    if properties:
        props.update(properties)

    return {
        "type": "Feature",
        "properties": props,
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    }
