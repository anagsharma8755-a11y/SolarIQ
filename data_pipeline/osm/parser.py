"""OSM data parser.

Converts raw Overpass JSON elements into building structures.
Handles way and relation elements, resolves nodes, and
constructs building footprints with coordinates.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _build_node_lookup(
    elements: list[dict[str, Any]],
) -> dict[int, tuple[float, float]]:
    """Build a lookup table of node IDs to (lon, lat) coordinates."""
    nodes: dict[int, tuple[float, float]] = {}
    for elem in elements:
        if elem.get("type") == "node":
            nid = elem.get("id")
            lon = elem.get("lon")
            lat = elem.get("lat")
            if nid is not None and lon is not None and lat is not None:
                nodes[nid] = (float(lon), float(lat))
    return nodes


def _extract_way_coordinates(
    way: dict[str, Any],
    node_lookup: dict[int, tuple[float, float]],
) -> list[tuple[float, float]]:
    """Extract ordered coordinates for a way from its node references."""
    node_refs = way.get("nodes", [])
    coordinates: list[tuple[float, float]] = []

    for nid in node_refs:
        if nid in node_lookup:
            coordinates.append(node_lookup[nid])
        else:
            logger.warning(
                "Node %s referenced by way %s not found.",
                nid,
                way.get("id"),
            )

    return coordinates


def _extract_building_properties(
    element: dict[str, Any],
) -> dict[str, Any]:
    """Extract useful properties from an OSM element."""
    tags = element.get("tags", {})
    props: dict[str, Any] = {}

    # Name
    if tags.get("name"):
        props["name"] = tags["name"]

    # Building type
    building_type = tags.get("building", "yes")
    if building_type != "yes":
        props["building_type"] = building_type

    # Height
    height_str = tags.get("height")
    if height_str:
        try:
            # Handle "30m", "30.5", etc.
            numeric = height_str.replace("m", "").replace("M", "").strip()
            props["height"] = float(numeric)
        except (ValueError, TypeError):
            pass

    # Levels
    levels_str = tags.get("building:levels")
    if levels_str:
        try:
            props["levels"] = int(levels_str)
        except (ValueError, TypeError):
            pass

    # Area
    area_str = tags.get("area")
    if area_str:
        try:
            props["area"] = float(area_str)
        except (ValueError, TypeError):
            pass

    return props


def parse_osm_elements(
    osm_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse raw Overpass JSON into a list of building dicts.

    Each building dict has:
    - osm_id: The OSM element ID
    - properties: Extracted tags (name, height, etc.)
    - coordinates: List of (lon, lat) pairs for the footprint
    - element_type: "way" or "relation"

    Args:
        osm_data: Raw Overpass JSON with 'elements' key.

    Returns:
        List of parsed building dicts.
    """
    elements = osm_data.get("elements", [])

    if not elements:
        logger.warning("No OSM elements to parse.")
        return []

    node_lookup = _build_node_lookup(elements)

    buildings: list[dict[str, Any]] = []
    processed_ids: set[int] = set()

    for elem in elements:
        elem_type = elem.get("type")

        if elem_type not in ("way", "relation"):
            continue

        osm_id = elem.get("id")
        if osm_id in processed_ids:
            continue

        # Only process buildings
        tags = elem.get("tags", {})
        if "building" not in tags:
            continue

        coords = _extract_way_coordinates(elem, node_lookup)

        if len(coords) < 3:
            logger.warning(
                "OSM %s %s has only %d points; skipping.",
                elem_type,
                osm_id,
                len(coords),
            )
            continue

        props = _extract_building_properties(elem)

        buildings.append(
            {
                "osm_id": osm_id,
                "element_type": elem_type,
                "properties": props,
                "coordinates": coords,
            }
        )
        processed_ids.add(osm_id)

    logger.info(
        "Parsed %d buildings from %d OSM elements.",
        len(buildings),
        len(elements),
    )

    return buildings
