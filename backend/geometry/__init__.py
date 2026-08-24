"""Backend geometry package.

Exposes the core calculation, surface extraction, LOD-2,
projection, and shading modules.
"""

from backend.geometry.calculations import (
    calculate_azimuth,
    calculate_bounding_box,
    calculate_centroid,
    calculate_normal,
    calculate_polygon_area,
    calculate_polygon_area_signed,
    calculate_tilt,
    classify_surface,
    is_degenerate_polygon,
    is_planar,
    is_reversed_winding,
    normalise_winding,
)
from backend.geometry.surfaces import extract_surfaces

__all__ = [
    "calculate_azimuth",
    "calculate_bounding_box",
    "calculate_centroid",
    "calculate_normal",
    "calculate_polygon_area",
    "calculate_polygon_area_signed",
    "calculate_tilt",
    "classify_surface",
    "extract_surfaces",
    "is_degenerate_polygon",
    "is_planar",
    "is_reversed_winding",
    "normalise_winding",
]
