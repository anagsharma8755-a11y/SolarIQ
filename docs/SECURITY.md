# SolarIQ Backend Security Audit

**Date:** 2025-01-23
**Auditor:** Buffy (Security Engineer)
**Scope:** Backend API, data pipeline, file handling, model loading

---

## Executive Summary

The SolarIQ backend had a **medium-risk** security posture before this
audit. The codebase was well-structured with Pydantic validation on
all API endpoints and no direct use of `pickle` or `eval`. However,
several gaps existed in file handling, error exposure, and secrets
management. All identified issues have been addressed with reasonable
mitigations.

**Risk rating after fixes: LOW**

---

## Findings & Mitigations

### 1. Secrets Management — HIGH PRIORITY ✅ FIXED

**Finding:** No `.gitignore` existed. Environment files, database
files, model artifacts, and `__pycache__` could be committed to
version control.

**Mitigation:**
- Created `.gitignore` covering `.env`, `*.db`, `models/*.pkl`,
  `models/*.joblib`, `__pycache__`, and other sensitive artifacts.
- No `.env` files were found committed (good baseline).

### 2. Path Traversal in File Loaders — HIGH PRIORITY ✅ FIXED

**Finding:** File loaders in `backend/geometry/parser.py`,
`data_pipeline/osm/geojson_loader.py`, `data_pipeline/solar/loader.py`,
and `data_pipeline/weather/loader.py` accepted arbitrary file paths
without validating they stayed within expected directories. An attacker
could use `../../etc/passwd` to read arbitrary files.

**Mitigation:**
- Created `backend/security.py` with `validate_path_within()` function
  that resolves symlinks and verifies the canonical path stays within
  an allowed root directory.
- Applied path validation to all file loading functions in the backend
  and data pipeline.
- Added symlink rejection to prevent symlink-based traversal attacks.

### 3. Unbounded HTTP Response Downloads — MEDIUM PRIORITY ✅ FIXED

**Finding:** External API calls to Overpass, PVGIS, and Open-Meteo
read responses without size limits. A malicious or compromised API
could return a multi-GB response causing memory exhaustion (DoS).

**Mitigation:**
- Added `MAX_OVERPASS_RESPONSE_SIZE` (50 MB) to OSM downloader.
- Added `MAX_API_RESPONSE_SIZE` (10 MB) to PVGIS and Open-Meteo
  providers.
- All HTTP responses are now size-limited before `json.loads()`.

### 4. Oversized Local File Loading — MEDIUM PRIORITY ✅ FIXED

**Finding:** Local CSV and JSON files were loaded without size checks.
A 1 GB JSON file could exhaust memory.

**Mitigation:**
- Added `_MAX_FILE_SIZE` (200 MB) checks to all local file loaders
  in `data_pipeline/weather/loader.py` and `data_pipeline/solar/loader.py`.
- Added 100 MB limit to `backend/geometry/parser.py`.
- Added 100 MB limit to `backend/security.py::safe_load_json()`.

### 5. Symlink-Based Attacks — MEDIUM PRIORITY ✅ FIXED

**Finding:** Symlinked files could be used to bypass path restrictions
or load untrusted content from outside the expected directory.

**Mitigation:**
- All file loaders now reject symlinks with explicit error messages.
- `validate_model_file()` rejects symlinked model files.

### 6. Error Message Information Disclosure — MEDIUM PRIORITY ✅ FIXED

**Finding:** The ML prediction endpoint leaked internal error details
to API clients via `f"ML prediction failed: {exc}"`. Runtime and
generic exception handlers did not log errors internally.

**Mitigation:**
- Sanitized ML prediction error message to generic "ML prediction
  failed." with internal logging for debugging.
- Added `logger.error()` calls to `RuntimeError` and `Exception`
  handlers so errors are logged server-side without being exposed.

### 7. Missing Security Headers — LOW PRIORITY ✅ FIXED

**Finding:** No security headers were set on API responses.

