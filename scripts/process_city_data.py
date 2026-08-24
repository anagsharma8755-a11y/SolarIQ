#!/usr/bin/env python3
"""Process city data through the SolarIQ data pipeline.

Usage:
    python scripts/process_city_data.py [--source PATH]

Processes building data from GeoJSON or OSM JSON format
and outputs standardized data compatible with the SolarIQ backend.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.config import DEFAULT_CITY_OUTPUT, SAMPLE_CITY_DIR
from data_pipeline.pipeline.city_pipeline import process_city_data

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process city data for SolarIQ."
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to city data file (GeoJSON or JSON). "
             "If not provided, uses sample data.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: data/processed/city_buildings.geojson)",
    )

    args = parser.parse_args()

    # Find source
    if args.source:
        source = Path(args.source)
    else:
        # Try sample data
        candidates = list(SAMPLE_CITY_DIR.glob("*.geojson")) + list(
            SAMPLE_CITY_DIR.glob("*.json")
        )
        if candidates:
            source = candidates[0]
            print(f"[INFO] Using sample data: {source.name}")
        else:
            print("[ERROR] No source data found.")
            print("[INFO] Run: python scripts/download_city_data.py")
            sys.exit(1)

    if not source.exists():
        print(f"[ERROR] Source file not found: {source}")
        sys.exit(1)

    output = Path(args.output) if args.output else DEFAULT_CITY_OUTPUT

    print(f"[INFO] Source: {source}")
    print(f"[INFO] Output: {output}")

    report = process_city_data(source, output)

    # Print report
    print()
    print("=" * 50)
    print("  CITY PIPELINE REPORT")
    print("=" * 50)

    for step in report.steps:
        status_icon = "OK" if step.status == "success" else "FAIL"
        print(f"  [{status_icon}] {step.step}: {step.details}")

    if report.validation:
        print()
        print(f"  Validation: {report.validation.records_valid} valid, "
              f"{report.validation.records_invalid} invalid")

    print()
    print(f"  Output: {output}")
    print(f"  Status: {report.status}")
    print("=" * 50)


if __name__ == "__main__":
    main()
