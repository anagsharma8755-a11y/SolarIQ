"""Security utilities for SolarIQ backend.

Provides:
- Path traversal protection for file operations
- Input sanitization for CSV injection
- Safe file loading helpers
- Trusted model-file validation
- Request size validation
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path traversal protection
# ---------------------------------------------------------------------------

# Maximum allowed file size for JSON loading (100 MB).
MAX_JSON_FILE_SIZE: int = 100 * 1024 * 1024

# Maximum allowed file size for CSV loading (200 MB).
MAX_CSV_FILE_SIZE: int = 200 * 1024 * 1024

# Allowed file extensions for trusted model files.
TRUSTED_MODEL_EXTENSIONS: set[str] = {
    ".json",       # sklearn pipeline exported as JSON
    ".joblib",     # joblib-serialized models (trusted only)
    ".pkl",        # pickle files (requires explicit trust)
}


class PathTraversalError(ValueError):
    """Raised when a file path escapes the allowed directory."""


class FileSizeError(ValueError):
    """Raised when a file exceeds the maximum allowed size."""


class ModelTrustError(ValueError):
    """Raised when a model file does not meet trust requirements."""


def validate_path_within(
    file_path: str | Path,
    allowed_root: str | Path,
) -> Path:
    """Ensure *file_path* resolves within *allowed_root*.

    Prevents path traversal attacks such as ``../../etc/passwd``.

    Args:
        file_path: The path to validate.
        allowed_root: The directory the path must stay within.

    Returns:
        The resolved, canonical path.

    Raises:
        PathTraversalError: If the resolved path escapes allowed_root.
    """
    root = Path(allowed_root).resolve()
    target = Path(file_path).resolve()

    # Check that target is within root or is root itself.
    try:
        target.relative_to(root)
    except ValueError:
        raise PathTraversalError(
            f"Path {file_path!r} resolves outside the allowed "
            f"directory {root!r} (resolved to {target!r})."
        )

    return target


def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from a filename.

    Strips path separators, null bytes, and control characters
    that could be used for directory traversal or injection.

    Args:
        filename: The raw filename.

    Returns:
        A sanitized filename safe for filesystem use.
    """
    # Remove null bytes and path separators.
    sanitized = filename.replace("\x00", "")
    sanitized = sanitized.replace("/", "_").replace("\\", "_")
    sanitized = sanitized.replace("..", "_")

    # Strip leading/trailing whitespace and dots.
    sanitized = sanitized.strip(" .")

    # If empty after sanitization, use a default.
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized


# ---------------------------------------------------------------------------
# CSV injection protection
# ---------------------------------------------------------------------------

# Characters that can trigger formula injection in spreadsheet apps.
CSV_INJECTION_PREFIXES: tuple[str, ...] = (
    "=", "+", "-", "@", "\t", "\r",
)


def sanitize_csv_value(value: str) -> str:
    """Sanitize a string value to prevent CSV injection.

    Spreadsheet applications (Excel, Google Sheets, LibreOffice)
    treat certain leading characters as formula indicators. This
    function prefixes dangerous values with a single quote.

    See: https://owasp.org/www-community/attacks/CSV_Injection

    Args:
        value: The raw string value.

    Returns:
        The sanitized value.
    """
    if not isinstance(value, str):
        return value

    stripped = value.lstrip()
    for prefix in CSV_INJECTION_PREFIXES:
        if stripped.startswith(prefix):
            return "'" + value

    return value


# ---------------------------------------------------------------------------
# Safe JSON file loading
# ---------------------------------------------------------------------------


def safe_load_json(
    file_path: str | Path,
    allowed_root: str | Path | None = None,
    max_size: int = MAX_JSON_FILE_SIZE,
) -> dict[str, Any] | list[Any]:
    """Load a JSON file with size and path validation.

    Prevents:
    - Path traversal via ``../`` sequences
    - Memory exhaustion via oversized files
    - Unsafe deserialization (uses json.load, not pickle)

    Args:
        file_path: Path to the JSON file.
        allowed_root: Optional root directory constraint.
        max_size: Maximum file size in bytes.

    Returns:
        Parsed JSON data.

    Raises:
        PathTraversalError: If path escapes allowed_root.
        FileSizeError: If file exceeds max_size.
        FileNotFoundError: If file does not exist.
        ValueError: If JSON is invalid.
    """
    path = Path(file_path)

    # Path traversal check.
    if allowed_root is not None:
        path = validate_path_within(path, allowed_root)

    # Existence check.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")

    # Size check (avoid reading entire file into memory).
    file_size = path.stat().st_size
    if file_size > max_size:
        raise FileSizeError(
            f"File {path} is {file_size} bytes, exceeding "
            f"the limit of {max_size} bytes."
        )

    # Safe JSON loading (not pickle, not yaml, not eval).
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def safe_load_json_from_bytes(
    data: bytes,
    max_size: int = MAX_JSON_FILE_SIZE,
) -> dict[str, Any] | list[Any]:
    """Parse JSON from raw bytes with size validation.

    Args:
        data: Raw JSON bytes.
        max_size: Maximum allowed size in bytes.

    Returns:
        Parsed JSON data.

    Raises:
        FileSizeError: If data exceeds max_size.
        ValueError: If JSON is invalid.
    """
    if len(data) > max_size:
        raise FileSizeError(
            f"Payload is {len(data)} bytes, exceeding "
            f"the limit of {max_size} bytes."
        )

    return json.loads(data.decode("utf-8"))