**Mitigation:**
- Added HTTP middleware that sets:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Cache-Control: no-store, no-cache, must-revalidate`
  - `Pragma: no-cache`
  - `X-Response-Time` for observability
- Logs slow requests (>5s) for monitoring.

### 8. Missing CORS Configuration — LOW PRIORITY ✅ FIXED

**Finding:** No CORS middleware was configured. By default, FastAPI
allows all origins, but this should be explicit.

**Mitigation:**
- Added `CORSMiddleware` with explicit configuration:
  - `allow_origins=["*"]` (TODO: restrict in production)
  - `allow_credentials=False`
  - `allow_methods=["GET", "POST"]`
  - `allow_headers=["*"]`
  - `max_age=600`

### 9. Untrusted Pickle Loading Risk — MEDIUM PRIORITY ✅ MITIGATED

**Finding:** The ML service uses a `Protocol` interface, not pickle.
However, if a future implementation uses pickle for model loading,
it could enable arbitrary code execution.

**Mitigation:**
- Created `docs/MODEL_SECURITY.md` documenting:
  - Why pickle files are not trusted
  - Trusted model file requirements (location, extension, integrity)
  - Safe loading procedures
  - Instructions for Person 1 (ML team)
- Created `validate_model_file()` in `backend/security.py` that:
  - Restricts model paths to `MODEL_DIR`
  - Only allows trusted extensions (`.json`, `.joblib`)
  - Rejects symlinks
  - Logs file metadata for audit

### 10. CSV Injection — LOW PRIORITY ✅ MITIGATED

**Finding:** CSV files processed by pandas could contain formula
injection payloads (`=SUM(...)`, `+cmd`, etc.) that execute when
opened in spreadsheet applications.

**Mitigation:**
- Created `sanitize_csv_value()` in `backend/security.py` that
  prefixes dangerous values with a single quote.
- Documented the OWASP CSV Injection reference.

### 11. No Request Logging/Observability — LOW PRIORITY ✅ FIXED

**Finding:** No request timing or slow-request detection.

**Mitigation:**
- Added `X-Response-Time` header and slow-request warning logging
  in the security middleware.

### 12. Bounding Box Validation in Downloads — LOW PRIORITY ✅ FIXED

**Finding:** The OSM downloader accepted latitude/longitude values
without range validation. Invalid values could cause unexpected
API behavior.

**Mitigation:**
- Added `validate_bbox()` to `backend/security.py`.
- Added bounding box validation in `data_pipeline/osm/downloader.py`
  before constructing the Overpass query.

---

## Pre-existing Good Practices (No Changes Needed)

1. **Pydantic validation on all API endpoints** — All request/response
   models use strict field constraints (`ge`, `le`, `max_length`,
   `min_length`, `pattern`).

2. **No use of `eval()` or `exec()`** — The codebase does not use
   dynamic code execution anywhere.

3. **No pickle loading** — The ML service uses a Protocol-based
   adapter pattern, not pickle deserialization.

4. **JSON parsing uses `json.load()`/`json.loads()`** — Standard
   library JSON parsing (not `yaml.load()` or custom deserializers).

5. **Error handlers on all exceptions** — FastAPI has catch-all
   handlers that prevent stack trace leakage.

6. **SQLAlchemy ORM** — Database access uses parameterized queries
   via the ORM, preventing SQL injection.

7. **Path safety in geometry parser** — Basic file existence and
   extension checks were already in place (enhanced with symlink
   rejection and size limits).

---

## Dependency Analysis

### requirements.txt Review

```
fastapi        — Web framework (actively maintained)
uvicorn        — ASGI server
numpy          — Numerical computation
shapely        — Geometry operations
pydantic       — Data validation
pytest         — Testing
httpx          — HTTP client (used by FastAPI testclient)
pyproj         — Coordinate projections
pandas         — Data processing
sqlalchemy     — ORM
```

**Assessment:** All packages are well-maintained and commonly used.
No unnecessary packages detected. No blind upgrades recommended
without testing.

---

## Testing

### Security Test Coverage

Created `tests/test_security.py` with 56 tests covering:

| Test Class | Tests | What's Tested |
|-----------|-------|---------------|
| `TestPathTraversal` | 4 | Path traversal via `../`, absolute escapes, symlinks |
| `TestSafeLoadJson` | 6 | Size limits, path traversal, invalid JSON, bytes |
| `TestCSVInjection` | 9 | Formula prefix detection (`=`, `+`, `-`, `@`, `\t`, `\r`) |
| `TestFilenameSanitization` | 5 | Path separators, null bytes, dots, empty names |
| `TestBboxValidation` | 7 | Lat/lon range, south>north, west>east |
| `TestCoordinateValidation` | 3 | Lat/lon bounds |
| `TestModelTrust` | 5 | Extension, symlink, path traversal, nonexistent |
| `TestAPISecurity` | 7 | Headers, error sanitization, building limits, XSS |
| `TestSchemaValidation` | 6 | Empty IDs, long IDs, vertex count, azimuth, tilt, area |
| `TestJSONSafety` | 2 | Prototype pollution, deep nesting |
| `TestGeometryParserSecurity` | 2 | Symlink rejection, oversized file rejection |

### Test Results

```
53 passed, 3 skipped (Windows symlink privilege limitation), 1 warning
Full suite: 583 passed, 1 pre-existing failure, 3 skipped
```

---

## Architecture Notes

### Request Flow Security

```
Client Request
    ↓
