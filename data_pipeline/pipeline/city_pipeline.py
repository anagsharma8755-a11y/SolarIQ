"""City data pipeline.

Orchestrates the complete flow from raw city/building data
to a clean, standardized dataset that the SolarIQ backend
can consume directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from data_pipeline.config import (
    DEFAULT_CITY_OUTPUT,
    PROCESSED_DATA_DIR,
)
from data_pipeline.geo.coordinates import (
    latlon_to_utm,
    validate_coordinates,
)
from data_pipeline.osm.cleaner import clean_osm_buildings
from data_pipeline.osm.converter import (
    convert_osm_data,
    osm_to_standardized_building,
)
from data_pipeline.osm.parser import parse_osm_elements
from data_pipeline.schemas import ProcessingReport, ProcessingStep
from data_pipeline.validation import build_validation_result, validate_building

logger = logging.getLogger(__name__)


def _load_geojson_file(
    file_path: Path,
) -> list[dict[str, Any]]:
    """Load a GeoJSON file and extract building features."""
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    buildings: list[dict[str, Any]] = []

    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        if geom_type == "Polygon" and coords:
            # GeoJSON Polygon coordinates are [[[lon, lat], ...]]
            footprint = coords[0]
            buildings.append(
                {
                    "osm_id": props.get("id", props.get("osm_id")),
                    "properties": {
                        "name": props.get("name"),
                        "building_type": props.get("building", "yes"),
                        "height": props.get("height"),
                    },
                    "coordinates": [
                        (c[0], c[1]) for c in footprint
                    ],
                }
            )

    return buildings


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for change detection."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def process_city_data(
    source_path: Path | str,
    output_path: Path | str | None = None,
    convert_to_utm: bool = True,
) -> ProcessingReport:
    """Run the complete city data pipeline.

    Args:
        source_path: Path to input file (GeoJSON or OSM JSON).
        output_path: Where to save the processed city JSON.
        convert_to_utm: Whether to also output UTM coordinates.

    Returns:
        A ProcessingReport with all steps documented.
    """
    source = Path(source_path)
    out = Path(output_path) if output_path else DEFAULT_CITY_OUTPUT

    steps: list[ProcessingStep] = []

    # ------------------------------------------------------------------
    # Step 1: Load raw data
    # ------------------------------------------------------------------
    logger.info("[STEP 1] Loading city data from %s", source.name)

    try:
        if source.suffix.lower() == ".geojson":
            raw_buildings = _load_geojson_file(source)
        elif source.suffix.lower() == ".json":
            # Check if it's OSM Overpass format or our city format
            with source.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if "elements" in data:
                # OSM Overpass format
                raw_buildings_parsed = parse_osm_elements(data)
                raw_buildings = raw_buildings_parsed
            elif "buildings" in data:
                # Already in our format
                raw_buildings = data["buildings"]
            else:
                raise ValueError(
                    "Unrecognized JSON format."
                )
        else:
            raise ValueError(
                f"Unsupported file format: {source.suffix}"
            )

        steps.append(
            ProcessingStep(
                step="load",
                status="success",
                records_in=0,
                records_out=len(raw_buildings),
                details=f"Loaded {len(raw_buildings)} buildings from {source.name}",
            )
        )
    except Exception as exc:
        steps.append(
            ProcessingStep(
                step="load",
                status="error",
                records_in=0,
                records_out=0,
                details=f"Failed to load: {exc}",
            )
        )
        return ProcessingReport(
            pipeline="city",
            source=str(source),
            status="error",
            steps=steps,
        )

    # ------------------------------------------------------------------
    # Step 2: Clean data
    # ------------------------------------------------------------------
    logger.info("[STEP 2] Cleaning building data...")

    if source.suffix.lower() == ".geojson":
        # For GeoJSON, we need to normalize first
        cleaned_buildings = []
        for b in raw_buildings:
            std = osm_to_standardized_building(b)
            cleaned_buildings.append(std)
        clean_report = {
            "input_count": len(raw_buildings),
            "output_count": len(cleaned_buildings),
        }
    else:
        # For OSM data, run the full cleaning pipeline
        cleaned_buildings, clean_report = clean_osm_buildings(
            raw_buildings
        )
        # Convert to standardized format
        city_data, conv_report = convert_osm_data(cleaned_buildings)
        cleaned_buildings = city_data["buildings"]

    steps.append(
        ProcessingStep(
            step="clean",
            status="success",
            records_in=clean_report.get("input_count", len(raw_buildings)),
            records_out=len(cleaned_buildings),
            details=f"Cleaned to {len(cleaned_buildings)} valid buildings",
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Validate
    # ------------------------------------------------------------------
    logger.info("[STEP 3] Validating building data...")

    validation_errors = []
    valid_buildings = []

    for idx, b in enumerate(cleaned_buildings):
        errs = validate_building(b, idx)
        if not errs:
            valid_buildings.append(b)
        else:
            validation_errors.extend(errs)

    validation_result = build_validation_result(
        len(cleaned_buildings),
        validation_errors,
    )

    steps.append(
        ProcessingStep(
            step="validate",
            status="success" if validation_result.valid else "warning",
            records_in=len(cleaned_buildings),
            records_out=len(valid_buildings),
            details=(
                f"Valid: {validation_result.records_valid}, "
                f"Invalid: {validation_result.records_invalid}"
            ),
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Transform coordinates
    # ------------------------------------------------------------------
    logger.info("[STEP 4] Transforming coordinates...")

    utm_count = 0
    if convert_to_utm:
        for building in valid_buildings:
            coords = building.get("coordinates")
            if coords:
                try:
                    validate_coordinates(
                        coords["latitude"],
                        coords["longitude"],
                    )
                    easting, northing, _, zone, hemi = latlon_to_utm(
                        coords["latitude"],
                        coords["longitude"],
                    )
                    building["utm"] = {
                        "easting": round(easting, 4),
                        "northing": round(northing, 4),
                        "zone": zone,
                        "hemisphere": hemi,
                    }
                    utm_count += 1
                except (ValueError, TypeError) as exc:
                    logger.warning(
                        "UTM conversion failed for %s: %s",
                        building.get("building_id"),
                        exc,
                    )

    steps.append(
        ProcessingStep(
            step="transform_coordinates",
            status="success",
            records_in=len(valid_buildings),
            records_out=utm_count,
            details=f"Converted {utm_count} buildings to UTM",
        )
    )

    # ------------------------------------------------------------------
    # Step 5: Save output
    # ------------------------------------------------------------------
    logger.info("[STEP 5] Saving processed data...")

    output_city = {
        "buildings": valid_buildings,
        "metadata": {
            "source_file": source.name,
            "building_count": len(valid_buildings),
            "source_hash": _compute_file_hash(source),
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        json.dump(output_city, f, indent=2, ensure_ascii=False)

    steps.append(
        ProcessingStep(
            step="save",
            status="success",
            records_in=len(valid_buildings),
            records_out=len(valid_buildings),
            details=f"Saved to {out.relative_to(out.parent.parent)}",
        )
    )

    logger.info(
        "[DONE] City pipeline complete: %d buildings saved.",
        len(valid_buildings),
    )

    return ProcessingReport(
        pipeline="city",
        source=str(source),
        status="success",
        steps=steps,
        validation=validation_result,
    )


def load_for_backend(
    processed_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Load processed city data in a format ready for the backend.

    This returns the ``buildings`` list that can be passed
    directly to ``backend.geometry.parser.load_city_from_file()``
    style processing.

    Args:
        processed_path: Path to the processed city JSON.
            Defaults to the standard output location.

    Returns:
        List of building dicts compatible with the backend.
    """
    path = Path(processed_path) if processed_path else DEFAULT_CITY_OUTPUT

    if not path.exists():
        raise FileNotFoundError(
            f"Processed city data not found: {path}. "
            "Run the city pipeline first."
        )

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
        data = json.load(f)

    buildings = data.get("buildings", [])

    # Strip pipeline-specific metadata to match backend format
    backend_buildings: list[dict[str, Any]] = []
    for b in buildings:
        backend_b: dict[str, Any] = {
            "building_id": b["building_id"],
            "surfaces": b["surfaces"],
        }
        if b.get("name"):
            backend_b["name"] = b["name"]

        backend_buildings.append(backend_b)

    return backend_buildings
