# SolarIQ Limitations

This document explicitly lists what SolarIQ **cannot do** and where
the current implementation falls short of production requirements.

## Geometry Limitations

### LOD-1 Only
The system generates Level of Detail 1 (LOD-1) building geometry:
extruded boxes with flat roofs. Real buildings have pitched roofs,
dormers, setbacks, and complex geometry that LOD-1 cannot represent.

- **LOD-2 data model exists** (`backend/geometry/lod2.py`) but
  LOD-2 generation from footprints is **not implemented**
- Pitched roofs are modeled as flat horizontal surfaces
- Roof obstacles (HVAC units, vents, skylights) are not considered

### No Real-World Geometry Source
The current pipeline generates LOD-1 boxes from 2D OSM footprints
+ a default height (15m). There is no integration with:
- CityGML data
- 3D Tiles
- LiDAR point clouds
- Photogrammetry outputs

### Polygon Limitations
- Only planar polygons are supported (non-planar surfaces rejected)
- Fan triangulation from first vertex (works for convex and simple
  concave polygons, but not complex concave)
- Self-intersecting polygons are not handled

## Shading Limitations

**Shading analysis is not integrated into the scoring pipeline.**

The `backend/geometry/shading.py` module exists with:
- `ShadingAnalyzer` class
- Simple proximity + height heuristic
- Horizon obstruction estimation

However, shading results are **not used** in solar scoring or
optimization. The current scoring assumes unobstructed solar access
for all surfaces.

What's missing:
- Ray-tracing between buildings
- Solar position modeling (sun path)
- Time-of-day shading variation
- Tree/vegetation obstruction
- Roof obstruction mapping

## Weather Data Limitations

### No Real-Time Integration
The weather pipeline processes historical or downloaded data. There
is no live weather feed integrated into energy estimation.

### Synthetic Fallback Data
When real weather data is unavailable, the fallback provider
generates synthetic clear-sky data. This does not represent
actual cloud cover, precipitation, or seasonal variation.

### Irradiance Not Used in Scoring
The annual irradiance value (default: 1700 kWh/m²) is a static
configuration parameter, not site-specific data. The weather
pipeline exists but its output is not consumed by the solar
scoring engine.

## ML Limitations

**No trained model exists.** The ML service is a stub:
- `ml_service.model = None` (always)
- `predict_if_available()` always returns `None`
- All responses use `fallback_score` from heuristics

What would be needed for a real ML model:
- Training dataset with actual energy production measurements
- Feature engineering pipeline
- Model training and evaluation
- Inference optimization
- Model versioning and rollback

## Solar Scoring Limitations

### Heuristic, Not Physics-Based
The scoring uses simple geometric heuristics:
- 50% orientation (south-facing preferred)
- 30% tilt (~20° optimal)
- 20% surface type (roof > facade)

This does not account for:
- Actual solar irradiance at the site
- Seasonal variation
- Cloud cover patterns
- Atmospheric conditions
- Panel technology differences

### Static Energy Estimation
Energy estimation uses fixed parameters:
- Coverage factor: 80% (configurable)
- Panel efficiency: 20% (configurable)
- Annual irradiance: 1700 kWh/m² (configurable)

These are global defaults, not site-specific values. Real
installations vary significantly based on location, panel
technology, and system design.

### No System Losses
The energy calculation does not model:
- Inverter efficiency
- Wiring losses
- Soiling/dirt accumulation
- Temperature derating
- Mismatch losses
- Snow coverage

The `PERFORMANCE_RATIO` config exists (default: 0.85) but is
**not applied** in the current energy formula.

## Data Pipeline Limitations

### OSM Data Quality
OpenStreetMap building data varies significantly by region:
- Height data is often missing (defaults to 15m)
- Footprint accuracy varies
- Building types are inconsistently tagged
- Coverage is incomplete in some areas

### No Data Freshness Tracking
The pipeline generates SHA-256 hashes of source files for change
detection, but there is no automatic re-processing when source
data changes.

## API Limitations

### No Authentication
The API has no authentication or authorization. All endpoints
are publicly accessible. This is suitable for development but
not production.

### No Rate Limiting
There is no per-IP or per-user rate limiting. A single client
can send unlimited requests.

### No Pagination
The `/city-analysis` endpoint returns all results at once.
For very large cities (1000+ buildings), this could produce
very large responses.

### No Streaming
Large analysis requests are processed synchronously. There is
no background job processing or streaming responses.

## Sample Data

All sample data in `sample_data/` is **synthetic**:
- `mumbai_sample.geojson` — Generated building footprints
- Weather data — Synthetic clear-sky approximations
- Solar data — Synthetic irradiance values

These are for development and testing only. They do not represent
real-world conditions for Mumbai or any other city.

## What Would Make This Production-Ready

1. **Real LOD-2/3 geometry** from CityGML or 3D Tiles
2. **Site-specific irradiance** from PVGIS, NSRDB, or similar
3. **Shading integration** in the scoring pipeline
4. **Trained ML model** with real energy production data
5. **Authentication and rate limiting**
6. **Background job processing** for large analyses
7. **Real weather data integration** for energy estimation
8. **Panel-specific parameters** (STC ratings, temperature coefficients)
9. **System loss modeling** (inverter, wiring, soiling)
10. **Database persistence** for analysis results
