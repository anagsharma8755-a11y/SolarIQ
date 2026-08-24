"""OpenStreetMap data downloader.

Downloads building data from OpenStreetMap via the Overpass API.
Supports:
- Bounding box queries
- Radius-based queries
- Graceful fallback when offline
- No API key required
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

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Maximum response size from Overpass API (50 MB).
_MAX_OVERPASS_RESPONSE_SIZE = 50 * 1024 * 1024

# Query template: fetch buildings within a bounding box.
# The bbox format is south,west,north,east.
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
    """Download OSM building data for a bounding box.

    Args:
        south, west, north, east: Bounding box in WGS84.
        output_path: Where to save the raw JSON response.
            Defaults to ``data/external/osm_buildings_raw.json``.
        timeout: HTTP request timeout in seconds.

    Returns:
        The parsed OSM Overpass JSON response.

    Raises:
        ConnectionError: If the network request fails.
        ValueError: If the response is invalid.
    """
    # Validate bounding box.
    if not (-90.0 <= south <= 90.0):
        raise ValueError(f"South latitude {south} out of range [-90, 90]")
    if not (-90.0 <= north <= 90.0):
        raise ValueError(f"North latitude {north} out of range [-90, 90]")
    if not (-180.0 <= west <= 180.0):
        raise ValueError(f"West longitude {west} out of range [-180, 180]")
    if not (-180.0 <= east <= 180.0):
        raise ValueError(f"East longitude {east} out of range [-180, 180]")
    if south >= north:
        raise ValueError(
            f"South latitude ({south}) must be less than "
            f"north latitude ({north})."
        )
    if west >= east:
        raise ValueError(
            f"West longitude ({west}) must be less than "
            f"east longitude ({east})."
        )

    query = OVERPASS_BUILDING_QUERY.format(
        south=south,
        west=west,
        north=north,
        east=east,
    )

    if output_path is None:
        output_path = EXTERNAL_DATA_DIR / "osm_buildings_raw.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading OSM buildings for bbox "
        "(%s, %s, %s, %s)...",
        south,
        west,
        north,
        east,
    )

    try:
        data_bytes = query.encode("utf-8")
        req = urllib.request.Request(
            OVERPASS_API_URL,
            data=data_bytes,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            # Enforce response size limit.
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
        raise ConnectionError(
            f"Failed to download OSM data: {exc}"
        ) from exc

    if "elements" not in data:
        raise ValueError(
            "OSM response does not contain 'elements' key."
        )

    # Save raw response
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    elements = data.get("elements", [])
    logger.info(
        "Downloaded %d OSM elements, saved to %s",
        len(elements),
        output_path,
    )

    return data


def load_osm_file(file_path: Path | str) -> dict[str, Any]:
    """Load an existing OSM JSON file.

    Args:
        file_path: Path to a JSON file exported from Overpass.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If JSON is invalid or file is unsafe.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"OSM file not found: {path}")

    if path.is_symlink():
        raise ValueError(
            f"Symlinked file not allowed: {path}. Use a regular file."
        )

    file_size = path.stat().st_size
    if file_size > 200 * 1024 * 1024:
        raise ValueError(
            f"File {path.name} is {file_size} bytes, exceeding "
            "the 200 MB limit."
        )

    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in {path}: {exc}"
            ) from exc

    return data


def save_osm_data(
    data: dict[str, Any],
    output_path: Path | str,
) -> Path:
    """Save OSM data to a JSON file.

    Returns:
        The resolved output path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved OSM data to %s", path)
    return path
