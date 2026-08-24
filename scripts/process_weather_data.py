#!/usr/bin/env python3
"""Process weather data through the SolarIQ data pipeline.

Usage:
    python scripts/process_weather_data.py [--source PATH]

Processes weather data from CSV or JSON format and outputs
cleaned, validated data.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.config import DEFAULT_WEATHER_OUTPUT, SAMPLE_WEATHER_DIR
from data_pipeline.pipeline.weather_pipeline import process_weather_data

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process weather data for SolarIQ."
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to weather data file (CSV or JSON). "
             "If not provided, uses sample data.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: data/processed/weather_clean.csv)",
    )

    args = parser.parse_args()

    # Find source
    if args.source:
        source = Path(args.source)
    else:
        candidates = list(SAMPLE_WEATHER_DIR.glob("*.csv")) + list(
            SAMPLE_WEATHER_DIR.glob("*.json")
        )
        if candidates:
            source = candidates[0]
            print(f"[INFO] Using sample data: {source.name}")
        else:
            print("[ERROR] No weather source data found.")
            sys.exit(1)

    if not source.exists():
        print(f"[ERROR] Source file not found: {source}")
        sys.exit(1)

    output = Path(args.output) if args.output else DEFAULT_WEATHER_OUTPUT

    print(f"[INFO] Source: {source}")
    print(f"[INFO] Output: {output}")

    report = process_weather_data(source, output)

    # Print report
    print()
    print("=" * 50)
    print("  WEATHER PIPELINE REPORT")
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
