from __future__ import annotations

import contextlib
import logging
import os
import time
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import (
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    DATA_DIR,
    DATABASE_URL,
    ENVIRONMENT,
    MODEL_DIR,
    PROCESSED_DATA_DIR,
)
from backend.api.building import router as building_router
from backend.api.city import router as city_router
from backend.api.optimization import router as optimization_router
from backend.api.prediction import router as prediction_router
from backend.api.location import router as location_router
from backend.api.area import router as area_router
from backend.api.ai import router as ai_router
from backend.logging_config import setup_logging
from backend.services.ml_service import ml_service

# Configure logging before anything else.
setup_logging()

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers (used before app creation)
# ------------------------------------------------------------------


def _mask_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if "@" in url:
        scheme_end = url.index("://") + 3
        at_pos = url.index("@")
        return url[:scheme_end] + "***:***@" + url[at_pos + 1:]
    return url


_cors_origins_raw = os.getenv("SOLARIQ_CORS_ORIGINS", "*")
_cors_origins = [
    o.strip() for o in _cors_origins_raw.split(",") if o.strip()
]


# ------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Modern lifespan context manager replacing deprecated on_event hooks.

    Runs setup logic before the app starts serving requests,
    and teardown logic after it stops.
    """
    # -- Startup --
    logger.info("=" * 60)
    logger.info("  SolarIQ Backend %s", APP_VERSION)
    logger.info("  Environment: %s", ENVIRONMENT)
    logger.info("=" * 60)

    # Ensure required directories exist.
    for label, path_str in [
        ("Data", DATA_DIR),
        ("Processed", PROCESSED_DATA_DIR),
        ("Models", MODEL_DIR),
    ]:
        p = Path(path_str)
        p.mkdir(parents=True, exist_ok=True)
        logger.info("  %s directory: %s", label, p.resolve())

    # Log database (mask password if present).
    safe_db = _mask_url(DATABASE_URL)
    logger.info("  Database: %s", safe_db)

    logger.info("  ML engine: %s", "connected" if ml_service.available else "fallback")
    logger.info("  CORS origins: %s", _cors_origins)
    logger.info("=" * 60)
    logger.info("  Server ready.")

    yield  # App is now running

    # -- Shutdown --
    logger.info("SolarIQ Backend shutting down.")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=600,
)


# ------------------------------------------------------------------
# Security / timing middleware
# ------------------------------------------------------------------


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next,
) -> JSONResponse:
    """Add security headers and request timing."""
    start_time = time.monotonic()

    response = await call_next(request)

    # Security headers.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate"
    )
    response.headers["Pragma"] = "no-cache"

    # Request timing for observability.
    elapsed = time.monotonic() - start_time
    response.headers["X-Response-Time"] = f"{elapsed:.4f}s"

    # Structured access log (skip health checks to reduce noise).
    if request.url.path not in ("/health", "/favicon.ico"):
        logger.info(
            "%s %s -> %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
        )

    # Log slow requests.
    if elapsed > 5.0:
        logger.warning(
            "Slow request: %s %s took %.2fs",
            request.method,
            request.url.path,
            elapsed,
        )

    return response


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(building_router)
app.include_router(city_router)
app.include_router(optimization_router)
app.include_router(prediction_router)
app.include_router(location_router)
app.include_router(area_router)
app.include_router(ai_router)


# ------------------------------------------------------------------
# Global error handlers
# ------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return structured 422 for request validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(
    request: Request, exc: RuntimeError
) -> JSONResponse:
    """Catch unhandled RuntimeErrors and return 500."""
    logger.error(
        "RuntimeError at %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal processing error occurred."
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all: never expose internal stack traces."""
    logger.error(
        "Unhandled exception at %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred."
        },
    )


# ------------------------------------------------------------------
# System endpoints
# ------------------------------------------------------------------


@app.get(
    "/",
    tags=["System"],
)
def root() -> dict[str, object]:
    """
    Return basic API information.

    The ``project`` field is retained for compatibility
    with the existing API contract.
    """
    return {
        "project": "SolarIQ",
        "status": "running",
        "version": APP_VERSION,
    }


@app.get(
    "/health",
    tags=["System"],
)
def health() -> dict[str, object]:
    """
    Lightweight health check for load balancers and orchestrators.

    Returns 200 if the process is alive and can serve requests.
    No external dependencies are checked here to keep this fast.
    """
    return {
        "status": "healthy",
        "version": APP_VERSION,
    }


@app.get(
    "/status",
    tags=["System"],
)
def status() -> dict[str, object]:
    """
    Detailed backend status for monitoring and debugging.

    Reports the state of all subsystems:
    - Application version and environment
    - Geometry and solar engines
    - ML engine (connected or fallback)
    - Database connectivity
    - Data and model directories
    """
    # Check database connectivity.
    db_status = "available"
    try:
        from backend.db.database import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception as exc:
        db_status = f"error: {type(exc).__name__}"
        logger.warning("Database health check failed: %s", exc)

    # Check directory accessibility.
    data_dir_ok = Path(DATA_DIR).is_dir()
    model_dir_ok = Path(MODEL_DIR).is_dir()

    return {
        "status": "healthy",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "services": {
            "geometry_engine": "available",
            "solar_engine": "available",
            "optimization_engine": "available",
            "ml_engine": (
                "connected"
                if ml_service.available
                else "fallback"
            ),
            "database": db_status,
        },
        "paths": {
            "data_dir": {"path": str(Path(DATA_DIR).resolve()), "accessible": data_dir_ok},
            "model_dir": {"path": str(Path(MODEL_DIR).resolve()), "accessible": model_dir_ok},
            "processed_dir": str(Path(PROCESSED_DATA_DIR).resolve()),
        },
    }
