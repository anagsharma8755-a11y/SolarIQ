from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(
    file_path: str | Path,
) -> dict[str, Any]:
    """
    Load a JSON file and return its contents.

    The MVP uses JSON as the internal representation of
    LOD-1 building geometry.

    Future parsers for CityGML, OBJ and GeoJSON can convert
    their input into the same internal structure.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {path}"
        )

    # Reject symlinks to prevent symlink-based attacks.
    if path.is_symlink():
        raise ValueError(
            f"Symlinked file not allowed: {path}. "
            "Use a regular file within MODEL_DIR or DATA_DIR."
        )

    # Check file size (100 MB limit for geometry files).
    file_size = path.stat().st_size
    if file_size > 100 * 1024 * 1024:
        raise ValueError(
            f"File {path.name} is {file_size} bytes, exceeding "
            "the 100 MB limit for geometry files."
        )

    if path.suffix.lower() != ".json":
        raise ValueError(
            "The MVP geometry parser currently supports JSON files only."
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON file: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Root JSON structure must be an object."
        )

    return data


def load_building_from_file(
    file_path: str | Path,
) -> dict[str, Any]:
    """
    Load one building from a JSON file.

    Expected structure:

    {
        "building_id": "B001",
        "surfaces": [...]
    }
    """

    data = load_json_file(file_path)

    if "building_id" not in data:
        raise ValueError(
            "Building data must contain 'building_id'."
        )

    if "surfaces" not in data:
        raise ValueError(
            "Building data must contain 'surfaces'."
        )

    if not isinstance(data["surfaces"], list):
        raise ValueError(
            "'surfaces' must be a list."
        )

    return data


def load_city_from_file(
    file_path: str | Path,
) -> list[dict[str, Any]]:
    """
    Load multiple buildings from a JSON city file.

    Expected structure:

    {
        "buildings": [
            {
                "building_id": "B001",
                "surfaces": [...]
            }
        ]
    }
    """

    data = load_json_file(file_path)

    buildings = data.get("buildings")

    if not isinstance(buildings, list):
        raise ValueError(
            "City data must contain a 'buildings' list."
        )

    for index, building in enumerate(
        buildings,
        start=1,
    ):
        if not isinstance(building, dict):
            raise ValueError(
                f"Building {index} must be a JSON object."
            )

        if not building.get("building_id"):
            raise ValueError(
                f"Building {index} is missing 'building_id'."
            )

        if not isinstance(
            building.get("surfaces"),
            list,
        ):
            raise ValueError(
                f"Building {building.get('building_id', index)} "
                "must contain a surfaces list."
            )

    return buildings