# SolarIQ Geometry Engine

## Overview

The geometry engine performs 3D polygon analysis on building surfaces.
It converts raw vertex lists into geometric properties needed for
solar suitability assessment.

## Core Function: `analyze_polygon_batch()`

The primary entry point computes all geometry properties in a
**single pass** through the vertices:

```python
result = analyze_polygon_batch(vertices)
# Returns: normal, area, tilt, azimuth, surface_type, centroid, bbox
```

### What It Computes

| Property | Method | Description |
|----------|--------|-------------|
| Normal | Cross product of first two edges | Unit surface normal vector |
| Area | Fan triangulation from first vertex | Surface area in m² |
| Tilt | `acos(normal.z)` | Angle from horizontal (0–90°) |
| Azimuth | `atan2(normal.x, normal.y)` | Compass bearing (0–360°) |
| Surface type | Tilt threshold at 45° | `roof`, `facade`, or `ground` |
| Centroid | Arithmetic mean of vertices | 3D center point |
| Bounding box | Axis-aligned min/max | Extent in each dimension |

### Performance

Single-pass analysis was optimized from 7 separate function calls.
At 1000 surfaces, this reduced geometry processing from ~510ms to
~220ms (2.3× speedup). See `docs/PERFORMANCE.md` for benchmarks.

## Coordinate Convention

```
X = East
Y = North
Z = Up

Azimuth:
  0°   = North
  90°  = East
  180° = South
  270° = West

Tilt:
  0°  = Horizontal (normal pointing straight up)
  90° = Vertical (normal pointing horizontally)
```

## Surface Classification

| Condition | Classification |
|-----------|---------------|
| Tilt < 45° AND normal.z > 0 | `roof` |
| Tilt < 45° AND normal.z < 0 | `ground` |
| Tilt ≥ 45° | `facade` |

## Winding Order

Vertex winding order affects normal direction. The engine:

1. Detects reversed winding via cross product dominant axis check
2. Automatically corrects reversed vertices
3. Flags corrected surfaces with `reversed_winding_corrected: true`

## Degenerate Polygon Detection

Polygons are rejected if:
- Fewer than 3 vertices
- Cross product magnitude < 1e-10 (collinear vertices)
- Computed area ≤ 0

## Geospatial Projections

`backend/geometry/projections.py` supports:

| Function | Purpose |
|----------|---------|
| `get_utm_zone(longitude)` | Auto-detect UTM zone |
| `get_utm_epsg(lat, lon)` | Get EPSG code for UTM zone |
| `vertices_to_utm(vertices, lat, lon)` | WGS84 → UTM transform |
| `vertices_to_wgs84(vertices, lat, lon)` | UTM → WGS84 transform |
| `calculate_area_in_m2(vertices, lat, lon)` | Area in projected CRS |
| `make_crs_metadata(lat, lon)` | CRS metadata for responses |

**Key rule:** Area calculations must use projected coordinates
(UTM), not geographic coordinates (degrees).

## LOD-2 Data Model

`backend/geometry/lod2.py` defines data classes for LOD-2 geometry:

| Class | Purpose |
|-------|---------|
| `RoofPlane` | Single planar roof surface |
| `RoofRidge` | Ridge line connecting two roof planes |
| `Dormer` | Dormer window projecting from a roof |
| `LOD2Building` | Complete LOD-2 building representation |
| `lod2_to_lod1_surfaces()` | Downgrade LOD-2 → LOD-1 for analysis |

**Important:** LOD-2 generation from footprints is **not implemented**.
The module provides data models and validation only. When actual LOD-2
data is available (e.g., from CityGML), it can be consumed directly.

## Shading Analysis

`backend/geometry/shading.py` provides:

- `ShadingAnalyzer` — Extensible interface for shading computation
- `ShadingSource` — Represents a potential shading obstruction
- `ShadingResult` — Analysis result with severity and fraction
- `estimate_horizon_obstruction()` — Simplified horizon model

**Current implementation:** Simple proximity + height heuristic.
No ray tracing or solar position modeling. The shading engine is
designed to be extended, not used in production scoring.

## Input Validation

Vertices are validated before geometric analysis:
- Must be a list of lists
- Each vertex must have exactly 3 numeric coordinates
- Minimum 3 vertices per surface
- No NaN or Infinity values
