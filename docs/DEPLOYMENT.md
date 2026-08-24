# SolarIQ Backend Deployment Guide

## Quick Start (Local)

### Prerequisites
- Python 3.12+
- pip

### Steps

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd solariq

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment config
cp .env.example .env

# 5. Start the server
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The API is now available at:
- **API**: http://127.0.0.1:8000
- **Interactive docs**: http://127.0.0.1:8000/docs
- **Health check**: http://127.0.0.1:8000/health

### Verify

```bash
curl http://127.0.0.1:8000/health
# {"status":"healthy","version":"0.1.0"}

curl http://127.0.0.1:8000/status
# Full status with database, services, paths
```

---

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose v2 (optional)

### Build and Run (Standalone)

```bash
# Build the image
docker build -t solariq-backend .

# Run the container
docker run -d \
  --name solariq \
  -p 8000:8000 \
  -e SOLARIQ_ENV=production \
  -e SOLARIQ_LOG_LEVEL=INFO \
  solariq-backend

# Verify
curl http://localhost:8000/health

# View logs
docker logs -f solariq

# Stop
docker stop solariq
```

### Docker Compose (Recommended for Local Dev)

```bash
# Start with hot-reload
docker compose up

# Rebuild after dependency changes
docker compose up --build

# Stop and remove
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Volume Mounts

For production, mount data and model directories:

```bash
docker run -d \
  --name solariq \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -v /path/to/models:/app/models \
  solariq-backend
```

---

## Configuration

All configuration is via environment variables. See `.env.example`
for the complete list with descriptions.

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOLARIQ_ENV` | `development` | `development`, `testing`, or `production` |
| `SOLARIQ_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` in containers) |
| `SOLARIQ_PORT` | `8000` | Server port |
| `SOLARIQ_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SOLARIQ_DATABASE_URL` | `sqlite:///solariq.db` | SQLAlchemy database URL |
| `SOLARIQ_CORS_ORIGINS` | `*` | Comma-separated allowed origins |

### Environment Profiles

#### Development
```bash
SOLARIQ_ENV=development
SOLARIQ_LOG_LEVEL=DEBUG
# Human-readable colored logs, hot-reload enabled
```

#### Testing
```bash
SOLARIQ_ENV=testing
SOLARIQ_LOG_LEVEL=WARNING
SOLARIQ_DATABASE_URL=sqlite://
# In-memory database, minimal logging
```

#### Production
```bash
SOLARIQ_ENV=production
SOLARIQ_LOG_LEVEL=INFO
SOLARIQ_DATABASE_URL=postgresql://user:pass@host:5432/solariq
SOLARIQ_CORS_ORIGINS=https://app.solariq.io
# JSON-structured logs, restricted CORS, PostgreSQL
```

---

## Health Endpoints

### GET /health
Lightweight check for load balancers and orchestrators.
Returns `200` if the process is alive. No external dependencies checked.

### GET /status
Detailed status for monitoring:
- **services**: geometry, solar, optimization engines, ML engine, database
- **paths**: data, model, and processed directories with accessibility check
- **environment**: current SOLARIQ_ENV value

### Docker HEALTHCHECK
The Dockerfile includes a built-in healthcheck that polls `/health`
every 30 seconds. Docker and orchestrators (ECS, Kubernetes) use
this to determine container health.

---

## Logging

### Development
Human-readable colored output to stderr:
```
22:10:15 INFO     backend.main   SolarIQ Backend 0.1.0
22:10:15 INFO     backend.main   Environment: development
22:10:40 INFO     backend.main GET /status -> 200 (645ms)
```

### Production
Structured JSON to stderr (one JSON object per line):
```json
{"timestamp":"2025-01-23T22:10:40+00:00","level":"INFO","logger":"backend.main","message":"GET /status -> 200 (645ms)","method":"GET","path":"/status","status_code":200,"duration_ms":645}
```

### What Gets Logged
- Request method, path, status code, and duration
- Startup configuration (environment, directories, database)
- Slow requests (>5 seconds)
- Errors and exceptions (with sanitized messages)

### What Does NOT Get Logged
- API keys or credentials
- Request/response bodies
- Full geometry payloads
- Database passwords (masked in URLs)

---

## Production Checklist

### Before Deploying

- [ ] Set `SOLARIQ_ENV=production`
- [ ] Set `SOLARIQ_LOG_LEVEL=INFO` (or `WARNING`)
- [ ] Configure `SOLARIQ_DATABASE_URL` for PostgreSQL
- [ ] Set `SOLARIQ_CORS_ORIGINS` to specific frontend domains
- [ ] Mount `data/` and `models/` as persistent volumes
- [ ] Ensure `models/` directory contains trusted model files only
- [ ] Review request limits (`SOLARIQ_MAX_BUILDINGS`, etc.)

### Running with Multiple Workers

For production throughput, run multiple uvicorn workers:

```bash
uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

Rule of thumb: `workers = 2 * CPU_cores + 1`

### Reverse Proxy (Nginx/Caddy)

Place a reverse proxy in front for TLS termination:

```nginx
# Nginx example
server {
    listen 443 ssl;
    server_name api.solariq.io;

    ssl_certificate /etc/ssl/certs/solariq.pem;
    ssl_certificate_key /etc/ssl/private/solariq.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Future Cloud Deployment

### AWS (ECS Fargate)

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag solariq-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/solariq-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/solariq-backend:latest

# Task definition uses the image, environment variables, and
# health check from the Dockerfile.
```

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/<project>/solariq-backend
gcloud run deploy solariq-backend \
  --image gcr.io/<project>/solariq-backend \
  --port 8000 \
  --set-env-vars SOLARIQ_ENV=production
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: solariq-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: solariq-backend
  template:
    metadata:
      labels:
        app: solariq-backend
    spec:
      containers:
      - name: backend
        image: solariq-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: SOLARIQ_ENV
          value: "production"
        - name: SOLARIQ_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: solariq-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: models
          mountPath: /app/models
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: solariq-data
      - name: models
        persistentVolumeClaim:
          claimName: solariq-models
```

---

## Running Tests

```bash
# Full test suite
python -m pytest -q

# With coverage
python -m pytest --cov=backend --cov-report=term-missing

# Security tests only
python -m pytest tests/test_security.py -v

# Performance profiling
python scripts/profile_performance.py
```

---

## File Structure

```
solariq/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Centralized configuration
│   ├── logging_config.py    # Structured logging setup
│   ├── security.py          # Security utilities
│   ├── api/                 # API route handlers
│   ├── services/            # Business logic
│   ├── geometry/            # Geometry computation
│   ├── schemas/             # Pydantic models
│   └── db/                  # Database layer
├── data_pipeline/           # Data ingestion pipeline
├── tests/                   # Test suite
├── docs/                    # Documentation
├── Dockerfile               # Container build
├── docker-compose.yml       # Local dev compose
├── .dockerignore            # Build context exclusions
├── .env.example             # Environment variable template
├── .gitignore               # Git exclusions
├── requirements.txt         # Pinned dependencies
└── pytest.ini               # Test configuration
```
