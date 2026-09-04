# Vantage Developer Onboarding, Codebase Architecture, & Testing Guide

## 1. Complete Directory Tree Layout

```text
D:\vantage\
├── .github/                       # CI/CD workflows (GitHub Actions)
│   └── workflows/ci.yml           # Automated linting, type checks & pytest pipeline
├── docs/                          # Master System Documentation Suite (01 to 09)
├── frontend/                      # React 18 + Vite + TypeScript Single Page Application
│   ├── public/                    # Static favicon and branding assets
│   ├── src/
│   │   ├── components/            # Reusable UI components (DAGVisualizer, NavigationBar)
│   │   ├── pages/                 # SPA Views (EnterpriseSettingsPage, ProjectsPage, Dashboard)
│   │   ├── services/              # Axios API client bindings
│   │   ├── App.tsx                # React Router & Application Layout
│   │   └── main.tsx               # React entry point
│   ├── package.json               # Frontend dependencies (React, Vite, Axios, Chart.js)
│   ├── tsconfig.json              # TypeScript compiler configuration
│   └── vite.config.ts             # Vite build & local proxy settings
├── tests/                         # Pytest Automated Test Suite
│   ├── e2e/                       # End-to-end flow tests (ingestion, security pipeline)
│   ├── fixtures/                  # Shared test mocks & OTLP JSON data
│   ├── integration/               # Database repository & query tests
│   ├── security/                  # Mandatory Adversarial Security Attack Simulations
│   │   └── test_attack_simulations.py # 5 Core v1.2 Architectural Security Tests
│   ├── unit/                      # Isolated unit tests for detectors, cache, RBAC
│   ├── test_ingest_buffer.py      # Queue buffer & DLQ overflow tests
│   ├── test_otlp.py               # OTLP ingestion & normalizer tests
│   ├── test_pii_masker.py         # Luhn & pattern PII masking tests
│   └── test_webhooks.py           # Webhook SSRF firewall & HMAC signing tests
├── vantage/                       # Core Vantage Python Package
│   ├── anomaly/                   # Statistical Anomaly Detection Engines
│   │   ├── base.py                # Abstract Base Detector class
│   │   ├── z_score.py             # Z-score statistical detector
│   │   ├── threshold.py           # Hard cap threshold detector
│   │   ├── rate_of_change.py      # Multiplicative rate of change detector
│   │   ├── error_rate.py          # Error percentage detector
│   │   └── volume_spike.py        # Spiking traffic volume detector
│   ├── api/                       # FastAPI REST API Layer
│   │   ├── app.py                 # FastAPI application factory & lifespan handler
│   │   ├── dependencies.py        # Authentication & service dependency injection
│   │   └── v1/                    # API v1 Router Modules
│   │       ├── alerts.py          # Alert rules & incident endpoints
│   │       ├── analytics.py       # Analytical rollup endpoints
│   │       ├── api_keys.py        # API key management endpoints
│   │       ├── audit.py           # Hash-chained audit log endpoints
│   │       ├── cache.py           # Query cache hit endpoints
│   │       ├── dpo.py             # Direct Preference Optimization dataset exporter
│   │       ├── health.py          # /health & /ready probes
│   │       ├── ingest.py          # Generic span ingestion endpoint
│   │       ├── otlp.py            # Native OpenTelemetry OTLP/REST endpoint
│   │       ├── policy.py          # Project circuit breaker policy endpoints
│   │       ├── projects.py        # Project management endpoints
│   │       ├── query.py           # Trace query & aggregation endpoints
│   │       ├── replay.py          # Deterministic replay & What-If endpoints
│   │       ├── router.py          # Central API v1 router aggregator
│   │       ├── vector.py          # RAG vector trace endpoints
│   │       └── webhooks.py        # Webhook endpoint management
│   ├── auth/                      # Authentication & Access Control
│   │   ├── rate_limiter.py        # Multi-Dimensional Rate & Concurrency Limiter
│   │   └── rbac.py                # Role-Based Access Control matrix (Admin/Dev/Viewer)
│   ├── core/                      # Core System Utilities & Configurations
│   │   ├── circuit_breaker.py     # Trace Action Budget Circuit Breaker
│   │   ├── config.py              # Pydantic BaseSettings environment manager
│   │   ├── exceptions.py          # Custom domain exceptions
│   │   └── logging.py             # Structured JSON logger configuration
│   ├── domain/                    # Pure Domain Entities & Interfaces
│   │   ├── alerts.py              # Alert domain classes
│   │   ├── experiments.py         # Experiment domain classes
│   │   ├── models.py              # CanonicalVantageSpan data model
│   │   └── projects.py            # Project domain classes
│   ├── ingest/                    # Telemetry Ingestion Pipeline
│   │   ├── buffer.py              # Bounded memory queue & Dead-Letter Queue (DLQ)
│   │   └── normalizer.py          # OTLP GenAI attribute normalizer
│   ├── replay/                    # Deterministic Replay Subsystem
│   │   └── engine.py              # ReplayEngine state reconstruction & tool mock layer
│   ├── security/                  # Active Security Enforcement Architecture (v1.2)
│   │   ├── __init__.py            # Exported security module bindings
│   │   ├── approval_workflow.py   # Single-Use TOCTOU Human Approval Workflow
│   │   ├── context.py             # Immutable SecurityContext dataclass
│   │   ├── decoder.py             # Base64 / Hex payload decoder
│   │   ├── execution_controller.py# Sole Tool Execution Choke Point
│   │   ├── jailbreak_detector.py # Prompt injection & jailbreak detector
│   │   ├── models.py              # Security threat types & scan result models
│   │   ├── normalizer.py          # Text normalizer for obfuscation handling
│   │   ├── output_inspector.py    # Data Classification & Destination Trust Guard
│   │   ├── pii_masker.py          # In-Flight PII Redactor (Luhn + Patterns)
│   │   ├── policy_gate.py         # Multi-Signal Policy Engine (BLOCK > APPROVAL > WARN)
│   │   ├── rules.py               # Pattern scanning security rules
│   │   ├── scanner.py             # Abstract security scanner base class
│   │   └── tool_authorizer.py     # Deny-by-Default Capability Matrix
│   ├── services/                  # Business Logic Application Services
│   │   ├── ingestion_service.py   # Telemetry processing coordinator
│   │   ├── query_service.py       # DuckDB analytical query service
│   │   ├── replay_service.py      # Replay manifest generator service
│   │   └── webhook_notifier.py    # SSRF-firewalled HMAC webhook dispatcher
│   └── storage/                   # Storage Layer Implementations
│       ├── duckdb/                # DuckDB OLAP backend implementation
│       └── sqlalchemy/            # SQLite / SQLAlchemy 2.0 ORM models & repository
├── Dockerfile                     # Multi-stage production container build
├── docker-compose.yml             # Docker stack definition (Vantage + Grafana)
├── pyproject.toml                 # Python project configuration & dependencies
└── README.md                      # Repository landing page & quickstart
```

