# SolarIQ ML Engine

## Current State

**The ML engine is a stub.** The adapter infrastructure is built,
but no trained model is connected. The system falls back to
heuristic solar scoring when no ML model is available.

## Architecture

The ML service uses a **Protocol-based adapter pattern**:

```python
class SolarPredictionModel(Protocol):
    def predict(self, features: dict[str, Any]) -> dict[str, Any]: ...

class MLService:
    def __init__(self, model: SolarPredictionModel | None = None): ...
    @property
    def available(self) -> bool: ...
    def predict(self, features: dict[str, Any]) -> dict[str, Any]: ...
    def predict_if_available(self, features: dict) -> dict | None: ...
```

This allows Person 1 (ML team) to plug in any model that implements
the `predict(features) -> dict` interface without changing the
FastAPI layer.

## How It Works (Now)

1. API request arrives at `/predict-solar` or `/analyze-building`
2. `analyze_surface()` computes heuristic solar score
3. `ml_service.predict_if_available(features)` is called
4. Since `model is None`, it returns `None`
5. Response includes `fallback_score` and `fallback_suitability`

## Integration Path (When Model Is Ready)

To connect a trained model:

```python
from backend.services.ml_service import MLService

class MySolarModel:
    def predict(self, features: dict) -> dict:
        # Your inference code here
        return {"solar_score": 0.85, "confidence": 0.92}

# Set the model at startup
ml_service.model = MySolarModel()
```

The model will then be used for all predictions, with the heuristic
as a fallback if inference fails.

## Features (Input)

When connected, the model receives:

| Feature | Type | Description |
|---------|------|-------------|
| `area_m2` | float | Surface area in square metres |
| `azimuth_deg` | float | Surface azimuth (0–360) |
| `tilt_deg` | float | Surface tilt (0–90) |
| `surface_type` | string | `roof`, `facade`, or `ground` |
| `latitude` | float | Optional site latitude |
| `longitude` | float | Optional site longitude |

## Expected Output

The model should return a dict with at minimum:
```json
{
  "solar_score": 0.85
}
```

Additional fields are passed through to the response.

## Datasets

**No training datasets are included in this repository.**
The sample data in `sample_data/` is synthetic and used for
development/testing only.

For real model training, you would need:
- Historical solar irradiance data per surface orientation
- Building geometry features (area, tilt, azimuth, type)
- Actual energy production measurements (ground truth)

## Model Files

Model files should be stored in the `models/` directory.
See `docs/MODEL_SECURITY.md` for trusted file requirements.

Currently, no model files exist in the repository.

## Limitations

1. **No trained model** — The ML service is a stub with no actual inference
2. **No training data** — No datasets for training are included
3. **No feature engineering pipeline** — Features are passed raw from API input
4. **No model versioning** — The `ModelMetadataModel` ORM exists but is unused
5. **No A/B testing** — Single model slot, no comparison framework
6. **No inference caching** — Each request triggers fresh inference (when model exists)

## What the Heuristic Does (Fallback)

When ML is unavailable, the system uses:

- **50% orientation** — South-facing surfaces score highest
- **30% tilt** — ~20° is considered optimal
- **20% surface type** — Roof surfaces score higher than facades

Energy estimation uses:
```
usable_area = area × coverage_factor (default: 0.80)
capacity_kw = usable_area × panel_efficiency (default: 0.20)
annual_energy = usable_area × irradiance × panel_efficiency
```

These are **baseline engineering estimates**, not ML predictions.
