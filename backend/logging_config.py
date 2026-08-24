"""Structured logging configuration for SolarIQ.

Provides a single ``setup_logging()`` call that configures
the root logger with appropriate formatters, handlers, and
levels based on the SOLARIQ_ENV and SOLARIQ_LOG_LEVEL
environment variables.

Logging design:
- Development: human-readable console output, DEBUG level.
- Testing: minimal output, WARNING level.
- Production: JSON-structured logs, INFO level, no secrets.

Security:
- Never log API keys, credentials, or full geometry payloads.
- Request paths are logged; request bodies are not.
- Error messages are sanitized before logging.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any


class _JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects.

    Each line contains:
        timestamp, level, logger, message, plus any extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception info if present.
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        # Include any extra fields added via logExtra=... .
        for key in ("method", "path", "status_code", "duration_ms"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


class _TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Use color on TTY.
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, "")
            reset = self.RESET
        else:
            color = ""
            reset = ""

        timestamp = datetime.fromtimestamp(
            record.created
        ).strftime("%H:%M:%S")

        return (
            f"{color}{timestamp} "
            f"{record.levelname:8s} "
            f"{record.name}{reset} "
            f"{record.getMessage()}"
        )


def setup_logging() -> None:
    """Configure the root logger based on environment.

    Reads SOLARIQ_ENV and SOLARIQ_LOG_LEVEL from the environment.
    Safe to call multiple times (idempotent).
    """
    env = os.getenv("SOLARIQ_ENV", "development")
    level_name = os.getenv("SOLARIQ_LOG_LEVEL", "").upper()

    # Determine log level.
    if level_name:
        level = getattr(logging, level_name, logging.INFO)
    elif env == "production":
        level = logging.INFO
    elif env == "testing":
        level = logging.WARNING
    else:
        level = logging.DEBUG

    root = logging.getLogger()

    # Avoid duplicate handlers on repeated calls.
    if root.handlers:
        root.handlers.clear()

    root.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if env == "production":
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(_TextFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured: env=%s level=%s",
        env,
        logging.getLevelName(level),
    )
