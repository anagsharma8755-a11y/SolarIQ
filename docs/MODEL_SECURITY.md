# SolarIQ ML Model Security Requirements

## Overview

This document specifies the security requirements for loading and
using ML models in the SolarIQ backend. The ML service is designed
to integrate with Person 1's solar prediction model.

## Why Pickle Files Are Not Trusted

Pickle files (`pickle`, `pickle5`, `cloudpickle`) can execute
**arbitrary Python code** during deserialization. An attacker who
can modify a pickle file can achieve **remote code execution (RCE)**
when the model is loaded.

**Never load untrusted pickle files blindly.**

## Trusted Model Format Requirements

Model files MUST meet **all** of the following requirements:

### 1. File Location
- Models MUST be stored within the configured `MODEL_DIR`
  (default: `models/`).
- The directory MUST be read-only to untrusted processes.
- Model paths MUST NOT be configurable via request parameters.

### 2. File Type
Only these formats are accepted:

| Format | Extension | Notes |
|--------|-----------|-------|
| JSON pipeline | `.json` | sklearn exported as JSON (preferred) |
| Joblib | `.joblib` | Acceptable for trusted internal use |
| Pickle | `.pkl` | **Requires explicit trust verification** |

All other extensions are rejected.

### 3. File Integrity
- Model files MUST be regular files (not symlinks).
- File size MUST be logged for audit purposes.
- Consider using checksums (SHA-256) for verified deployments.

### 4. Loading Procedure
When loading any model file:

```python
from backend.security import validate_model_file
from backend.config import MODEL_DIR

# Validate before loading
validated_path = validate_model_file(
    file_path=model_path,
    allowed_root=MODEL_DIR,
)

# Then load with the validated path
# Use joblib.load() for .joblib files
# Use json.load() for .json files
# For .pkl: use ONLY if you have verified the source
```

### 5. Runtime Protection
- The ML model is loaded via the `MLService` adapter pattern.
- If no model is connected, the system gracefully falls back to
  heuristic calculations.
- Model prediction errors are logged internally and never
  exposed to API clients.

## For Person 1 (ML Team)

### Recommended: Export as JSON

If using scikit-learn, export your pipeline as JSON:

```python
import json
from sklearn.pipeline import Pipeline

# Train your pipeline
pipeline = Pipeline([...])
pipeline.fit(X_train, y_train)

# Export as JSON (if using compatible estimators)
model_data = {
    "pipeline_config": pipeline.get_params(),
    "training_metadata": {
        "version": "1.0.0",
        "trained_at": "2025-01-15",
        "features": ["area_m2", "azimuth_deg", "tilt_deg", "surface_type"],
    }
}

with open("models/solar_model.json", "w") as f:
    json.dump(model_data, f)
```

### Alternative: Joblib

```python
import joblib

joblib.dump(pipeline, "models/solar_model.joblib")
```

### What NOT to Do
- Do NOT commit `.pkl` files to version control.
- Do NOT load models from user-uploaded files.
- Do NOT use `exec()` or `eval()` for model loading.
- Do NOT use `pickle.loads()` on untrusted data.

## Verification Checklist

- [ ] Model file is within `MODEL_DIR`
- [ ] Model file is not a symlink
- [ ] Model file extension is trusted (`.json`, `.joblib`, `.pkl`)
- [ ] Model file is from a verified source
- [ ] File size is within expected bounds
- [ ] Loading uses safe deserialization (not raw pickle on untrusted data)