---

## 2. File-by-File Purpose Reference Table

| File Path | Primary Function & Responsibilities | Key Exported Symbols |
| :--- | :--- | :--- |
| `vantage/security/context.py` | Defines immutable security context passed across security components. | `SecurityContext` |
| `vantage/security/policy_gate.py` | Multi-signal policy engine evaluating precedence (`BLOCK > APPROVAL > WARN > ALLOW`). | `MultiSignalPolicyGate`, `SecurityPolicyDecision` |
| `vantage/security/tool_authorizer.py` | Deny-by-default capability scoping by `Action+Resource+Env`. | `ToolAuthorizer` |
| `vantage/security/approval_workflow.py` | TOCTOU action fingerprinting and atomic single-use approvals. | `HumanApprovalWorkflow`, `ApprovalRecord` |
| `vantage/security/output_inspector.py` | Data sensitivity classification and destination trust validation. | `OutputInspector`, `DataClassification`, `DestinationTrust` |
| `vantage/security/execution_controller.py` | Sole choke-point enforcing policy before tool execution occurs. | `ExecutionController`, `ExecutionResult` |
| `vantage/security/pii_masker.py` | In-flight PII & secret redactor using Luhn checksums and regex. | `PIIMasker` |
| `vantage/security/jailbreak_detector.py` | Scans prompts for injection attempts, DAN bypasses, and overrides. | `JailbreakDetector` |
| `vantage/ingest/buffer.py` | In-memory ring buffer (`max_capacity=10000`) and Dead-Letter Queue. | `BoundedIngestBuffer` |
| `vantage/services/webhook_notifier.py` | Webhook dispatch with SSRF firewalling and HMAC signatures. | `WebhookNotifier` |
| `vantage/auth/rate_limiter.py` | Multi-dimensional rate and concurrency limiter. | `MultiDimensionalRateLimiter` |
| `vantage/core/circuit_breaker.py` | Trace action budget circuit breaker manager. | `TraceActionCircuitBreaker` |
| `vantage/storage/duckdb/` | Vectorized OLAP backend executing SQL analytical queries. | `DuckDBTelemetryRepository` |
| `vantage/storage/sqlalchemy/metadata_repository.py` | Async SQLite transactional metadata storage repository. | `SQLiteMetadataRepository` |

