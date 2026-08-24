"""OSM GeoJSON loader.

Supports loading building data from:
- GeoJSON files (local)
- OSM Overpass API (with bbox queries)
- OSM JSON format

Uses Mumbai as the demonstration region.
All network operations have graceful fallback for offline mode.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from data_pipeline.config import EXTERNAL_DATA_DIR

logger = logging.getLogger(__name__)

# Mumbai bounding box (south, west, north, east)
MUMBAI_BBOX = (18.88, 72.75, 19.28, 72.98)

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Maximum response size from Overpass API (50 MB).
_MAX_OVERPASS_RESPONSE_SIZE = 50 * 1024 * 1024

# Maximum allowed local file size (200 MB).
_MAX_LOCAL_FILE_SIZE = 200 * 1024 * 1024

OVERPASS_BUILDING_QUERY = (
    '[out:json][timeout:30];'
    '('
    '  way["building"]({south},{west},{north},{east});'
    '  relation["building"]({south},{west},{north},{east});'
    ');'
    'out body;>;'
    'out skel qt;'
)


def download_osm_buildings(
    south: float,
    west: float,
    north: float,
    east: float,
    output_path: Path | str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Download OSM building data for a bounding box via Overpass API.

    Args:
        south, west, north, east: Bounding box in WGS84.
        output_path: Where to save the raw JSON response.
        timeout: HTTP request timeout in seconds.

    Returns:
        The parsed OSM Overpass JSON response.

    Raises:
        ConnectionError: If the network request fails.
        ValueError: If the response is invalid.
    """
    query = OVERPASS_BUILDING_QUERY.format(
        south=south, west=west, north=north, east=east,
    )

    if output_path is None:
        output_path = EXTERNAL_DATA_DIR / "osm_buildings_raw.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading OSM buildings for bbox (%s, %s, %s, %s)...",
        south, west, north, east,
    )

    try:
        data_bytes = query.encode("utf-8")
        req = urllib.request.Request(
            OVERPASS_API_URL,
            data=data_bytes,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            # Enforce response size limit to prevent memory exhaustion.
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > _MAX_OVERPASS_RESPONSE_SIZE:
                raise ConnectionError(
                    f"Response too large: {content_length} bytes. "
                    f"Limit: {_MAX_OVERPASS_RESPONSE_SIZE} bytes."
                )
            body = response.read(_MAX_OVERPASS_RESPONSE_SIZE + 1)
            if len(body) > _MAX_OVERPASS_RESPONSE_SIZE:
                raise ConnectionError(
                    f"Response exceeds {_MAX_OVERPASS_RESPONSE_SIZE} bytes."
                )
            data = json.loads(body.decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise ConnectionError(f"Failed to download OSM data: {exc}") from exc

    if "elements" not in data:
        raise ValueError("OSM response does not contain 'elements' key.")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "Downloaded %d OSM elements, saved to %s",
        len(data.get("elements", [])), output_path,
    )
    return data


def load_geojson_file(file_path: Path | str) -> dict[str, Any]:
    """Load a GeoJSON file containing building features.

    Returns a dict with 'features' key containing the GeoJSON features.

    Security: Rejects symlinked files and enforces size limits.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {path}")

    if path.is_symlink():
        raise ValueError(
            f"Symlinked file not allowed: {path}. "
            "Use a regular file."
        )

    file_size = path.stat().st_size
    if file_size > _MAX_LOCAL_FILE_SIZE:
        raise ValueError(
            f"File {path.name} is {file_size} bytes, exceeding "
            f"the {_MAX_LOCAL_FILE_SIZE} byte limit."
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "features" not in data:
        raise ValueError(f"GeoJSON file {path.name} missing 'features' key.")

    return data


def geojson_to_buildings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert GeoJSON features to building dicts.

    Each building dict has:
    - osm_id: from properties or generated
    - properties: extracted tags
    - coordinates: list of (lon, lat) pairs
    """
    features = data.get("features", [])
    buildings: list[dict[str, Any]] = []

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        if geom_type == "Polygon" and coords:
            footprint = coords[0]
            buildings.append({
                "osm_id": props.get("id", props.get("osm_id")),
                "properties": {
                    "name": props.get("name"),
                    "building_type": props.get("building", "yes"),
                    "height": props.get("height"),
                },
                "coordinates": [(c[0], c[1]) for c in footprint],
            })
        elif geom_type == "MultiPolygon" and coords:
            # Take the largest polygon
            largest = max(coords, key=lambda poly: len(poly[0]))
            footprint = largest[0]
            buildings.append({
                "osm_id": props.get("id", props.get("osm_id")),
                "properties": {
                    "name": props.get("name"),
                    "building_type": props.get("building", "yes"),
                    "height": props.get("height"),
                },
                "coordinates": [(c[0], c[1]) for c in footprint],
            })

    logger.info("Extracted %d buildings from GeoJSON.", len(buildings))
    return buildings


def load_osm_buildings(
    source: Path | str,
    bbox: tuple[float, float, float, float] | None = None,
    force_download: bool = False,
) -> list[dict[str, Any]]:
    """Load OSM buildings from a file or download via Overpass API.

    Args:
        source: Path to a GeoJSON/JSON file, or 'overpass' to download.
        bbox: Bounding box (south, west, north, east) for Overpass queries.
        force_download: Force re-download even if cached.

    Returns:
        List of building dicts with osm_id, properties, coordinates.
    """
    source_path = Path(source) if source != "overpass" else None

    if source_path and source_path.exists():
        # Load from file
        suffix = source_path.suffix.lower()
        if suffix == ".geojson":
            data = load_geojson_file(source_path)
            return geojson_to_buildings(data)
        elif suffix == ".json":
            with source_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "elements" in data:
                # OSM Overpass format - use parser
                from data_pipeline.osm.parser import parse_osm_elements
                return parse_osm_elements(data)
            elif "features" in data:
                return geojson_to_buildings(data)
            elif "buildings" in data:
                return data["buildings"]
            else:
                raise ValueError(f"Unrecognized JSON format in {source_path.name}")

    # Download from Overpass API
    effective_bbox = bbox or MUMBAI_BBOX
    cache_path = EXTERNAL_DATA_DIR / "osm_buildings_raw.json"

    if cache_path.exists() and not force_download:
        logger.info("Using cached OSM data from %s", cache_path)
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        try:
            data = download_osm_buildings(
                effective_bbox[0], effective_bbox[1],
                effective_bbox[2], effective_bbox[3],
            )
        except ConnectionError as exc:
            logger.warning("Network unavailable: %s", exc)
            raise

    from data_pipeline.osm.parser import parse_osm_elements
    return parse_osm_elements(data)
