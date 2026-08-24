# SolarIQ Backend

SolarIQ is the backend component of the SIH1739 project:

> Building Integrated Photo-voltaic (BIPV) potential assessment and visualisation using LOD-1 3D City Model.

This backend is responsible for:

- 3D building geometry processing
- Surface extraction
- Surface area calculation
- Surface normal calculation
- Surface orientation
- Surface tilt
- Roof/facade classification
- Solar suitability scoring
- Baseline energy estimation
- Building-level analysis
- City-level analysis
- Solar surface ranking
- ML model integration interface

---

## Technology

- Python
- FastAPI
- NumPy
- Shapely
- Pydantic
- Pytest

The current MVP uses JSON as the internal representation of LOD-1-style building geometry.

The geometry architecture can later be extended to support:

- GeoJSON
- CityGML
- OBJ
- Other LOD-1 sources

---

# Project Structure

```text
backend/
├── main.py
│
├── api/
│   ├── building.py
│   ├── city.py
│   └── optimization.py
│
├── geometry/
│   ├── parser.py
│   ├── surfaces.py
│   └── calculations.py
│
├── services/
│   ├── solar_service.py
│   └── ml_service.py
│
├── models/
├── schemas/
│   └── building.py
│
├── database/
│
└── tests/
    ├── test_api.py
    ├── test_calculations.py
    ├── test_parser.py
    └── test_surfaces.py