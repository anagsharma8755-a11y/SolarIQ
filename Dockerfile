# ---------------------------------------------------------------------------
# SolarIQ Backend — Production Dockerfile
#
# Multi-stage build for minimal final image.
# Stage 1: Install dependencies into a virtualenv.
# Stage 2: Copy only runtime artifacts.
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS builder

WORKDIR /build

# Install dependencies first (layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS runtime

# Non-root user for security.
RUN groupadd -r solariq && useradd -r -g solariq solariq

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

# Copy application code.
COPY backend/ backend/
COPY data_pipeline/ data_pipeline/
COPY conftest.py .
COPY pytest.ini .

# Create directories for data, models, cache, and processed output.
RUN mkdir -p data/processed data/cache/geocoding data/cache/osm data/cache/weather models sample_data \
    && chown -R solariq:solariq /app

# Environment defaults.
ENV SOLARIQ_ENV=production \
    SOLARIQ_HOST=0.0.0.0 \
    SOLARIQ_PORT=8000 \
    SOLARIQ_LOG_LEVEL=INFO \
    SOLARIQ_DATABASE_URL=sqlite:///data/solariq.db \
    SOLARIQ_DATA_DIR=data \
    SOLARIQ_PROCESSED_DATA_DIR=data/processed \
    SOLARIQ_MODEL_DIR=models

USER solariq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
