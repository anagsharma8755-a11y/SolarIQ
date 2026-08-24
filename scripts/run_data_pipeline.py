#!/usr/bin/env python3
"""Run SolarIQ data pipelines.

Usage:
    python scripts/run_data_pipeline.py                    # Run all pipelines
    python scripts/run_data_pipeline.py --stage city       # Run only city pipeline
    python scripts/run_data_pipeline.py --stage weather    # Run only weather pipeline
    python scripts/run_data_pipeline.py --stage solar      # Run only solar pipeline
    python scripts/run_data_pipeline.py --stage osm        # Run only OSM pipeline
    python scripts/run_data_pipeline.py --city /path/to/city.geojson
    python scripts/run_data_pipeline.py --weather /path/to/weather.csv
    python scripts/run_data_pipeline.py --solar /path/to/solar.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.pipeline.run_all import run_all_pipelines
from data_pipeline.pipeline.city_pipeline import process_city_data
from data_pipeline.pipeline.weather_pipeline import process_weather_data
from data_pipeline.pipeline.solar_pipeline import process_solar_data
from data_pipeline.pipeline.osm_pipeline import process_osm_data

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SolarIQ data pipelines."
    )
    parser.add_argument(
        "--stage",
        type=str,
        default=None,
        choices=["city", "weather", "solar", "osm", "all"],
        help="Run a specific pipeline stage (default: all).",
    )
    parser.add_argument("--city", type=str, default=None, help="Path to city data file.")
    parser.add_argument("--weather", type=str, default=None, help="Path to weather data file.")
    parser.add_argument("--solar", type=str, default=None, help="Path to solar data file.")
    parser.add_argument("--osm", type=str, default=None, help="Path to OSM data file.")

    args = parser.parse_args()

    print("=" * 60)
    print("  SolarIQ Data Pipeline")
    print("=" * 60)
    print()

    if args.stage and args.stage != "all":
        # Run individual stage
        stage = args.stage
        if stage == "city" and args.city:
            report = process_city_data(args.city)
            _print_report("city", report)
        elif stage == "weather" and args.weather:
            report = process_weather_data(args.weather)
            _print_report("weather", report)
        elif stage == "solar" and args.solar:
            report = process_solar_data(args.solar)
            _print_report("solar", report)
        elif stage == "osm" and args.osm:
            report = process_osm_data(args.osm)
            _print_report("osm", report)
        else:
            print(f"  Stage '{stage}' requires a source file. Use --{stage} /path/to/file")
            sys.exit(1)
    else:
        # Run all pipelines
        results = run_all_pipelines(
            city_source=args.city,
            weather_source=args.weather,
            solar_source=args.solar,
        )

        print()
        print("=" * 60)
        print("  PIPELINE SUMMARY")
        print("=" * 60)

        for name, pipeline in results["pipelines"].items():
            status_icon = "OK" if pipeline["status"] == "success" else "FAIL"
            print(f"  [{status_icon}] {name}: {pipeline['status']}")
            for step in pipeline.get("steps", []):
                s_icon = "  OK" if step["status"] == "success" else "  FAIL"
                print(f"    {s_icon} {step['step']}: {step['details']}")

        print()
        print(f"  Overall Status: {results['status']}")
        print("=" * 60)

    # Show generated files
    print()
    print("  Generated files:")
    processed_dir = PROJECT_ROOT / "data" / "processed"
    if processed_dir.exists():
        for f in sorted(processed_dir.glob("*")):
            if f.is_file():
                size = f.stat().st_size
                print(f"    {f.name} ({size} bytes)")


def _print_report(name: str, report: object) -> None:
    """Print a processing report."""
    print()
    print(f"  [{name.upper()}] Status: {report.status}")
    for step in report.steps:
        icon = "OK" if step.status == "success" else "FAIL"
        print(f"    [{icon}] {step.step}: {step.details}")


if __name__ == "__main__":
    main()
