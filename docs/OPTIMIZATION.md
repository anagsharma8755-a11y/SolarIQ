# SolarIQ Optimization Engine

## Overview

The optimization engine ranks building surfaces by solar suitability
using a transparent, multi-factor weighted scoring system. Every
ranking decision is explainable and deterministic.

## Scoring Formula

```
composite = w₁ × suitability_score
          + w₂ × energy_score
          + w₃ × capacity_score
          + w₄ × area_score
          + w₅ × orientation_score
```

Each component is normalized to [0, 1] before weighting.

## Default Weights

| Factor | Weight | Configurable Via |
|--------|--------|-----------------|
| Suitability | 0.35 | `SOLARIQ_OPT_WEIGHT_SUITABILITY` |
| Energy | 0.25 | `SOLARIQ_OPT_WEIGHT_ENERGY` |
| Capacity | 0.15 | `SOLARIQ_OPT_WEIGHT_CAPACITY` |
| Area | 0.15 | `SOLARIQ_OPT_WEIGHT_AREA` |
| Orientation | 0.10 | `SOLARIQ_OPT_WEIGHT_ORIENTATION` |

Weights are normalized at runtime to sum to exactly 1.0.

## Pipeline Steps

1. **Extract surfaces** from all input buildings
2. **Analyze** each surface (solar score, energy potential)
3. **Filter** out ground surfaces
4. **Apply constraints** (min score, min area, surface type whitelist)
5. **Compute normalization bounds** from the filtered set
6. **Score** each surface with the composite formula
7. **Sort** by composite score (descending), then energy, then area
8. **Apply limits** (max surfaces, max cumulative capacity)
9. **Generate recommendations** — human-readable explanations
10. **Aggregate** city-level metrics

## Recommendation Generation

Each ranked surface receives a deterministic explanation:

```
Top-ranked surface; high solar suitability score; near-optimal tilt (20°);
horizontal roof surface; large usable area (320 m²); significant capacity
(64.0 kW); high annual yield (544,000 kWh/yr).
```

The recommendation highlights:
- Rank position (Top, #2, #3, etc.)
- Solar suitability level
- Tilt quality (near-optimal, acceptable, suboptimal)
- Orientation quality (favorable south-facing, moderate, north-facing)
- Area significance (large, moderate)
- Capacity significance
- Annual yield significance

## Constraint Filtering

| Constraint | Type | Applied When |
|------------|------|-------------|
| `min_solar_score` | float | Before scoring |
| `min_usable_area_m2` | float | Before scoring |
| `surface_types` | list[str] | Before scoring |
| `max_surfaces` | int | After sorting |
| `max_total_capacity_kw` | float | After sorting |

## City-Level Aggregation

The optimizer produces city-level summaries:

| Metric | Description |
|--------|-------------|
| `total_suitable_area_m2` | Sum of usable areas across ranked surfaces |
| `total_potential_capacity_kw` | Sum of estimated capacities |
| `total_annual_energy_kwh` | Sum of annual energy estimates |
| `top_buildings` | Building IDs sorted by total capacity |
| `top_surfaces` | Surface IDs in rank order (top 20) |

## Transparency

The optimization is designed for **explainability**:
- All weights are public and configurable
- The scoring formula is documented
- Each surface gets a human-readable recommendation
- Normalization bounds are computed from the actual dataset
- No hidden parameters or learned weights
