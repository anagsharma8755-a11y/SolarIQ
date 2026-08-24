# SolarIQ Testing Guide

## Quick Start

```bash
# Run all tests
python -m pytest -q

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest backend/tests/test_api.py -v

# Run security tests only
python -m pytest tests/test_security.py -v

# Run with coverage
python -m pytest --cov=backend --cov-report=term-missing
```

## Test Structure

```
tests/
├── conftest.py                    # Project-wide pytest config
├── test_security.py               # Security-focused tests (56 tests)
└── data_pipeline/
    ├── test_city_pipeline.py
    ├── test_coordinates.py
    ├── test_data_quality.py
    ├── test_osm_geojson.py
    ├── test_projections.py
    ├── test_solar_pipeline.py
    ├── test_solar_providers.py
    ├── test_validation.py
    ├── test_weather_pipeline.py
    └── test_weather_providers.py

backend/tests/
├── test_api.py                    # Core API endpoint tests
├── test_api_extended.py           # Extended API tests
├── test_calculations.py           # Geometry calculation tests
├── test_database.py               # Database repository tests
├── test_geometry_extended.py      # Extended geometry tests
├── test_ml_service.py             # ML service adapter tests
├── test_optimization_extended.py  # Optimization engine tests
├── test_parser.py                 # File parser tests
├── test_qa_comprehensive.py       # QA integration tests
├── test_solar_service.py          # Solar scoring tests
└── test_surfaces.py               # Surface extraction tests
```

## Test Categories

### API Tests (`test_api.py`, `test_api_extended.py`)
- Endpoint response codes and shapes
- Request validation (malformed JSON, missing fields)
- Building analysis pipeline
- City analysis aggregation
- Optimization ranking
- ML prediction fallback
- Error handler behavior
- Security headers

### Geometry Tests (`test_calculations.py`, `test_geometry_extended.py`)
- Normal calculation
- Area calculation (triangles, quads, polygons)
- Tilt and azimuth computation
- Surface classification
- Degenerate polygon detection
- Reversed winding correction
- Centroid and bounding box
- Winding normalization

### Solar Tests (`test_solar_service.py`)
- Orientation scoring
- Tilt scoring
- Solar score calculation
- Energy potential estimation
- Ground surface handling
- Suitability labels

### Optimization Tests (`test_optimization_extended.py`)
- Composite scoring
- Constraint filtering
- Ranking correctness
- City-level aggregation
- Recommendation generation
- Edge cases (empty inputs, single surface)

### Database Tests (`test_database.py`)
- CRUD operations for all models
- Relationship integrity
- Transaction rollback
- Pipeline run lifecycle

### Security Tests (`test_security.py`)
- Path traversal protection
- CSV injection sanitization
- File size limits
- Model trust validation
- Bounding box validation
- Coordinate validation
- API security headers
- Schema validation edge cases

### Data Pipeline Tests (`tests/data_pipeline/`)
- OSM data parsing
- GeoJSON loading
- Data cleaning
- Validation
- Weather/solar providers
- Pipeline orchestration

## Current Results

```
583 passed, 1 pre-existing failure, 3 skipped
```

The single pre-existing failure is `test_optimization_limit_exceeds_candidates`
which expects `limit=500` to succeed, but the endpoint validates
`le=MAX_OPTIMIZATION_LIMIT=200`.

## Writing New Tests

### API Tests
```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_my_endpoint():
    response = client.post("/analyze-building", json={...})
    assert response.status_code == 200
    data = response.json()
    assert "building_id" in data
```

### Unit Tests
```python
from backend.geometry.calculations import analyze_polygon_batch

def test_roof_classification():
    result = analyze_polygon_batch([
        [0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]
    ])
    assert result["surface_type"] == "roof"
```

## Test Configuration

`pytest.ini`:
```ini
[pytest]
testpaths = backend/tests tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```
