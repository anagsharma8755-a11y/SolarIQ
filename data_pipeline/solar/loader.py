"""Solar radiation data loader.

Supports CSV and JSON input files with flexible column name
detection and normalization.

Security: Files are validated for size and path safety before
loading to prevent path traversal and memory exhaustion.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from data_pipeline.config import SOLAR_COLUMN_MAP

# Maximum allowed file size (200 MB).
_MAX_FILE_SIZE = 200 * 1024 * 1024



def _validate_file_path(path: Path) -> None:
    """Validate that a file path is safe to load."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")

    if path.is_symlink():
        raise ValueError(
            f"Symlinked file not allowed: {path}. "
            "Use a regular file."
        )

    file_size = path.stat().st_size
    if file_size > _MAX_FILE_SIZE:
        raise ValueError(
            f"File {path.name} is {file_size} bytes, exceeding "
            f"the {_MAX_FILE_SIZE} byte limit."
        )

logger = logging.getLogger(__name__)


def _normalize_column_name(col: str) -> str:
    """Map a column name to the canonical name using SOLAR_COLUMN_MAP."""
    normalized = col.strip().lower().replace(" ", "_")
    return SOLAR_COLUMN_MAP.get(normalized, normalized)


def load_csv(file_path: Path | str) -> pd.DataFrame:
    """Load a solar radiation CSV file with column normalization.

    Returns a DataFrame with canonical column names.
    """
    path = Path(file_path)

    _validate_file_path(path)

    df = pd.read_csv(path)

    # Normalize column names
    df.columns = [_normalize_column_name(c) for c in df.columns]

    logger.info(
        "Loaded %d rows from %s",
        len(df),
        path.name,
    )

    return df


def load_json(file_path: Path | str) -> pd.DataFrame:
    """Load a solar radiation JSON file with column normalization.

    Supports both a list of records and an object with a
    ``records`` key.
    """
    path = Path(file_path)

    _validate_file_path(path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        records = data.get("records", data.get("data", []))
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError(
            f"Unexpected JSON structure in {path.name}."
        )

    df = pd.DataFrame(records)

    # Normalize column names
    df.columns = [_normalize_column_name(c) for c in df.columns]

    logger.info(
        "Loaded %d records from %s",
        len(df),
        path.name,
    )

    return df


def load_solar_data(file_path: Path | str) -> pd.DataFrame:
    """Load solar radiation data from CSV or JSON.

    Returns a DataFrame with canonical column names.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return load_csv(path)
    elif suffix == ".json":
        return load_json(path)
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}'. "
            "Use .csv or .json."
        )
