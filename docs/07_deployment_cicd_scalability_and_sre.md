# Vantage Production Deployment, CI/CD, Cloud Scalability, & SRE Operations

Welcome to **Document 07**! This document explains how Vantage is packaged for production, how the automated CI/CD pipeline works, how to scale it for enterprise traffic, and how to respond when things go wrong.

---

## ❓ Why Do We Use Docker? (Simple Explanation)

Without Docker, every server that runs Vantage would need:
- Python 3.12+ installed manually
- Node.js 18+ installed manually
- All Python packages installed in the right versions
- All frontend npm packages installed
- The correct environment variables configured

This is error-prone and slow. Docker solves this by **packaging everything into a single, self-contained image** — the application, all its dependencies, and the exact runtime version — so you can deploy to any server with a single command.

> 💡 **Simple Analogy**: Docker is like shipping a product in a box with all batteries included and instructions pre-applied. No assembly required on the other end.

---

## 1. Production Containerization Reference

### Multi-Stage `Dockerfile`
Vantage uses a **2-stage Docker build** to keep production image sizes under 150MB while ensuring static frontend asset compilation.

#### Why 2 Stages?
- **Stage 1 (Frontend Builder)**: Uses a `node:18-alpine` image to compile the React TypeScript frontend into static HTML/CSS/JS files. Node.js is only needed during *build time* — we do NOT want to ship Node.js in the final production image (it would add ~200MB unnecessarily).
- **Stage 2 (Python Runner)**: Uses a minimal `python:3.12-slim` image containing only the Python runtime and backend code. The compiled frontend files are **copied** from Stage 1 into this image using `COPY --from=frontend-builder`. The final production image contains:
  - Python 3.12-slim (no Node.js, no npm)
  - Vantage backend code
  - Pre-compiled frontend static files
  - All Python dependencies
  - Result: < 150MB total image size

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

### What is CI/CD and Why Do We Use It?
**CI (Continuous Integration)** means every time a developer pushes code to GitHub, an automated pipeline immediately:
1. Runs all 69 Pytest tests
2. Checks code style with Ruff (linting)
3. Verifies type safety with Mypy
4. Builds the frontend production bundle

If any step fails, the pull request is blocked from merging. This prevents broken code from ever reaching the `master` branch.

**CD (Continuous Deployment)** means a successful CI run can automatically trigger a deployment to a staging or production environment.

> 💡 **Why this matters**: Without CI/CD, a developer could accidentally push code that breaks a security check, removes a test, or causes a type error — and nobody would know until a user is affected.

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
        # Checks code style and catches common errors (unused imports, etc.)
        run: ruff check vantage/ tests/

      - name: Type Checking (Mypy)
        # Verifies type annotations are correct across the entire codebase
        run: mypy vantage/ --ignore-missing-imports

      - name: Execute Automated Test Suite (Pytest)
        # Runs all 69 tests and generates a coverage XML report
        run: |
          pytest tests/ --cov=vantage --cov-report=xml -v

      - name: Build Frontend SPA
        # Installs Node.js and compiles the React frontend
        uses: actions/setup-node@v4
        with:
          node-version: "18"

      - name: npm install and build
        run: |
          cd frontend
          npm ci
          npm run build