---

## 3. Step-by-Step Local Setup Guide

### Environment Prerequisites
- Python 3.12+ (or 3.13)
- Node.js 18+ & npm
- Git

### Terminal Execution Steps

```bash
# 1. Clone Repository & Navigate to Directory
git clone https://github.com/YATHARTHH/vantage.git
cd vantage

# 2. Set Up Python Virtual Environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 3. Install Backend Dependencies
pip install --upgrade pip
pip install -e .[dev]

# 4. Initialize Database & Seed Demo Traces
python setup_project_and_seed.py

# 5. Start Backend Server (Uvicorn)
python -m uvicorn vantage.api.app:app --host 0.0.0.0 --port 8000 --reload

# 6. Set Up and Build Frontend Application (In separate terminal)
cd frontend
npm install
cmd.exe /c "npm run build"  # Or npm run dev for local HMR
```

Once running, navigate to `http://localhost:8000` to access the unified Vantage portal.

---

## 4. Automated Testing Suite & Extension Recipes

### Running Pytest Test Suite
Vantage includes 69 automated tests spanning unit, integration, end-to-end, and adversarial security attack simulations:

```bash
# Run complete Pytest test suite via Virtual Environment
cmd.exe /c ".venv\Scripts\python.exe -m pytest -v"

# Run specific test modules (e.g. Security Attack Simulations)
cmd.exe /c ".venv\Scripts\python.exe -m pytest tests/security/test_attack_simulations.py -v"
```

### Recipe 1: Adding a Custom Anomaly Detector
To add a new statistical detector (e.g. detecting sudden prompt token inflation):
1. Subclass `AbstractDetector` in `vantage/anomaly/base.py`.
2. Implement the `detect(spans: List[CanonicalVantageSpan]) -> List[AlertRecord]` method.
3. Register the detector string key in `vantage/domain/alerts.py`.
4. Add unit test verification in `tests/unit/test_anomaly_detectors.py`.

### Recipe 2: Adding a Custom Security Policy Rule
To add a custom policy rule (e.g. blocking database drops in any environment):
1. Open `vantage/security/policy_gate.py`.
2. Add rule check inside `MultiSignalPolicyGate.evaluate()`:
   ```python
   if ctx.action == "database.drop":
       matched_rules.append("HARD_BLOCK_DATABASE_DROP")
       return SecurityPolicyDecision(
           decision="BLOCK",
           reason_code="DATABASE_DROP_PROHIBITED",
           reason="Database drop operations are strictly prohibited across all environments",
           matched_rules=matched_rules,
           ...
       )
   ```
3. Add a test case in `tests/security/test_attack_simulations.py`.