CORSMiddleware (origin/method validation)
    ↓
Security Headers Middleware (nosniff, DENY, cache control)
    ↓
FastAPI Request Validation (Pydantic, size limits)
    ↓
Route Handler (business logic)
    ↓
Error Handlers (sanitize all errors)
    ↓
Response (with security headers)
```

### File Loading Security Chain

```
User/Script Input Path
    ↓
resolve() (canonical path)
    ↓
validate_path_within() (path traversal check)
    ↓
is_symlink() check (symlink rejection)
    ↓
stat().st_size check (size limit)
    ↓
Extension check (trusted formats only)
    ↓
json.load() / pd.read_csv() (safe deserialization)
```

---

## Recommendations for Future Work

1. **Production CORS:** Replace `allow_origins=["*"]` with specific
   frontend origins.

2. **API Authentication:** If the API moves beyond internal use,
   add API key or OAuth2 authentication.

3. **Rate Limiting:** Add per-IP rate limiting to prevent abuse.

4. **Request Body Size Middleware:** Configure FastAPI's maximum body
   size at the server level (uvicorn/hypercorn).

5. **Model Checksum Verification:** Store SHA-256 checksums for
   deployed model files and verify before loading.

6. **Security Headers CSP:** Add Content-Security-Policy header if
   serving any HTML content.

7. **Audit Logging:** Add structured audit logging for all API
   requests and file operations.

---

## Files Modified

| File | Changes |
|------|---------|
| `.gitignore` | **Created** — Secrets, caches, model artifacts |
| `backend/security.py` | **Created** — Security utilities module |
| `backend/main.py` | CORS, security middleware, error logging |
| `backend/api/prediction.py` | Sanitized ML error messages |
| `backend/geometry/parser.py` | Symlink rejection, size limit |
| `data_pipeline/osm/downloader.py` | Bbox validation, response size limit, file validation |
| `data_pipeline/osm/geojson_loader.py` | Response size limit, file validation |
| `data_pipeline/solar/loader.py` | File validation, size limit |
| `data_pipeline/solar/providers.py` | API response size limit, file validation |
| `data_pipeline/weather/loader.py` | File validation, size limit |
| `data_pipeline/weather/providers.py` | API response size limit, file validation |
| `data_pipeline/pipeline/city_pipeline.py` | File validation in `load_for_backend()` |
| `docs/MODEL_SECURITY.md` | **Created** — Trusted model requirements |
| `tests/test_security.py` | **Created** — 56 security-focused tests |
