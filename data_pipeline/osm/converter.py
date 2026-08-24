"""OSM data converter.

Converts cleaned OSM buildings into SolarIQ's standardized
building format, generating LOD-1 building geometry from
footprint coordinates and height information.
"""

from __future__ import annotations

import logging
from typing import Any

from data_pipeline.geo.geometry import compute_centroid

logger = logging.getLogger(__name__)

# Default building height if not available from OSM
DEFAULT_BUILDING_HEIGHT_M = 15.0


def _generate_box_surfaces(
    coordinates: list[tuple[float, float]],
    height: float,
    building_id: str,
) -> list[dict[str, Any]]:
    """Generate LOD-1 box building surfaces from a footprint.

    Creates a simple extruded box with:
    - Roof (top polygon)
    - Facades (one per footprint edge)
    - Ground (bottom polygon)

    The coordinate system is local: origin at the first
    footprint point, X = east, Y = north, Z = up.
    """
    # Compute a local origin (first point)
    origin_lon, origin_lat = coordinates[0]

    # Convert footprint to local XY coordinates
    # Simple approximation: 1 degree longitude ≈ cos(lat) * 111 km
    import math
    cos_lat = math.cos(math.radians(origin_lat))
    local_xy = []
    for lon, lat in coordinates:
        x = (lon - origin_lon) * cos_lat * 111320.0
        y = (lat - origin_lat) * 110540.0
        local_xy.append([round(x, 4), round(y, 4)])

    # Close the ring if needed
    if local_xy[0] != local_xy[-1]:
        local_xy.append(local_xy[0])

    n_points = len(local_xy) - 1  # exclude duplicate closing point
    surfaces: list[dict[str, Any]] = []
    surface_counter = 1

    # --- Roof surface (top polygon) ---
    roof_verts = [[xy[0], xy[1], round(height, 4)] for xy in local_xy[:-1]]
    surfaces.append(
        {
            "surface_id": f"{building_id}-S{surface_counter:03d}",
            "vertices": roof_verts,
        }
    )
    surface_counter += 1

    # --- Facade surfaces (one per edge) ---
    for i in range(n_points):
        j = (i + 1) % n_points
        p0 = local_xy[i]
        p1 = local_xy[j]

        facade_verts = [
            [p0[0], p0[1], 0.0],
            [p1[0], p1[1], 0.0],
            [p1[0], p1[1], round(height, 4)],
            [p0[0], p0[1], round(height, 4)],
        ]
        surfaces.append(
            {
                "surface_id": f"{building_id}-S{surface_counter:03d}",
                "vertices": facade_verts,
            }
        )
        surface_counter += 1

    # --- Ground surface (bottom polygon) ---
    ground_verts = [[xy[0], xy[1], 0.0] for xy in local_xy[:-1]]
    surfaces.append(
        {
            "surface_id": f"{building_id}-S{surface_counter:03d}",
            "vertices": ground_verts,
        }
    )

    return surfaces


def osm_to_standardized_building(
    building: dict[str, Any],
    building_id: str | None = None,
) -> dict[str, Any]:
    """Convert a cleaned OSM building to the standardized format.

    Args:
        building: Cleaned OSM building dict from the cleaner.
        building_id: Optional override for the building ID.

    Returns:
        A standardized building dict compatible with the
        SolarIQ backend parser.
    """
    bid = building_id or building.get("building_id", "UNKNOWN")
    coordinates = building.get("coordinates", [])
    props = building.get("properties", {})

    # Compute centroid
    centroid = compute_centroid(coordinates)

    # Determine building height
    height = props.get("height", DEFAULT_BUILDING_HEIGHT_M)

    # Generate surfaces
    surfaces = _generate_box_surfaces(coordinates, height, bid)

    standardized: dict[str, Any] = {
        "building_id": bid,
        "name": props.get("name", f"Building {bid}"),
        "source": "osm",
        "coordinates": {
            "latitude": round(centroid[1], 6),
            "longitude": round(centroid[0], 6),
        },
        "crs": "EPSG:4326",
        "surfaces": surfaces,
        "metadata": {
            "osm_id": building.get("osm_id"),
            "height_m": height,
            "building_type": props.get("building_type", "yes"),
        },
    }

    return standardized


def osm_to_city_json(
    buildings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert a list of cleaned OSM buildings to city JSON format.

    Returns:
        A city dict with a "buildings" list, compatible with
        ``backend.geometry.parser.load_city_from_file()``.
    """
    standardized = [
        osm_to_standardized_building(b) for b in buildings
    ]

    return {"buildings": standardized}


def convert_osm_data(
    cleaned_buildings: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Full conversion pipeline: cleaned OSM → standardized city.

    Returns:
        (city_data, conversion_report)
    """
    report: dict[str, Any] = {
        "input_count": len(cleaned_buildings),
        "output_count": 0,
        "total_surfaces": 0,
        "conversions_successful": 0,
        "conversions_failed": 0,
    }

    standardized_list: list[dict[str, Any]] = []

    for b in cleaned_buildings:
        try:
            std = osm_to_standardized_building(b)
            standardized_list.append(std)
            report["conversions_successful"] += 1
            report["total_surfaces"] += len(std["surfaces"])
        except Exception as exc:
            logger.warning(
                "Failed to convert building %s: %s",
                b.get("building_id"),
                exc,
            )
            report["conversions_failed"] += 1

    city_data = {"buildings": standardized_list}
    report["output_count"] = len(standardized_list)

    logger.info(
        "Conversion complete: %d buildings, %d total surfaces.",
        report["output_count"],
        report["total_surfaces"],
    )

    return city_data, report
