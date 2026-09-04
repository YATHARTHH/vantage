# Vantage Production Deployment, CI/CD, Cloud Scalability, & SRE Operations

## 1. Production Containerization Reference

### Multi-Stage `Dockerfile`
Vantage uses a multi-stage Docker build to keep production image sizes under 150MB while ensuring static frontend asset compilation.

```dockerfile
# Stage 1: Build Frontend SPA Assets
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Backend Dependencies & Code
COPY pyproject.toml README.md ./
COPY vantage/ ./vantage/
RUN pip install --no-cache-dir -e .

# Copy Compiled Frontend SPA Assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/ready || exit 1

CMD ["python", "-m", "uvicorn", "vantage.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml` Stack Definition
```yaml
version: '3.8'

services:
  vantage-server:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - VANTAGE_ENV=production
      - VANTAGE_DEBUG=false
      - VANTAGE_DATABASE_URL=sqlite+aiosqlite:////app/data/vantage.db
      - VANTAGE_DUCKDB_PATH=/app/data/vantage.duckdb
    volumes:
      - vantage_data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ready"]
      interval: 10s
      timeout: 5s
      retries: 3

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  vantage_data:
  grafana_data:
```

---

## 2. GitHub Actions CI/CD Pipeline (`.github/workflows/ci.yml`)

```yaml
name: Vantage CI/CD Pipeline

on:
  push:
    branches: [ master, main ]
  pull_request:
    branches: [ master, main ]

jobs:
  quality-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Codebase
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy pytest pytest-cov
          pip install -e .

      - name: Code Linting (Ruff)
        run: ruff check vantage/ tests/

      - name: Type Checking (Mypy)
        run: mypy vantage/ --ignore-missing-imports

      - name: Execute Automated Test Suite (Pytest)
        run: |
          pytest tests/ --cov=vantage --cov-report=xml -v

      - name: Build Frontend SPA
        uses: actions/setup-node@v4
        with:
          node-version: "18"
        with:
          run: |
            cd frontend
            npm ci
            npm run build
```

---

## 3. High-Throughput Cloud Architecture (1,000,000 Requests/Day)

To scale Vantage from a single-instance deployment to high-throughput enterprise scale (handling >1,000,000 telemetry spans and tool evaluations daily), the target cloud architecture separates stateless API nodes from async worker pools and distributed analytical engines:

```text
                                 ENTERPRISE CLIENT TRAFFIC (1M+ req/day)
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │   Cloud API Gateway (Kong)    │
                                    │   WAF & TLS Termination       │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ Kubernetes Cluster (HPA Pods) │
                                    │ FastAPI Stateless Workers     │
                                    └───────────────┬───────────────┘
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   ▼                                                                 ▼
    ┌───────────────────────────────┐                               ┌───────────────────────────────┐
    │ Redis Cluster (Pub/Sub & Cache│                               │ Managed Distributed OLAP      │
    │ & Celery Task Queue Broker)   │                               │ (ClickHouse Cloud Cluster)    │
    └───────────────┬───────────────┘                               └───────────────┬───────────────┘
                    │                                                               │
                    ▼                                                               ▼
    ┌───────────────────────────────┐                               ┌───────────────────────────────┐
    │ Managed Relational Database   │                               │ Security & Compliance         │
    │ (AWS Aurora PostgreSQL HA)    │                               │ Immutable S3 Parquet Storage  │
    └───────────────────────────────┘                               └───────────────────────────────┘
```

### Key Scaling Transformations
1. **Stateless API Scale-Out**: Deploy FastAPI pods in Kubernetes managed by Horizontal Pod Autoscaler (HPA) targeting 70% CPU/Memory utilization.
2. **Ingestion Buffer Migration**: Replace in-memory ring buffers with high-throughput Redis Streams or Apache Kafka topics capable of ingesting 100,000 spans/second.
3. **OLAP Storage Migration**: Transition DuckDB (ideal for embedded single-node analytics) to a multi-node ClickHouse cluster for petabyte-scale telemetry queries.
4. **Relational Database High Availability**: Migrate SQLite to AWS Aurora PostgreSQL with multi-AZ failover and read-replicas.

---

## 4. SRE Operations & Incident Runbooks

### Health Probes & SLA Indicators
- `/health` Endpoint: Liveness probe. Returns HTTP 200 `{"status": "healthy"}` if the Python application process is responsive.
- `/ready` Endpoint: Readiness probe. Returns HTTP 200 `{"status": "ready"}` if DuckDB and SQLite database connection pools are active. Returns HTTP 503 if database storage is unavailable.

### Service Level Objectives (SLOs)
- **Ingestion Availability**: $99.95\%$ uptime for `/api/v1/otlp/v1/traces`.
- **Policy Enforcement Latency**: p99 overhead <= 3 ms for `ExecutionController.execute()`.
- **Telemetry Processing Losslessness**: Zero span loss under normal operating parameters; $< 0.001\%$ DLQ overflow rate under extreme spikes.

### Operational Incident Runbooks

#### Runbook 1: Ingestion Buffer Overflow (DLQ Spikes)
1. **Symptom**: Alert fires for elevated Dead-Letter Queue writes (`.dlq_spans.jsonl` size increasing).
2. **Diagnosis**: Check log outputs for storage write timeouts or disk I/O exhaustion using `tail -n 100 .dlq_spans.jsonl`.
3. **Mitigation**:
   - Verify DuckDB lock state and disk space availability.
   - Scale out API worker threads or increase `max_capacity` buffer threshold.
   - Re-ingest failed DLQ spans using `python scripts/reingest_dlq.py`.

#### Runbook 2: Cryptographic Audit Hash Chain Tampering
1. **Symptom**: `GET /api/v1/audit/logs` returns `chain_valid = false` with error message indicating broken hash link at `entry_id = N`.
2. **Diagnosis**: Inspect database access logs to identify unauthorized direct SQL `UPDATE` or `DELETE` operations on `audit_logs`.
3. **Mitigation**:
   - Immediately revoke API keys associated with the actor key recorded at entry $N$.
   - Export cold storage backup of audit log tables for forensic analysis.
   - Restore database to last verified valid hash checkpoint.
