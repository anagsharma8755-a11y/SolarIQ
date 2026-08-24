"""Geospatial projection helpers for 3D building geometry.

Supports:
- WGS84 (EPSG:4326) latitude/longitude
- UTM projected CRS with automatic zone detection
- Area calculations in projected (metric) coordinate systems
- CRS metadata preservation throughout the pipeline

Key distinction:
- Input vertices may be in geographic coordinates (degrees) or
  projected coordinates (metres).
- Area calculations MUST be performed in a projected CRS to
  obtain square metres.  Computing area in degree-based
  coordinates yields square degrees, which is meaningless for
  solar panel sizing.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
import pyproj
from pyproj import CRS, Transformer

from backend.geometry.calculations import Vector3, _to_array


# ---------------------------------------------------------------------------
# CRS detection
# ---------------------------------------------------------------------------


def get_utm_zone(longitude: float) -> int:
    """Return the UTM zone number for a given longitude.

    UTM zones span 6 degrees of longitude, starting at 180W
    as zone 1.

    Examples:
        >>> get_utm_zone(72.8777)  # Mumbai
        43
        >>> get_utm_zone(-73.9857)  # New York
        18
    """
    zone = int(math.floor((longitude + 180.0) / 6.0)) + 1
    return max(1, min(60, zone))


def get_utm_epsg(latitude: float, longitude: float) -> int:
    """Return the EPSG code for the UTM zone containing this point.

    Automatically selects the correct hemisphere.
    """
    zone = get_utm_zone(longitude)
    if latitude >= 0:
        return 32600 + zone
    return 32700 + zone


def get_utm_crs(latitude: float, longitude: float) -> CRS:
    """Return the pyproj CRS for the UTM zone of this point."""
    epsg = get_utm_epsg(latitude, longitude)
    return CRS.from_epsg(epsg)


# ---------------------------------------------------------------------------
# Coordinate transformation
# ---------------------------------------------------------------------------


def vertices_to_utm(
    vertices: Sequence[Vector3],
    latitude: float,
    longitude: float,
) -> list[list[float]]:
    """Transform 3D vertices from WGS84 to UTM.

    The latitude and longitude define the UTM zone.  The Z
    coordinate (height) is passed through unchanged.

    Args:
        vertices: List of [x, y, z] where x=lon, y=lat, z=elev
                  (in degrees + metres).
        latitude: Reference latitude for UTM zone selection.
        longitude: Reference longitude for UTM zone selection.

    Returns:
        List of [easting, northing, elevation] in metres.
    """
    epsg = get_utm_epsg(latitude, longitude)
    crs_wgs84 = CRS.from_epsg(4326)
    crs_utm = CRS.from_epsg(epsg)

    transformer = Transformer.from_crs(
        crs_wgs84, crs_utm, always_xy=True,
    )

    result = []
    for v in vertices:
        arr = _to_array(v)
        easting, northing = transformer.transform(arr[0], arr[1])
        result.append([float(easting), float(northing), float(arr[2])])

    return result


def vertices_to_wgs84(
    vertices: Sequence[Vector3],
    latitude: float,
    longitude: float,
) -> list[list[float]]:
    """Transform 3D vertices from UTM to WGS84.

    The latitude and longitude define the source UTM zone.
    The Z coordinate (height) is passed through unchanged.
    """
    epsg = get_utm_epsg(latitude, longitude)
    crs_utm = CRS.from_epsg(epsg)
    crs_wgs84 = CRS.from_epsg(4326)

    transformer = Transformer.from_crs(
        crs_utm, crs_wgs84, always_xy=True,
    )

    result = []
    for v in vertices:
        arr = _to_array(v)
        lon, lat = transformer.transform(arr[0], arr[1])
        result.append([float(lon), float(lat), float(arr[2])])

    return result


# ---------------------------------------------------------------------------
# Area in projected CRS
# ---------------------------------------------------------------------------


def calculate_area_in_m2(
    vertices: Sequence[Vector3],
    latitude: float | None = None,
    longitude: float | None = None,
) -> float:
    """Calculate surface area in square metres.

    If *latitude* and *longitude* are provided, the vertices
    are assumed to be in WGS84 (degrees) and are projected
    to the appropriate UTM zone before computing area.

    If coordinates are None, the vertices are assumed to
    already be in a metric projected CRS (e.g. UTM) and
    area is computed directly.

    Units:
        Input vertices in degrees -> UTM projection -> m^2
        Input vertices in metres  -> direct computation -> m^2
    """
    from backend.geometry.calculations import calculate_polygon_area

    if latitude is not None and longitude is not None:
        utm_vertices = vertices_to_utm(vertices, latitude, longitude)
        return calculate_polygon_area(utm_vertices)

    return calculate_polygon_area(vertices)


# ---------------------------------------------------------------------------
# CRS metadata
# ---------------------------------------------------------------------------


def make_crs_metadata(
    latitude: float | None = None,
    longitude: float | None = None,
    source_crs: str = "EPSG:4326",
) -> dict[str, Any]:
    """Build a CRS metadata dict for embedding in analysis results.

    Returns:
        A dict with source_crs, projected_crs, utm_zone,
        hemisphere, and projection_description.
    """
    meta: dict[str, Any] = {
        "source_crs": source_crs,
        "projected_crs": None,
        "utm_zone": None,
        "hemisphere": None,
        "projection_description": "Geographic coordinates (degrees)",
    }

    if latitude is not None and longitude is not None:
        epsg = get_utm_epsg(latitude, longitude)
        zone = get_utm_zone(longitude)
        hemisphere = "N" if latitude >= 0 else "S"

        meta["projected_crs"] = f"EPSG:{epsg}"
        meta["utm_zone"] = zone
        meta["hemisphere"] = hemisphere
        meta["projection_description"] = (
            f"UTM Zone {zone}{hemisphere} (EPSG:{epsg}) "
            f"- projected coordinates in metres"
        )

    return meta


# ---------------------------------------------------------------------------
# Geospatial surface metadata
# ---------------------------------------------------------------------------


def enrich_surface_metadata(
    surface_data: dict[str, Any],
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """Add CRS-aware geospatial metadata to a surface dict.

    This function enriches the output of extract_surfaces()
    with:
    - CRS information
    - Projected area (in m^2) when geographic coords are given
    - Source coordinate system documentation

    Does not modify existing fields.
    """
    enriched = dict(surface_data)
    enriched["crs"] = make_crs_metadata(latitude, longitude)

    if latitude is not None and longitude is not None:
        verts = surface_data.get("vertices", [])
        if verts:
            enriched["projected_area_m2"] = round(
                calculate_area_in_m2(verts, latitude, longitude), 4
            )

    return enriched
