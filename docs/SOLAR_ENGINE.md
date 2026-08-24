# SolarIQ Solar Engine

## Overview

The solar engine scores building surfaces for BIPV suitability
and estimates energy production potential. It uses a heuristic
model — not a physics-based irradiance simulation.

## Solar Scoring

### Formula

```
solar_score = 0.50 × orientation_score
            + 0.30 × tilt_score
            + 0.20 × surface_type_weight
```

### Components

**Orientation Score** (`orientation_score()`)
- South-facing surfaces score highest (1.0)
- North-facing surfaces score lowest (0.0)
- Roofs receive maximum orientation score (1.0)
- Linear interpolation based on angular distance from south

**Tilt Score** (`tilt_score()`)
- Optimal tilt: ~20° (MVP heuristic)
- Score decreases linearly with distance from 20°
- Range: 0.0 (90° tilt) to 1.0 (20° tilt)

**Surface Type Weight**
- Roof: 1.0
- Facade: 0.65
- Ground: score = 0.0 (excluded from analysis)

### Suitability Labels

| Score Range | Label |
|-------------|-------|
| ≥ 0.75 | `high` |
| 0.50 – 0.74 | `medium` |
| < 0.50 | `low` |

## Energy Estimation

### Formula

```
usable_area      = surface_area × coverage_factor
capacity_kw      = usable_area × panel_efficiency
annual_energy_kwh = usable_area × annual_irradiance × panel_efficiency
```

### Defaults (Configurable via Environment Variables)

| Parameter | Default | Env Var |
|-----------|---------|---------|
| Coverage factor | 0.80 | `SOLARIQ_COVERAGE_FACTOR` |
| Panel efficiency | 0.20 | `SOLARIQ_PANEL_EFFICIENCY` |
| Annual irradiance | 1700 kWh/m² | `SOLARIQ_ANNUAL_IRRADIANCE` |
| Performance ratio | 0.85 | `SOLARIQ_PERFORMANCE_RATIO` |

### Ground Surfaces

Ground surfaces always return zero energy:
```json
{
  "usable_area_m2": 0.0,
  "estimated_capacity_kw": 0.0,
  "estimated_annual_energy_kwh": 0.0
}
```

## Important Caveats

1. **This is NOT a scientific irradiance model.** The scoring uses
   simple geometric heuristics, not TMY data, horizon analysis,
   or PV simulation.

2. **The 20° optimal tilt is a rough approximation.** Actual optimal
   tilt depends on latitude, season, and local conditions.

3. **Coverage factor and panel efficiency are global defaults.** Real
   installations vary significantly by panel technology and roof
   geometry.

4. **Annual irradiance (1700 kWh/m²) is a mid-latitude average.**
   Actual values range from ~1000 (northern Europe) to ~2500
   (desert regions).

5. **No shading, soiling, or temperature derating is applied.**
   The `PERFORMANCE_RATIO` config exists but is not used in the
   current energy calculation.

## What Would Make This More Accurate

- Site-specific irradiance data (PVGIS, NSRDB, etc.)
- Actual panel specifications (STC ratings, temperature coefficients)
- Shading analysis from surrounding geometry
- Inverter efficiency curves
- System sizing optimization

These are out of scope for the current MVP.
