<div align="center">

# ⚡ Vantage — AI Agent Observability & Active Security Enforcement Platform

[![CI Pipeline](https://img.shields.io/badge/CI%20Pipeline-Passing-brightgreen?style=for-the-badge&logo=github-actions)](https://github.com/YATHARTHH/vantage/actions)
[![Pytest Suite](https://img.shields.io/badge/Pytest-69%2F69%20Passed-success?style=for-the-badge&logo=pytest)](https://pytest.org/)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-FFF000?style=for-the-badge&logo=duckdb)](https://duckdb.org)
[![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)](LICENSE)

> **Universal OpenTelemetry (OTLP) AI Telemetry, In-Flight PII Redaction, Multi-Signal Policy Precedence, Single-Use TOCTOU Human Approvals, Mandatory Execution Choke-Points, and Deterministic Offline Replays.**

<br />

![Vantage Hero Banner](assets/vantage_hero_banner.png)

</div>

---

> [!IMPORTANT]
> Vantage transitions AI monitoring from passive observation ("detect and report") to **active runtime enforcement ("authorize and enforce")**.
> Core Imperative: *"Detection provides evidence. Policy makes the decision. Authorization determines capability. Enforcement controls the side effect. Audit records why."*

---

## 🌟 Key Capabilities at a Glance

| Feature Module | Capabilities & Description | Key Architecture Components |
| :--- | :--- | :--- |
| 🛡️ **Active Security Enforcement (v1.2)** | Mandatory execution choke-point (`ExecutionController.execute(...)`) intercepting tool calls prior to execution. Evaluates capability matrix (`Action+Resource+Env`), data sensitivity, and destination trust. | `ExecutionController`, `MultiSignalPolicyGate`, `ToolAuthorizer` |
| 🔒 **TOCTOU Action Fingerprinting** | Cryptographic SHA-256 canonical JSON action hash (`tool`, `action`, `resource`, `environment`, `arguments`). Single-use atomic approval consumption (`consumed_at`) with stale-policy checks. | `HumanApprovalWorkflow`, `ApprovalRecord` |
| 🕵️ **In-Flight PII & Secret Redaction** | In-flight scrubbing of credit cards (validated via Luhn algorithm checksum), SSNs, API keys (`sk-...`, `vg_live_...`), and emails prior to queue buffering and DuckDB persistence. | `PIIMasker`, `JailbreakDetector` |
| ⚡ **Dual-Database Subsystem** | DuckDB vectorized columnar OLAP engine for sub-second analytical queries across millions of spans paired with SQLite/SQLAlchemy 2.0 for transactional state and hash-chained audit logs. | `DuckDBTelemetryRepository`, `SQLiteMetadataRepository` |
| 🔄 **Deterministic Replay Engine** | Reconstructs complete execution state from recorded span trees into a `ReplayManifest`, mocking downstream tools to allow offline debugging and "What-If" prompt tuning without side-effects. | `ReplayEngine`, `ReplayService` |
| 🚨 **5 Anomaly Detectors & Circuit Breakers** | Statistical detectors (**Z-Score, Threshold, Rate-Change, Error Rate %, Volume Spikes**) + Trace Action Budget Circuit Breakers (`max_tool_calls_per_trace`). | `TraceActionCircuitBreaker`, `AbstractDetector` |
| 📊 **React SPA & Interactive SVG DAG** | Glassmorphic React 18 single-page app featuring interactive span DAG visualizer, approval queue workflow, and role capability matrix. | Integrated React + Vite + TS SPA |

---

## 🏗️ End-to-End System Architecture

```mermaid
flowchart TD
    subgraph SOURCES["1. Telemetry & Agent Sources"]
        A1["OpenTelemetry OTLP Exporters"]
        A2["LangChain / LlamaIndex Agents"]
        A3["Custom Python / TypeScript SDKs"]
        A4["REST API Ingestion Clients"]
    end

    subgraph INGESTION["2. Ingestion & Security Pipeline"]
        B1["FastAPI Ingestion Router (/api/v1/otlp/v1/traces)"]
        B2["Header & API Key Authenticator (Bearer / X-API-Key)"]
        B3["Gzip Decompressor & 10MB Payload Cap"]
        B4["In-Flight PII / Secret Masker (Luhn + Pattern Scanner)"]
        B5["Bounded Ingestion Buffer (Cap: 10,000 Spans)"]
        B6["Atomic Dead-Letter Queue (.dlq_spans.jsonl)"]
    end

    subgraph DUAL_DB["3. Dual-Database Storage Subsystem"]
        subgraph OLTP["SQLite / SQLAlchemy 2.0 (Transactional DB)"]
            C1["Projects & API Keys"]
            C2["Alert Rules & Records"]
            C3["Human Approvals & Policies"]
            C4["Cryptographic Hash-Chained Audit Logs"]
        end
        subgraph OLAP["DuckDB (Analytical Storage Engine)"]
            D1["telemetry_spans (Parquet / Columnar)"]
            D2["metrics_hourly (Aggregated OLAP)"]
            D3["unmapped_sources (Diagnostic Data)"]
        end
    end

    subgraph ENFORCEMENT["4. Active Security Enforcement Layer"]
        E1["SecurityContext Dataclass (Immutable)"]
        E2["Trust Provenance Analyzer"]
        E3["Output Inspector & Sanitizer"]
        E4["Deny-by-Default Tool Authorizer (Action+Resource+Env)"]
        E5["Data Sensitivity & Destination Trust Guard"]
        E6["Multi-Signal Policy Engine (BLOCK > APPROVAL > WARN > ALLOW)"]
        E7["Human Approval Workflow (Single-Use + TOCTOU Hash)"]
        E8["ExecutionController (Sole Tool Choke-Point)"]
    end

    subgraph INTELLIGENCE["5. Replay & Intelligence Engines"]
        F1["Deterministic ReplayEngine & Mock Layer"]
        F2["Statistical Anomaly Detectors (Z-Score, Error %, Spike)"]
        F3["Policy Circuit Breaker (Trace Action Budgets)"]
        F4["SSRF Protected Webhook Dispatcher (HMAC Signed)"]
    end

    subgraph FRONTEND["6. User Interface & Analytics Portal"]
        G1["React 18 + Vite Single Page Application"]
        G2["Interactive Trace SVG DAG Visualizer"]
        G3["Active Security & Human Approval Center"]
        G4["Project & API Key Management Dashboard"]
    end

    %% Flow Connections
    SOURCES --> B1
    B1 --> B2 --> B3 --> B4 --> B5
    B5 -- "Async Flush (500ms / 100 items)" --> OLAP
    B5 -- "Overflow" --> B6
    B1 --> OLTP

    E1 --> E2 & E3 & E4 & E5 --> E6
    E6 -- "REQUIRE_APPROVAL" --> E7
    E6 -- "ALLOW / WARN" --> E8
    E7 -- "Verified Single-Use" --> E8
    E8 --> |"Executes Tool"| SOURCES
    E8 --> |"Audit Record"| C4

    DUAL_DB --> INTELLIGENCE
    INTELLIGENCE --> F4
    DUAL_DB --> FRONTEND
    ENFORCEMENT --> FRONTEND
```

---

## 📚 Master Documentation Suite (`docs/`)

The repository includes a comprehensive 9-part Master Documentation Suite written from first principles and grounded in the Vantage codebase:

```text
docs/
├── 01_project_vision_usecases_and_requirements.md  # Vision, Use Cases, Differentiators Matrix & Challenges
├── 02_system_architecture_and_tech_stack.md       # Architecture Flowchart, Tech Stack Justifications & 10 ADRs
├── 03_data_model_telemetry_and_storage.md          # Dual-DB Architecture, Canonical Span & 10 Table Schemas
├── 04_security_threat_model_and_active_enforcement.md # OWASP LLM 2025 Mapping, ExecutionController & Hash Audit
├── 05_replay_dag_circuit_breaker_and_intelligence_engines.md # ReplayEngine, SVG DAG, Circuit Breakers & Detectors
├── 06_developer_onboarding_codebase_and_testing.md # Codebase Tree, File Purpose Table & Setup Guide
├── 07_deployment_cicd_scalability_and_sre.md       # Production Dockerfile, GitHub Actions CI/CD & 1M Req Scaling
├── 08_api_otlp_and_integration_reference.md        # REST API Matrix, OTLP Specs & Working cURL Commands
└── 09_interview_prep_glossary_and_faq.md           # 1-Min Pitch, 5-Min System Script, 20+ Technical Q&As & FAQ
```

---

## 🛠️ Technology Stack

```text
Vantage System Stack
├── Core Runtime     : Python 3.12+ | FastAPI | Uvicorn | Pydantic v2 | SQLAlchemy 2.0
├── Analytical DB    : DuckDB Vectorized Columnar OLAP Engine (Parquet Storage)
├── Transactional DB : SQLite + Async SQLAlchemy (aiosqlite)
├── Active Security  : SecurityContext | PolicyGate | ExecutionController | PIIMasker
├── Frontend UI      : React 18.3 | TypeScript | Vite | React Router v6 | Lucide React
├── Container Stack  : Docker | docker-compose | Grafana 11 OSS Integration
└── Testing Suite    : Pytest (69/69 Tests Passing, 100%) | Pytest-Asyncio | HTTPX
```

---

## 🚀 Quickstart Guide

### 1. Repository Setup & Dependencies

```bash
# Clone the repository
git clone https://github.com/YATHARTHH/vantage.git
cd vantage

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install Python requirements
pip install -e .[dev]
```

### 2. Initialize Database & Seed Demo Traces

```bash
python setup_project_and_seed.py
```

### 3. Launch Vantage Server (Backend + React SPA)

```bash
python -m uvicorn vantage.api.app:app --host 0.0.0.0 --port 8000 --reload
```

> [!TIP]
> Navigate to **[http://localhost:8000/](http://localhost:8000/)** in your browser:
> - 📁 **Projects Overview**: `http://localhost:8000/`
> - 🛡️ **Active Security & Approvals**: `http://localhost:8000/enterprise`
> - 🚨 **Alerts & Incidents**: `http://localhost:8000/alerts`
> - 📊 **Telemetry Explorer**: `http://localhost:8000/telemetry`
> - 📖 **Swagger OpenAPI Docs**: `http://localhost:8000/docs`

---

## 🧪 Verification & Automated Testing

Vantage maintains a 100% test pass rate across unit, integration, end-to-end, and adversarial security simulation tests:

```bash
# Run full Pytest test suite (69 tests)
python -m pytest tests/ -v

# Run Adversarial Security Attack Simulations specifically
python -m pytest tests/security/test_attack_simulations.py -v
```

---

## 📄 License

This project is open-source software licensed under the **[MIT License](LICENSE)**.
