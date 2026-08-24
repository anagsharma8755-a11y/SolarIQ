"""OSM data cleaner.

Removes duplicates, invalid geometries, missing IDs,
and normalizes building data into a consistent format.
"""

from __future__ import annotations

import logging
from typing import Any

from shapely.geometry import Polygon

logger = logging.getLogger(__name__)


def _compute_centroid(
    coordinates: list[tuple[float, float]],
) -> tuple[float, float]:
    """Compute the centroid of a coordinate list."""
    if not coordinates:
        return (0.0, 0.0)
    n = len(coordinates)
    return (
        sum(c[0] for c in coordinates) / n,
        sum(c[1] for c in coordinates) / n,
    )


def _is_valid_polygon(
    coordinates: list[tuple[float, float]],
) -> bool:
    """Check if a coordinate list forms a valid polygon."""
    if len(coordinates) < 3:
        return False

    try:
        ring = list(coordinates)
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        polygon = Polygon(ring)
        return polygon.is_valid and polygon.area > 0
    except Exception:
        return False


def _deduplicate_by_location(
    buildings: list[dict[str, Any]],
    tolerance: float = 1e-6,
) -> list[dict[str, Any]]:
    """Remove buildings that are at the same location.

    Keeps the building with more coordinates (larger polygon).
    """
    seen: dict[tuple[int, int], dict[str, Any]] = {}

    result: list[dict[str, Any]] = []

    for building in buildings:
        coords = building.get("coordinates", [])
        if not coords:
            continue

        centroid = _compute_centroid(coords)
        # Quantize to tolerance for grouping
        key = (
            int(round(centroid[0] / tolerance)),
            int(round(centroid[1] / tolerance)),
        )

        if key in seen:
            existing = seen[key]
            if len(coords) > len(existing.get("coordinates", [])):
                result = [b for b in result if b is not existing]
                seen[key] = building
                result.append(building)
            # else skip this duplicate
        else:
            seen[key] = building
            result.append(building)

    removed = len(buildings) - len(result)
    if removed > 0:
        logger.info("Removed %d duplicate buildings.", removed)

    return result


def _generate_building_id(
    index: int,
    osm_id: Any | None = None,
) -> str:
    """Generate a normalized building ID."""
    if osm_id is not None:
        return f"B{index:04d}-OSM{osm_id}"
    return f"B{index:04d}"


def clean_osm_buildings(
    buildings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Clean a list of parsed OSM buildings.

    Steps:
    1. Remove buildings with no coordinates
    2. Remove buildings with invalid polygons
    3. Remove duplicate buildings by location
    4. Normalize building IDs

    Args:
        buildings: List of parsed OSM building dicts.

    Returns:
        Tuple of (cleaned buildings, cleaning report).
    """
    total_input = len(buildings)
    report: dict[str, Any] = {
        "total_input": total_input,
        "removed_no_coordinates": 0,
        "removed_invalid_geometry": 0,
        "removed_duplicates": 0,
        "cleaned_count": 0,
    }

    # Step 1: Remove buildings with no coordinates
    with_coords = []
    for b in buildings:
        coords = b.get("coordinates", [])
        if coords:
            with_coords.append(b)
        else:
            report["removed_no_coordinates"] += 1

    # Step 2: Remove invalid geometries
    valid = []
    for b in with_coords:
        coords = b.get("coordinates", [])
        if _is_valid_polygon(coords):
            valid.append(b)
        else:
            report["removed_invalid_geometry"] += 1
            logger.warning(
                "Removing building with invalid geometry: %s",
                b.get("osm_id"),
            )

    # Step 3: Deduplicate by location
    unique = _deduplicate_by_location(valid)
    report["removed_duplicates"] = len(valid) - len(unique)

    # Step 4: Normalize IDs
    cleaned: list[dict[str, Any]] = []
    for idx, b in enumerate(unique, start=1):
        normalized = dict(b)
        normalized["building_id"] = _generate_building_id(
            idx, b.get("osm_id")
        )
        normalized["source"] = "osm"
        cleaned.append(normalized)

    report["cleaned_count"] = len(cleaned)

    logger.info(
        "Cleaning complete: %d → %d buildings.",
        total_input,
        len(cleaned),
    )

    return cleaned, report
