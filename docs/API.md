# SolarIQ API Reference

Base URL: `http://localhost:8000`

## System Endpoints

### GET /

Return basic API information.

**Response** `200 OK`
```json
{
  "project": "SolarIQ",
  "status": "running",
  "version": "0.1.0"
}
```

---

### GET /health

Lightweight health check for load balancers and orchestrators.
Returns 200 if the process is alive. No external dependencies checked.

**Response** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

### GET /status

Detailed backend status for monitoring and debugging.

**Response** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "services": {
    "geometry_engine": "available",
    "solar_engine": "available",
    "optimization_engine": "available",
    "ml_engine": "fallback",
    "database": "available"
  },
  "paths": {
    "data_dir": {"path": "/app/data", "accessible": true},
    "model_dir": {"path": "/app/models", "accessible": true},
    "processed_dir": "/app/data/processed"
  }
}
```

---

## Building Analysis

### POST /analyze-building

Analyze a single building's solar potential.

**Request Body**
```json
{
  "building": {
    "building_id": "B001",
    "name": "Example Building",
    "surfaces": [
      {
        "surface_id": "S001",
        "vertices": [
          [0, 0, 10],
          [20, 0, 10],
          [20, 20, 10],
          [0, 20, 10]
        ]
      }
    ]
  }
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `building_id` | string | Yes | 1–128 characters |
| `name` | string | No | max 256 characters |
| `surfaces` | array | Yes | min 1 surface |
| `surfaces[].surface_id` | string | No | auto-generated if omitted |
| `surfaces[].vertices` | array | Yes | min 3 vertices, each `[x, y, z]` |

**Response** `200 OK`
```json
{
  "building_id": "B001",
  "name": "Example Building",
  "surface_count": 1,
  "total_surface_area_m2": 400.0,
  "usable_surface_area_m2": 320.0,
  "estimated_capacity_kw": 64.0,
  "estimated_annual_energy_kwh": 544000.0,
  "surfaces": [
    {
      "surface_id": "S001",
      "building_id": "B001",
      "area_m2": 400.0,
      "normal": {"x": 0.0, "y": 0.0, "z": 1.0},
      "azimuth_deg": 0.0,
      "tilt_deg": 0.0,
      "surface_type": "roof",
      "vertices": [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]],
      "solar_score": 0.8,
      "solar_suitability": "high",
      "energy_potential": {
        "usable_area_m2": 320.0,
        "estimated_capacity_kw": 64.0,
        "estimated_annual_energy_kwh": 544000.0
      },
      "ml_prediction": null
    }
  ]
}
```

**Errors**

| Code | Cause |
|------|-------|
| 422 | Malformed geometry, missing `building_id`, collinear vertices, degenerate polygon |

---

## City Analysis

### POST /city-analysis

Analyze multiple buildings at once. Returns per-building results
and an aggregated city summary.

**Request Body**
```json
{
  "buildings": [
    {
      "building_id": "B001",
      "surfaces": [
        {
          "vertices": [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]]
        }
      ]
    }
  ]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `buildings` | array | Yes | min 1, max 100 (configurable) |

**Response** `200 OK`
```json
{
  "summary": {
    "building_count": 1,
    "surface_count": 1,
    "total_surface_area_m2": 400.0,
    "total_usable_surface_area_m2": 320.0,
    "total_estimated_capacity_kw": 64.0,
    "total_estimated_annual_energy_kwh": 544000.0
  },
  "buildings": [
    { "...same as /analyze-building response..." }
  ]
}
```

**Errors**

| Code | Cause |
|------|-------|
| 413 | More than `SOLARIQ_MAX_BUILDINGS` (default: 100) |
| 422 | Malformed geometry in any building |

---

## Solar Prediction

### POST /predict-solar

Predict solar potential for a single surface. Uses ML model if
connected, otherwise returns heuristic fallback.

**Request Body**
```json
{
  "surface_id": "PS-001",
  "building_id": "PB-001",
  "area_m2": 400.0,
  "azimuth_deg": 180.0,
  "tilt_deg": 20.0,
  "surface_type": "roof",
  "latitude": 19.076,
  "longitude": 72.878
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `area_m2` | float | Yes | > 0 |
| `azimuth_deg` | float | Yes | 0–360 |
| `tilt_deg` | float | Yes | 0–90 |
| `surface_type` | string | Yes | `roof`, `facade`, or `ground` |
| `latitude` | float | No | -90 to 90 |
| `longitude` | float | No | -180 to 180 |

**Response** `200 OK`
```json
{
  "surface_id": "PS-001",
  "building_id": "PB-001",
  "available": false,
  "prediction": null,
  "fallback_score": 0.8,
  "fallback_suitability": "high",
  "fallback_energy": {
    "usable_area_m2": 320.0,
    "estimated_capacity_kw": 64.0,
    "estimated_annual_energy_kwh": 544000.0
  }
}
```

| Field | Description |
|-------|-------------|
| `available` | Whether an ML model is connected |
| `prediction` | ML model output, or `null` if unavailable |
| `fallback_score` | Heuristic solar score (0.0–1.0) |
| `fallback_suitability` | `high`, `medium`, or `low` |
| `fallback_energy` | Baseline energy estimation |

**Errors**

| Code | Cause |
|------|-------|
| 422 | Invalid field values (area ≤ 0, azimuth > 360, invalid surface_type) |
| 500 | ML prediction failed (when model is connected) |

---

## Optimization

### POST /optimization-routes

Rank building surfaces by solar suitability using multi-factor
weighted scoring. Ground surfaces are excluded.

**Request Body** — Same as `/city-analysis` (list of buildings)

**Query Parameters**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `limit` | int | 5 | 1–200 | Max results to return |
| `min_solar_score` | float | — | 0.0–1.0 | Minimum solar score filter |
| `min_usable_area` | float | — | > 0 | Minimum usable area (m²) |
| `max_surfaces` | int | — | > 0 | Maximum surfaces to return |
| `max_capacity` | float | — | > 0 | Maximum cumulative capacity (kW) |

**Example**
```
POST /optimization-routes?limit=10&min_solar_score=0.5
```

**Response** `200 OK`
```json
{
  "total_candidates": 4,
  "filtered_candidates": 3,
  "scoring_weights": {
    "suitability": 0.35,
    "energy": 0.25,
    "capacity": 0.15,
    "area": 0.15,
    "orientation": 0.10
  },
  "city_summary": {
    "total_suitable_area_m2": 1280.0,
    "total_potential_capacity_kw": 256.0,
    "total_annual_energy_kwh": 2176000.0,
    "top_buildings": ["B001", "B002"],
    "top_surfaces": ["S001", "S003", "S002"]
  },
  "results": [
    {
      "rank": 1,
      "building_id": "B001",
      "surface_id": "S001",
      "area_m2": 400.0,
      "surface_type": "roof",
      "azimuth_deg": 0.0,
      "tilt_deg": 0.0,
      "solar_score": 0.8,
      "solar_suitability": "high",
      "usable_area_m2": 320.0,
      "estimated_capacity_kw": 64.0,
      "estimated_annual_energy_kwh": 544000.0,
      "composite_score": 0.85,
      "recommendation": "Top-ranked surface; high solar suitability score; ..."
    }
  ]
}
```

**Scoring Formula**
```
composite = w₁ × suitability
          + w₂ × energy
          + w₃ × capacity
          + w₄ × area
          + w₅ × orientation
```

Each component is normalized to [0, 1] before weighting. Weights
sum to 1.0 and are configurable via environment variables.

**Errors**

| Code | Cause |
|------|-------|
| 422 | Invalid geometry, invalid query parameters |

---

## Common Response Headers

All responses include:

| Header | Description |
|--------|-------------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Cache-Control` | `no-store, no-cache, must-revalidate` |
| `X-Response-Time` | Request processing time (e.g., `0.0452s`) |

## Error Response Format

All errors return JSON:
```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (422) include field-level details:
```json
{
  "detail": [
    {
      "loc": ["body", "building", "surfaces"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```
