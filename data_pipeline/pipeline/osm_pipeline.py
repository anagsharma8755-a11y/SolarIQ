"""OSM data pipeline.

Orchestrates the complete flow from raw OSM data
to a clean, standardized city dataset:
download -> validate -> normalize -> clean -> transform -> store
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from data_pipeline.config import DEFAULT_CITY_OUTPUT
from data_pipeline.geo.coordinates import latlon_to_utm, validate_coordinates
from data_pipeline.osm.cleaner import clean_osm_buildings
from data_pipeline.osm.converter import convert_osm_data
from data_pipeline.osm.parser import parse_osm_elements
from data_pipeline.schemas import ProcessingReport, ProcessingStep
from data_pipeline.validation import build_validation_result, validate_building

logger = logging.getLogger(__name__)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def process_osm_data(
    source_path: Path | str,
    output_path: Path | str | None = None,
    convert_to_utm: bool = True,
) -> ProcessingReport:
    """Run the complete OSM data pipeline.

    Steps:
    1. Load raw OSM data (JSON with 'elements' key)
    2. Parse elements into building footprints
    3. Clean and deduplicate
    4. Validate
    5. Transform coordinates to UTM
    6. Convert to standardized format
    7. Save output

    Args:
        source_path: Path to OSM Overpass JSON file.
        output_path: Where to save the processed city JSON.
        convert_to_utm: Whether to also output UTM coordinates.

    Returns:
        A ProcessingReport documenting all steps.
    """
    source = Path(source_path)
    out = Path(output_path) if output_path else DEFAULT_CITY_OUTPUT

    steps: list[ProcessingStep] = []

    # --- Step 1: Load ---
    logger.info("[STEP 1] Loading OSM data from %s", source.name)
    try:
        with source.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
        elements = raw_data.get("elements", [])
        steps.append(ProcessingStep(
            step="load",
            status="success",
            records_in=0,
            records_out=len(elements),
            details=f"Loaded {len(elements)} OSM elements from {source.name}",
        ))
    except Exception as exc:
        steps.append(ProcessingStep(
            step="load", status="error",
            records_in=0, records_out=0,
            details=f"Failed to load: {exc}",
        ))
        return ProcessingReport(
            pipeline="osm", source=str(source),
            status="error", steps=steps,
        )

    # --- Step 2: Parse ---
    logger.info("[STEP 2] Parsing OSM elements...")
    parsed = parse_osm_elements(raw_data)
    steps.append(ProcessingStep(
        step="parse",
        status="success",
        records_in=len(elements),
        records_out=len(parsed),
        details=f"Parsed {len(parsed)} buildings from OSM elements",
    ))

    # --- Step 3: Clean ---
    logger.info("[STEP 3] Cleaning building data...")
    cleaned, clean_report = clean_osm_buildings(parsed)
    steps.append(ProcessingStep(
        step="clean",
        status="success",
        records_in=clean_report["total_input"],
        records_out=clean_report["cleaned_count"],
        details=(
            f"Removed {clean_report['removed_no_coordinates']} no-coords, "
            f"{clean_report['removed_invalid_geometry']} invalid-geom, "
            f"{clean_report['removed_duplicates']} duplicates"
        ),
    ))

    # --- Step 4: Validate ---
    logger.info("[STEP 4] Validating building data...")
    # Convert to standardized format for validation
    city_data, conv_report = convert_osm_data(cleaned)
    validation_errors = []
    valid_buildings = []
    for idx, b in enumerate(city_data["buildings"]):
        errs = validate_building(b, idx)
        if not errs:
            valid_buildings.append(b)
        else:
            validation_errors.extend(errs)

    validation_result = build_validation_result(
        len(city_data["buildings"]), validation_errors,
    )
    steps.append(ProcessingStep(
        step="validate",
        status="success" if validation_result.valid else "warning",
        records_in=len(city_data["buildings"]),
        records_out=len(valid_buildings),
        details=f"Valid: {validation_result.records_valid}, Invalid: {validation_result.records_invalid}",
    ))

    # --- Step 5: Transform coordinates ---
    logger.info("[STEP 5] Transforming coordinates...")
    utm_count = 0
    if convert_to_utm:
        for building in valid_buildings:
            coords = building.get("coordinates")
            if coords:
                try:
                    validate_coordinates(coords["latitude"], coords["longitude"])
                    easting, northing, _, zone, hemi = latlon_to_utm(
                        coords["latitude"], coords["longitude"],
                    )
                    building["utm"] = {
                        "easting": round(easting, 4),
                        "northing": round(northing, 4),
                        "zone": zone,
                        "hemisphere": hemi,
                    }
                    utm_count += 1
                except (ValueError, TypeError) as exc:
                    logger.warning("UTM conversion failed for %s: %s", building.get("building_id"), exc)

    steps.append(ProcessingStep(
        step="transform_coordinates",
        status="success",
        records_in=len(valid_buildings),
        records_out=utm_count,
        details=f"Converted {utm_count} buildings to UTM",
    ))

    # --- Step 6: Save ---
    logger.info("[STEP 6] Saving processed data...")
    output_city = {
        "buildings": valid_buildings,
        "metadata": {
            "source_file": source.name,
            "building_count": len(valid_buildings),
            "source_hash": _compute_file_hash(source),
            "pipeline": "osm",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(output_city, f, indent=2, ensure_ascii=False)

    steps.append(ProcessingStep(
        step="save",
        status="success",
        records_in=len(valid_buildings),
        records_out=len(valid_buildings),
        details=f"Saved to {out}",
    ))

    logger.info("[DONE] OSM pipeline complete: %d buildings saved.", len(valid_buildings))

    return ProcessingReport(
        pipeline="osm",
        source=str(source),
        status="success",
        steps=steps,
        validation=validation_result,
    )