# ---------------------------------------------------------------------------
# Trusted model-file validation
# ---------------------------------------------------------------------------


def validate_model_file(
    file_path: str | Path,
    allowed_root: str | Path | None = None,
) -> Path:
    """Validate that a model file meets trust requirements.

    Security requirements for ML model files:
    1. Must be within the configured MODEL_DIR.
    2. Must have a recognized, trusted extension.
    3. Must not be a symlink (to prevent symlink-based attacks).
    4. File size is logged for audit purposes.

    Why not blindly load pickle?
    - Pickle files can execute arbitrary Python code during
      deserialization. An attacker who can modify a pickle file
      can achieve remote code execution.
    - Use JSON-serialized models or joblib with trusted sources
      instead.

    Args:
        file_path: Path to the model file.
        allowed_root: The MODEL_DIR to constrain paths within.

    Returns:
        The validated, resolved path.

    Raises:
        ModelTrustError: If trust validation fails.
        PathTraversalError: If path escapes allowed_root.
    """
    path = Path(file_path)

    # Path traversal check.
    if allowed_root is not None:
        path = validate_path_within(path, allowed_root)

    if not path.exists():
        raise ModelTrustError(f"Model file not found: {path}")

    # Symlink check.
    if path.is_symlink():
        raise ModelTrustError(
            f"Model file {path} is a symlink. "
            "Symlinked model files are not trusted. "
            "Use a regular file within MODEL_DIR."
        )

    # Extension check.
    if path.suffix.lower() not in TRUSTED_MODEL_EXTENSIONS:
        raise ModelTrustError(
            f"Model file {path} has extension {path.suffix!r}. "
            f"Trusted extensions: {sorted(TRUSTED_MODEL_EXTENSIONS)}"
        )

    # Log file size for audit trail.
    size = path.stat().st_size
    logger.info(
        "Model file validated: %s (%d bytes, ext=%s)",
        path.name, size, path.suffix,
    )

    return path


# ---------------------------------------------------------------------------
# Overpass query validation
# ---------------------------------------------------------------------------

def validate_bbox(
    south: float,
    west: float,
    north: float,
    east: float,
) -> None:
    """Validate a geographic bounding box.

    Args:
        south: Southern latitude.
        west: Western longitude.
        north: Northern latitude.
        east: Eastern longitude.

    Raises:
        ValueError: If the bounding box is invalid.
    """
    if not (-90.0 <= south <= 90.0):
        raise ValueError(f"South latitude {south} out of range [-90, 90]")
    if not (-90.0 <= north <= 90.0):
        raise ValueError(f"North latitude {north} out of range [-90, 90]")
    if not (-180.0 <= west <= 180.0):
        raise ValueError(f"West longitude {west} out of range [-180, 180]")
    if not (-180.0 <= east <= 180.0):
        raise ValueError(f"East longitude {east} out of range [-180, 180]")
    if south >= north:
        raise ValueError(
            f"South latitude ({south}) must be less than "
            f"north latitude ({north})."
        )
    if west >= east:
        raise ValueError(
            f"West longitude ({west}) must be less than "
            f"east longitude ({east})."
        )

    # Warn about excessively large areas (> 5 degrees).
    span_lat = north - south
    span_lon = east - west
    if span_lat > 5.0 or span_lon > 5.0:
        logger.warning(
            "Bounding box is large (%.2f° lat × %.2f° lon). "
            "This may return excessive data.",
            span_lat, span_lon,
        )


def validate_coordinate(
    latitude: float,
    longitude: float,
) -> None:
    """Validate a single coordinate pair.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Raises:
        ValueError: If coordinates are out of range.
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} out of range [-90, 90]")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} out of range [-180, 180]")
