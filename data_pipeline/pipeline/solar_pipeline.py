"""Solar radiation data pipeline.

Orchestrates the complete flow from raw solar data
to a clean, validated CSV output.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import pandas as pd

from data_pipeline.config import DEFAULT_SOLAR_OUTPUT
from data_pipeline.schemas import ProcessingReport, ProcessingStep
from data_pipeline.solar.cleaner import clean_solar_data
from data_pipeline.solar.loader import load_solar_data
from data_pipeline.solar.validator import validate_solar_df

logger = logging.getLogger(__name__)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def process_solar_data(
    source_path: Path | str,
    output_path: Path | str | None = None,
) -> ProcessingReport:
    """Run the complete solar radiation data pipeline.

    Args:
        source_path: Path to input CSV or JSON file.
        output_path: Where to save the cleaned CSV.

    Returns:
        A ProcessingReport documenting all steps.
    """
    source = Path(source_path)
    out = Path(output_path) if output_path else DEFAULT_SOLAR_OUTPUT

    steps: list[ProcessingStep] = []

    # ------------------------------------------------------------------
    # Step 1: Load
    # ------------------------------------------------------------------
    logger.info("[STEP 1] Loading solar data from %s", source.name)

    try:
        df = load_solar_data(source)
        steps.append(
            ProcessingStep(
                step="load",
                status="success",
                records_in=0,
                records_out=len(df),
                details=f"Loaded {len(df)} rows from {source.name}",
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
            pipeline="solar",
            source=str(source),
            status="error",
            steps=steps,
        )

    # ------------------------------------------------------------------
    # Step 2: Clean
    # ------------------------------------------------------------------
    logger.info("[STEP 2] Cleaning solar data...")

    df_clean, clean_report = clean_solar_data(df)

    steps.append(
        ProcessingStep(
            step="clean",
            status="success",
            records_in=clean_report["rows_input"],
            records_out=clean_report["rows_output"],
            details=(
                f"Removed {clean_report['rows_removed_missing']} missing, "
                f"{clean_report['rows_removed_duplicates']} duplicates"
            ),
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Validate
    # ------------------------------------------------------------------
    logger.info("[STEP 3] Validating solar data...")

    validation_result = validate_solar_df(df_clean)

    steps.append(
        ProcessingStep(
            step="validate",
            status="success" if validation_result.valid else "warning",
            records_in=len(df_clean),
            records_out=validation_result.records_valid,
            details=(
                f"Valid: {validation_result.records_valid}, "
                f"Invalid: {validation_result.records_invalid}"
            ),
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Save
    # ------------------------------------------------------------------
    logger.info("[STEP 4] Saving cleaned solar data...")

    out.parent.mkdir(parents=True, exist_ok=True)

    # Add source metadata
    df_clean["source"] = source.stem
    df_clean["source_hash"] = _compute_file_hash(source)

    df_clean.to_csv(out, index=False)

    steps.append(
        ProcessingStep(
            step="save",
            status="success",
            records_in=len(df_clean),
            records_out=len(df_clean),
            details=f"Saved to {out.relative_to(out.parent.parent)}",
        )
    )

    logger.info(
        "[DONE] Solar pipeline complete: %d rows saved.",
        len(df_clean),
    )

    return ProcessingReport(
        pipeline="solar",
        source=str(source),
        status="success",
        steps=steps,
        validation=validation_result,
    )


def load_processed_solar(
    processed_path: Path | str | None = None,
) -> pd.DataFrame:
    """Load processed solar data.

    Args:
        processed_path: Path to cleaned CSV.
            Defaults to standard output location.

    Returns:
        Cleaned solar DataFrame.
    """
    path = (
        Path(processed_path)
        if processed_path
        else DEFAULT_SOLAR_OUTPUT
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Processed solar data not found: {path}. "
            "Run the solar pipeline first."
        )

    return pd.read_csv(path)