```

### What Each CI Step Checks

| Step | Tool | What It Catches | Failure Means |
|:-----|:-----|:----------------|:--------------|
| Linting | Ruff | Style violations, unused imports, undefined names | Code quality issue — fix before merging |
| Type Checking | Mypy | Type mismatches, wrong function signatures | Logic error — could cause runtime bugs |
| Tests | Pytest | Security check failures, broken logic, regression bugs | A feature is broken — must fix before merging |
| Frontend Build | npm | TypeScript compile errors, missing dependencies | Frontend broken — users can't load the UI |

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

### Cloud Migration Checklist
When you outgrow the single-instance deployment and need to scale to enterprise cloud, follow this step-by-step migration path:

| Step | What to Change | From | To | Why |
|:-----|:---------------|:-----|:---|:----|
| **1** | Telemetry OLAP storage | DuckDB (embedded) | ClickHouse Cloud cluster | DuckDB is single-node; ClickHouse handles petabyte-scale distributed queries |
| **2** | Metadata OLTP storage | SQLite (file-based) | AWS Aurora PostgreSQL (HA) | Aurora has multi-AZ failover, automatic backups, and read replicas |
| **3** | Ingestion buffer | In-memory deque | Redis Streams or Apache Kafka | Distributed buffer survives pod restarts; handles 100K+ spans/sec across pods |
| **4** | API runtime | Single Uvicorn process | Kubernetes HPA (Horizontal Pod Autoscaler) | Auto-scales pods based on CPU/memory load |
| **5** | API gateway | Direct HTTP | Kong or AWS API Gateway with WAF | Adds rate limiting, TLS termination, DDoS protection before traffic hits pods |
| **6** | Audit log storage | SQLite table | Immutable S3 Parquet + CloudTrail | Regulatory-grade immutability for SOC2/HIPAA compliance |

Configuration changes for each step are isolated to the `.env` file (`VANTAGE_DATABASE_URL`, `VANTAGE_DUCKDB_PATH`) and `docker-compose.yml` — no application code changes needed.

---

## 4. SRE Operations & Incident Runbooks

### What is SRE?
**SRE (Site Reliability Engineering)** is the practice of making sure a production system stays healthy, recovers quickly from failures, and meets its performance targets. SRE engineers write **runbooks** — step-by-step response guides for the most common failure scenarios, so that when something breaks at 3 AM, there is a clear procedure to follow.

### Health Probes & SLA Indicators
- `/health` Endpoint: Liveness probe. Returns HTTP 200 `{"status": "healthy"}` if the Python application process is responsive.
- `/ready` Endpoint: Readiness probe. Returns HTTP 200 `{"status": "ready"}` if DuckDB and SQLite database connection pools are active. Returns HTTP 503 if database storage is unavailable.

### Service Level Objectives (SLOs)

SLOs define the minimum performance standards that Vantage must meet. They are measured continuously and trigger alerts if breached:

| SLO | Target | How It Is Measured | What Triggers an Alert |
|:----|:-------|:-------------------|:-----------------------|
| **Ingestion Availability** | 99.95% uptime for `/api/v1/otlp/v1/traces` | Uptime monitoring every 30 seconds (e.g. Grafana, UptimeRobot) | 3 consecutive failed health checks → PagerDuty alert |
| **Policy Enforcement Latency** | p99 overhead ≤ 3ms for `ExecutionController.execute()` | Prometheus histogram metric `vantage_policy_check_duration_ms` | If p99 > 3ms for 5 consecutive minutes → warning alert |
| **Telemetry Losslessness** | < 0.001% DLQ overflow rate | Monitor `.dlq_spans.jsonl` file growth rate | If DLQ grows by > 100 spans/min → critical alert (ingestion falling behind) |

### Operational Incident Runbooks

#### Runbook 1: Ingestion Buffer Overflow (DLQ Spikes)
**Symptom**: Alert fires for elevated Dead-Letter Queue writes (`.dlq_spans.jsonl` growing rapidly).

**What This Means**: The in-memory ingestion buffer (`max_capacity = 10,000 spans`) is filling faster than the background async flusher can write to DuckDB. Incoming spans are overflowing to disk.

**Diagnosis & Mitigation**:
1. Check log outputs for write timeouts or disk I/O exhaustion:
   ```bash
   tail -n 100 .dlq_spans.jsonl
   ```
2. Check available disk space: `df -h /app/data`
3. Verify DuckDB lock state (another process may have the file open).
4. Scale out worker threads or increase `max_capacity` in `vantage/ingest/buffer.py`.
5. Re-ingest failed DLQ spans after resolving the bottleneck:
   ```bash
   python scripts/reingest_dlq.py
   ```

---

#### Runbook 2: Cryptographic Audit Hash Chain Tampering
**Symptom**: `GET /api/v1/audit/logs` returns `chain_valid: false` with a broken hash link at `entry_id = N`.

**What This Means**: Someone directly modified or deleted a row in the `audit_logs` SQLite table, breaking the SHA-256 hash chain. This is a serious security incident.

**Diagnosis & Mitigation**:
1. Inspect database access logs for unauthorized direct SQL `UPDATE` or `DELETE` on `audit_logs`.
2. Immediately revoke API keys associated with the `actor_key_id` at broken entry `N`.
3. Export a cold storage backup of audit log tables for forensic analysis.
4. Restore the database to the last verified valid hash checkpoint.
5. File a security incident report — this may indicate a compromised admin account.

---

#### Runbook 3: Security Scanner Hang (All Requests Blocked)
**Symptom**: All tool execution requests return `BLOCKED` with `reason_code: SECURITY_ENGINE_FAILURE`. No real threat detected — the fail-closed policy triggered because a scanner crashed.

**What This Means**: One of the security scanners (`JailbreakDetector`, `OutputInspector`, or `ToolAuthorizer`) raised an unhandled exception. `ExecutionController` caught it and defaulted to fail-closed (`BLOCK`) to keep the system safe.

**Diagnosis & Mitigation**:
1. Check server logs for stack traces:
   ```bash
   journalctl -u vantage -n 200 | grep ERROR
   ```
2. Identify which scanner is failing from the trace.
3. If the issue is transient (memory spike, timeout), restart the server:
   ```bash
   docker restart vantage-server
   # OR in Kubernetes:
   kubectl rollout restart deployment/vantage
   ```
4. If it is a code bug, roll back to the previous Docker image version.

---

#### Runbook 4: DuckDB File Corruption
**Symptom**: `/ready` returns HTTP 503. Logs show `duckdb.Error: database file appears to be malformed`.

**What This Means**: The `vantage.duckdb` file on disk was corrupted, likely due to an abrupt shutdown during a write operation.

**Diagnosis & Mitigation**:
1. Stop the Vantage server immediately to prevent further writes.
2. Check if a WAL file exists alongside `vantage.duckdb` — DuckDB may auto-recover.
3. Restore from the most recent volume backup:
   ```bash
   cp /backups/vantage.duckdb.backup /app/data/vantage.duckdb
   ```
4. Note: DuckDB holds only telemetry spans. Security metadata (API keys, policies, audit logs) is in SQLite and is **unaffected** by DuckDB corruption.
5. Re-ingest any spans lost since the last backup from the DLQ file.

---

#### Runbook 5: All API Keys Accidentally Revoked
**Symptom**: All API requests return HTTP 401 `INVALID_API_KEY`. No keys appear active. The system appears locked out.

**Recovery Steps**:
1. Connect directly to the SQLite database file:
   ```bash
   sqlite3 /app/data/vantage.db
   ```
2. Check the `api_keys` table:
   ```sql
   SELECT key_id, display_name, status FROM api_keys;
   ```
3. Restore the emergency admin key:
   ```sql
   UPDATE api_keys
   SET status = 'active', revoked_at = NULL
   WHERE key_id = 'vg_key_admin_recovery';
   ```
4. After recovery, generate a new admin key via the API and revoke the emergency key.

