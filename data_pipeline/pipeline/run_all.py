"""Run all data pipelines.

Orchestrates city, weather, and solar pipelines in sequence,
generates a combined processing report and pipeline state.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_pipeline.config import (
    DEFAULT_REPORT_OUTPUT,
    DEFAULT_PIPELINE_STATE,
    PROCESSED_DATA_DIR,
    SAMPLE_CITY_DIR,
    SAMPLE_SOLAR_DIR,
    SAMPLE_WEATHER_DIR,
)
from data_pipeline.pipeline.city_pipeline import process_city_data
from data_pipeline.pipeline.solar_pipeline import process_solar_data
from data_pipeline.pipeline.weather_pipeline import process_weather_data

logger = logging.getLogger(__name__)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    import hashlib

    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_sample_file(directory: Path) -> Path | None:
    """Find the first data file in a sample directory."""
    if not directory.exists():
        return None

    for ext in ("*.geojson", "*.json", "*.csv"):
        files = sorted(directory.glob(ext))
        if files:
            return files[0]

    return None


def run_all_pipelines(
    city_source: Path | str | None = None,
    weather_source: Path | str | None = None,
    solar_source: Path | str | None = None,
) -> dict[str, Any]:
    """Run all data pipelines.

    If no source paths are provided, attempts to find
    sample data files automatically.

    Args:
        city_source: Path to city/building data file.
        weather_source: Path to weather data file.
        solar_source: Path to solar radiation data file.

    Returns:
        Combined results dict with reports and state.
    """
    results: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipelines": {},
        "status": "success",
    }

    state: dict[str, Any] = {}

    # --- City pipeline ---
    city_path = Path(city_source) if city_source else _find_sample_file(SAMPLE_CITY_DIR)
    if city_path and city_path.exists():
        logger.info("=" * 50)
        logger.info("  CITY PIPELINE")
        logger.info("=" * 50)
        report = process_city_data(city_path)
        results["pipelines"]["city"] = {
            "status": report.status,
            "steps": [s.model_dump() for s in report.steps],
        }
        state["city"] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "source_hash": _compute_file_hash(city_path),
            "status": report.status,
        }
    else:
        logger.warning("No city source data found. Skipping.")
        state["city"] = {"status": "skipped", "reason": "no source data"}

    # --- Weather pipeline ---
    weather_path = Path(weather_source) if weather_source else _find_sample_file(SAMPLE_WEATHER_DIR)
    if weather_path and weather_path.exists():
        logger.info("=" * 50)
        logger.info("  WEATHER PIPELINE")
        logger.info("=" * 50)
        report = process_weather_data(weather_path)
        results["pipelines"]["weather"] = {
            "status": report.status,
            "steps": [s.model_dump() for s in report.steps],
        }
        state["weather"] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "source_hash": _compute_file_hash(weather_path),
            "status": report.status,
        }
    else:
        logger.warning("No weather source data found. Skipping.")
        state["weather"] = {"status": "skipped", "reason": "no source data"}

    # --- Solar pipeline ---
    solar_path = Path(solar_source) if solar_source else _find_sample_file(SAMPLE_SOLAR_DIR)
    if solar_path and solar_path.exists():
        logger.info("=" * 50)
        logger.info("  SOLAR PIPELINE")
        logger.info("=" * 50)
        report = process_solar_data(solar_path)
        results["pipelines"]["solar"] = {
            "status": report.status,
            "steps": [s.model_dump() for s in report.steps],
        }
        state["solar"] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "source_hash": _compute_file_hash(solar_path),
            "status": report.status,
        }
    else:
        logger.warning("No solar source data found. Skipping.")
        state["solar"] = {"status": "skipped", "reason": "no source data"}

    # Determine overall status
    statuses = [
        p.get("status", "skipped")
        for p in results["pipelines"].values()
    ]
    if all(s == "success" for s in statuses):
        results["status"] = "success"
    elif any(s == "error" for s in statuses):
        results["status"] = "error"
    else:
        results["status"] = "partial"

    # Save combined report
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with DEFAULT_REPORT_OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    # Save pipeline state
    with DEFAULT_PIPELINE_STATE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)

    logger.info("=" * 50)
    logger.info("  ALL PIPELINES COMPLETE")
    logger.info("  Status: %s", results["status"])
    logger.info("=" * 50)

    return results
