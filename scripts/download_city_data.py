#!/usr/bin/env python3
"""Download city data from OpenStreetMap.

Usage:
    python scripts/download_city_data.py

Downloads building data for a configurable bounding box
and saves it to data/external/.

Falls back gracefully if the network is unavailable.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.config import EXTERNAL_DATA_DIR, SAMPLE_CITY_DIR
from data_pipeline.osm.downloader import download_osm_buildings

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download city data from OpenStreetMap."
    )
    parser.add_argument(
        "--south",
        type=float,
        default=19.07,
        help="Southern boundary latitude (default: 19.07)",
    )
    parser.add_argument(
        "--west",
        type=float,
        default=72.87,
        help="Western boundary longitude (default: 72.87)",
    )
    parser.add_argument(
        "--north",
        type=float,
        default=19.09,
        help="Northern boundary latitude (default: 19.09)",
    )
    parser.add_argument(
        "--east",
        type=float,
        default=72.89,
        help="Eastern boundary longitude (default: 72.89)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: data/external/osm_buildings_raw.json)",
    )

    args = parser.parse_args()

    output_path = (
        Path(args.output)
        if args.output
        else EXTERNAL_DATA_DIR / "osm_buildings_raw.json"
    )

    print(f"[INFO] Bounding box: ({args.south}, {args.west}, {args.north}, {args.east})")
    print(f"[INFO] Output: {output_path}")

    try:
        data = download_osm_buildings(
            south=args.south,
            west=args.west,
            north=args.north,
            east=args.east,
            output_path=output_path,
        )
        elements = data.get("elements", [])
        print(f"[OK] Downloaded {len(elements)} OSM elements")
        print(f"[OK] Saved to {output_path}")

    except ConnectionError as exc:
        print(f"[WARN] Network unavailable: {exc}")
        print("[INFO] Falling back to sample city data...")

        # Copy sample data to external
        import shutil
        sample_file = SAMPLE_CITY_DIR / "mumbai_sample.geojson"
        if sample_file.exists():
            dest = EXTERNAL_DATA_DIR / "mumbai_sample.geojson"
            shutil.copy2(sample_file, dest)
            print(f"[OK] Copied sample data to {dest}")
        else:
            print("[ERROR] No sample data available.")
            sys.exit(1)


if __name__ == "__main__":
    main()
