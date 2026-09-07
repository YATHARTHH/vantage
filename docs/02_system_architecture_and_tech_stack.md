# Vantage System Architecture, Tech Stack Justifications, & Architecture Decision Records (ADRs)

Welcome to **Document 02**! This document provides the complete, production-grade architectural specification of Vantage. It combines high-resolution technical diagrams, exhaustive technology stack trade-off analyses, and formal **Architecture Decision Records (ADRs)**—accompanied by plain-language explanations.

---

## ❓ What is an ADR (Architecture Decision Record)?

> 💡 **Simple Analogy**: Imagine a team of structural engineers building a skyscraper. They must decide: *"Should we use a glass facade or a reinforced steel facade?"* They choose steel because of high-altitude wind resistance. To ensure future maintenance crews don't swap it for glass without understanding why, they write down an official note: **"We selected steel to withstand 120 mph winds."**

In software architecture, an **Architecture Decision Record (ADR)** is that exact note! It is a formal document capturing:
1. **Context**: What problem or constraint were we facing?
2. **Decision**: What technology, pattern, or framework did we choose?
3. **Consequences**: What benefits did we gain, and what trade-offs did we accept?

We maintain ADRs so that any engineer, auditor, or hiring manager reviewing Vantage can understand **WHY** every technical decision was made.

---

## 1. High-Resolution System Architecture Diagram

Below is the complete 6-tier architectural flowchart of Vantage.

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

### 🏭 Plain-Language Summary of Each Tier
* **Tier 1 (Sources)**: AI agents running anywhere (LangChain, LlamaIndex, Python) stream trace data into Vantage using the OpenTelemetry standard format.
* **Tier 2 (Ingestion Pipeline)**: FastAPI authenticates API keys, decompresses payloads, redacts PII/secrets *in flight*, and buffers up to 10,000 spans in memory before writing to disk.
* **Tier 3 (Dual Storage)**: High-speed trace analytics flow into **DuckDB** (columnar OLAP — fast at reading millions of rows), while security state (API keys, policies, audit logs) is saved in **SQLite** (transactional OLTP — strict and accurate for small critical writes).
* **Tier 4 (Active Enforcement)**: `ExecutionController` intercepts AI tool calls *before* they execute, checking permissions, scanning for jailbreaks, and requiring human approval when necessary.
* **Tier 5 (Intelligence & Replay)**: Statistical engines scan for cost spikes and latency anomalies, while `ReplayEngine` reconstructs past executions offline for safe debugging.
* **Tier 6 (Frontend Portal)**: A React 18 SPA renders real-time execution DAGs, approval queues, and metric charts so engineers have a visual window into what every agent is doing.

### 🔗 How the Tiers Connect — The Data Journey

The tiers are ordered deliberately. Here is why data flows in this specific sequence and what would break if you changed it:

```text
Tier 1 (Sources)
  │  AI agents and frameworks emit telemetry spans.
  │  These travel over HTTP to the Vantage ingestion endpoint.
  ▼
Tier 2 (Ingestion Pipeline)
  │  MUST come before storage — this is where PII is scrubbed IN MEMORY.
  │  If we stored first and scrubbed later, raw credit cards would touch disk
  │  even briefly — a GDPR/HIPAA violation.
  │  After scrubbing, spans enter the in-memory buffer (not disk yet).
  ▼
Tier 3 (Dual Storage)
  │  Clean, scrubbed spans are flushed asynchronously to DuckDB.
  │  Security metadata (API keys, approvals) writes to SQLite — separate
  │  database so heavy analytics never block security operations.
  ▼
Tier 4 (Active Enforcement)
  │  Reads security policies FROM SQLite (Tier 3) to make decisions.
  │  This happens in real-time on every tool call — NOT on telemetry spans.
  │  Telemetry (Tier 2-3) and Security Enforcement (Tier 4) are parallel paths.
  ▼
Tier 5 (Intelligence & Replay)
  │  Reads historical spans FROM DuckDB (Tier 3) to detect anomalies.
  │  Anomaly alerts are written back to SQLite (Tier 3) as alert_records.
  │  Replay Engine reads past traces from DuckDB to reconstruct execution.
  ▼
Tier 6 (Frontend)
  │  Reads from BOTH databases (Tier 3) via the REST API.
  │  Shows the developer everything: spans, costs, security events, approvals.
  │  The frontend never writes directly to databases — all writes go through
  │  the backend API which enforces authentication and authorization.
```

> 💡 **The Key Insight**: Tiers 2 and 4 are not sequential — they run in parallel. Tier 2 handles telemetry (passive observation), Tier 4 handles tool enforcement (active blocking). Both feed into Tier 3 as their shared storage layer.

---

## 2. Tech Stack Justifications & Rejected Alternatives

Vantage was architected with explicit performance, security, and developer velocity trade-offs. Below is the engineering justification for every technology selected versus alternatives rejected. For each choice, we first explain **what the tool is**, then **why we chose it**, then **what we rejected and why**.

### A. Core Runtime: Python 3.12+
* **What is it?** Python is the programming language the entire Vantage backend is written in. Version 3.12 is the latest stable release as of 2024.
* **Why Selected**: Python 3.12 provides improved `asyncio` *(async = ability to handle many requests at the same time without waiting)* performance, GIL improvements *(GIL = Global Interpreter Lock, a Python mechanism that previously limited true parallel execution — 3.12 reduces this bottleneck)*, and native interoperability with all major AI frameworks (LangChain, LlamaIndex, OpenAI, Anthropic, HuggingFace). Every AI SDK has a first-class Python library.
* **Alternatives Rejected**:
  - *Node.js / TypeScript*: Lacks native deep-learning ecosystem integration and scientific computing packages (NumPy, SciPy) required for Z-score anomaly detection algorithms.
  - *Go / Rust*: Excellent raw execution speed, but lacks rapid AI model connector bindings and standard schema definitions present in Python's AI ecosystem.

### B. API Framework: FastAPI
* **What is it?** FastAPI is a modern Python web framework for building REST APIs. It handles incoming HTTP requests and routes them to the right backend function.
* **Why Selected**: Built on Starlette and Pydantic v2 *(Pydantic = a Python library that automatically validates incoming data — if a field is supposed to be an integer but a string arrives, Pydantic rejects it before it reaches your code)*. Provides high-throughput async I/O handling, automatic OpenAPI/Swagger documentation generation, and low overhead (< 2ms router overhead per request).
* **Alternatives Rejected**:
  - *Flask / Django*: Synchronous execution models *(synchronous = handles one request at a time, blocking others while it waits)* lock worker threads during async DuckDB queries and HTTP webhook dispatches, causing severe ingestion bottlenecks under heavy telemetry load.
  - *NestJS*: Adds unnecessary TypeScript transpilation complexity to a backend heavily integrated with Python data science tools.

### C. Analytical Storage Engine: DuckDB
* **What is it?** DuckDB is a database that runs inside your application process (no separate server needed) and stores data in a column-by-column format instead of row-by-row — making it extremely fast at analytics.
* **Why Selected**: Columnar storage *(columnar = data stored by column, not by row — so a query like `AVG(latency)` only reads the latency column, skipping all other data)* achieves sub-second analytical aggregations across tens of millions of spans. Zero external server infrastructure — the database is a single `.duckdb` file. Supports native Parquet file persistence and vectorized SQL *(vectorized = processes many values at once using CPU SIMD instructions, like doing 8 calculations in parallel instead of 1)*.
* **Alternatives Rejected**:
  - *ClickHouse / Snowflake*: Incredible scale, but requires complex multi-node infrastructure, zookeeper/ch-keeper setup, and high maintenance costs. Unsuited for lightweight local deployment.
  - *PostgreSQL (Standard B-Tree)*: Row-oriented layout *(row-oriented = must read the entire row to get one column's value)* degrades rapidly when performing analytical aggregations (`AVG(latency)`, `SUM(tokens)`) across millions of span rows.

### D. Transactional Storage Engine: SQLite + SQLAlchemy 2.0 (Async)
* **What is it?** SQLite is a lightweight relational database stored as a single file. SQLAlchemy is a Python library that lets you write Python code instead of raw SQL to interact with the database. Alembic is a tool that manages database schema changes over time (like version control for your database).
* **Why Selected**: Zero-configuration, ACID-compliant *(ACID = Atomicity, Consistency, Isolation, Durability — guarantees that database writes are 100% complete or 100% rolled back, never half-done)* transactional engine for application state (projects, API keys, alert rules, human approval tokens, hash-chained audit logs). Paired with SQLAlchemy 2.0 async sessions and Alembic migrations *(migrations = scripts that evolve the database schema as the application grows — adding columns, creating tables — without losing existing data)*.
* **Alternatives Rejected**:
  - *PostgreSQL-only for everything*: Mixing high-frequency streaming telemetry writes with ACID-strict transactional updates leads to severe table lock contention and WAL bloat *(WAL = Write-Ahead Log, PostgreSQL's internal change journal — excessive concurrent writes cause it to grow uncontrollably, degrading performance)*.
  - *MongoDB / Document DB*: Lack of strict ACID guarantees across multi-row API key revocations and hash-chained audit trails violates security compliance requirements.

### E. Frontend Application: React 18 + Vite + TypeScript
* **What is it?** React is a JavaScript library for building user interfaces. Vite is the tool that compiles the React code into production-ready HTML/CSS/JS files. TypeScript is a version of JavaScript that adds type safety (catching bugs before the code runs).
* **Why Selected**: Vite provides instant HMR *(Hot Module Replacement = when you save a file during development, only that changed component reloads in the browser — no full page refresh, saves developers minutes per hour)* and optimized production bundles. React 18's concurrent rendering allows smooth updates of real-time trace graphs, interactive DAG visualizations, and fast tab navigation. TypeScript ensures zero type-mismatch bugs across frontend API integrations.
* **Alternatives Rejected**:
  - *Next.js (Server-Side Rendering)*: Adds unnecessary SSR *(Server-Side Rendering = the server renders each HTML page on demand before sending to the browser — great for public-facing marketing sites, overkill for internal admin dashboards)* infrastructure complexity. Client-side SPA static files hosted directly by FastAPI is simpler and faster for an internal portal.
  - *Vue / Angular*: React has the largest enterprise ecosystem for interactive visualization libraries and SVG graph renderers.

### F. Telemetry Standard: OpenTelemetry (OTLP) + OpenInference
* **What is it?** OpenTelemetry is an open industry standard (maintained by the Cloud Native Computing Foundation — the same organization behind Kubernetes) for collecting telemetry data (traces, metrics, logs) from any software system.
* **Why Selected**: Vendor-neutral — eliminates lock-in, enabling enterprise agents built with any language or framework to send spans directly to Vantage without custom plugins. Backed by Google, Microsoft, and Amazon. OpenInference extends OpenTelemetry with AI-specific semantic conventions (`gen_ai.usage.input_tokens`, `gen_ai.input.messages`).
* **Alternatives Rejected**:
  - *Proprietary Custom SDK-only*: Forces developers to re-instrument existing applications entirely and locks telemetry into Vantage's ecosystem — killing adoption.

---

## 3. Architecture Decision Records (ADRs)

Below are all 10 formal architectural decisions made during Vantage's design. Each ADR explains the problem context, the decision made, and the consequence (trade-offs accepted). A "Plain-Language Summary" follows each one so the decision is understandable to any reader.

### Quick-Glance: All 10 ADRs at a Glance

| ADR | Decision Made | The Core Reason |
|:----|:-------------|:----------------|
| **ADR-001** | Use two separate databases (DuckDB + SQLite) | Analytics and security ops must never compete for the same DB resources |
| **ADR-002** | In-memory ring buffer + Dead-Letter Queue overflow | Survive traffic bursts without dropping data and without needing Redis |
| **ADR-003** | All tool calls must pass through `ExecutionController` | A single choke-point means security can never be accidentally bypassed |
| **ADR-004** | SHA-256 action fingerprint for TOCTOU prevention | Lock approved arguments so they cannot be swapped right before execution |
| **ADR-005** | Fail-Closed for security, Fail-Safe for telemetry | Scanner crash → BLOCK. Buffer crash → degrade safely. Never "fail open." |
| **ADR-006** | PII scrubbing happens in memory before any storage | Raw credit cards must never touch disk — compliance by architecture |
| **ADR-007** | SHA-256 hash-chained audit logs | Any tampered audit record immediately breaks the chain — forensic-grade |
| **ADR-008** | Dispatch-time DNS resolution for webhooks | Prevents SSRF attacks where DNS tricks the server into hitting internal IPs |
| **ADR-009** | Multi-signal policy engine with hard precedence | A single threat score can be bypassed; BLOCK must always beat everything else |
| **ADR-010** | Normalize all telemetry to `CanonicalVantageSpan` | Different AI frameworks use different field names — one model rules them all |

---

### ADR-001: Dual-Database Separation (DuckDB OLAP + SQLite OLTP)
- **Context**: Vantage must ingest thousands of telemetry spans per second while simultaneously handling strict ACID transactional operations for API keys, security policies, and audit logs.
- **Decision**: Separate data storage into two specialized engines: DuckDB for immutable, high-volume columnar span telemetry; SQLite/SQLAlchemy for relational transactional entities.
- **Consequences**: Eliminates database lock contention. Allows analytical queries to scan millions of spans in milliseconds without impacting API key validation or security policy checks.
- **Plain-Language Summary**: We split analytical queries (DuckDB) from security policy rules (SQLite) so huge analytics reports never slow down security checks.

### ADR-002: In-Memory Bounded Queue with Dead-Letter Queue (DLQ)
- **Context**: Ingestion spikes can overwhelm storage backends, causing dropped HTTP connections.
- **Decision**: Implement an in-memory ring buffer (`max_capacity=10000`) with an async background worker flushing every 500ms. Overflows write atomically to `.dlq_spans.jsonl`.
- **Consequences**: Guarantees zero dropped telemetry spans during traffic bursts without requiring a Redis broker for single-instance deployments.
- **Plain-Language Summary**: If traffic spikes suddenly, spans are buffered safely in memory. If memory fills up, extra spans spill over to a disk file (`.dlq_spans.jsonl`) so no data is ever lost.

### ADR-003: Mandatory ExecutionController Choke Point
- **Context**: Untrusted LLM code could potentially bypass security checks if tool invocation is scattered across various agent modules.
- **Decision**: Route ALL tool executions through a single, unified method: `ExecutionController.execute(...)`.
- **Consequences**: Provides complete mediation. Ensures capability authorization, data sensitivity checks, TOCTOU fingerprint validation, and human approvals are enforced without exception.
- **Plain-Language Summary**: Every single AI tool call must pass through ONE single security gate. No tool can execute without passing all checks first.

### ADR-004: Single-Use TOCTOU Action Fingerprinting
- **Context**: An attacker could modify tool arguments or target environments after human approval was granted.
- **Decision**: Hash the complete action context (`tool`, `action`, `resource`, `environment`, `arguments`) into a SHA-256 fingerprint, and enforce atomic single-use approval consumption (`consumed_at`).
- **Consequences**: Completely eliminates Time-Of-Check-To-Time-Of-Use (TOCTOU) tampering and approval replay attacks.
- **Plain-Language Summary**: When a manager approves a request, we lock the exact arguments with a digital SHA-256 stamp. If the AI changes the parameters right before execution, it is blocked.

### ADR-005: Fail-Closed Security Enforcement vs. Fail-Safe Telemetry Ingestion
- **Context**: A failure in a security scanner or policy gate could either halt the application or allow unauthorized execution.
- **Decision**: Enforce Fail-Closed (`BLOCK`) for agent tool execution when security scanners fail; enforce Fail-Safe (safe buffer degradation) for telemetry ingestion.
- **Consequences**: Prevents security breaches during component outages while ensuring observability collection does not bring down the host platform.
- **Plain-Language Summary**: If a security scanner crashes, Vantage defaults to **BLOCKING** the action to keep your system safe.

### ADR-006: In-Flight PII Redaction Before Persistence
- **Context**: Storing raw PII (credit cards, SSNs, secrets) in telemetry storage violates HIPAA, GDPR, and PCI-DSS compliance.
- **Decision**: Execute `PIIMasker` directly in the ingestion pipeline before buffering or writing spans to DuckDB.
- **Consequences**: Telemetry storage never retains raw sensitive secrets. Non-sensitive tags (`pii_scrubbed=true`, `pii_types=[...]`) are retained for auditing.
- **Plain-Language Summary**: Credit cards and secrets are scrubbed in memory *before* saved to disk so sensitive user data is never stored.

### ADR-007: Cryptographic Hash-Chained Audit Trail
- **Context**: Audit logs stored in standard database tables can be silently altered or deleted by a compromised admin or database user.
- **Decision**: Chain audit log entries using SHA-256 hashes where `hash_i = SHA256(entry_i + hash_{i-1})`.
- **Consequences**: Any modification, insertion, or deletion of past audit entries immediately invalidates the cryptographic chain, providing tamper-evident forensic compliance.
- **Plain-Language Summary**: Audit log rows are cryptographically linked using SHA-256. If anyone tries to alter past logs in the database, the hash chain breaks instantly.

### ADR-008: Dispatch-Time DNS Resolution for Webhooks (SSRF Firewall)
- **Context**: Webhooks pointing to external URLs can be exploited via Server-Side Request Forgery (SSRF) or DNS rebinding to access internal private networks (`127.0.0.1`, `169.254.169.254`).
- **Decision**: Re-resolve target hostnames to IP addresses immediately before socket connection in `webhook_notifier.py`, rejecting loopback, RFC1918, or cloud metadata IPs. Disable HTTP redirects (`follow_redirects=False`).
- **Consequences**: Completely blocks SSRF and DNS rebinding attacks on outbound webhooks.
- **Plain-Language Summary**: Webhooks check destination IP addresses right before sending data to prevent hackers from targeting internal private networks.

### ADR-009: Multi-Signal Deterministic Precedence Policy Engine
- **Context**: Heuristic threat scores alone are easily obfuscated by adversarial prompt injection.
- **Decision**: Implement a policy engine combining threat scores, tool risk, data classification, and capability scope into a strict precedence hierarchy: `BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`.
- **Consequences**: Negative security signals hard-deny execution regardless of positive heuristics, creating a robust defense-in-depth model.
- **Plain-Language Summary**: Security decisions follow a strict hierarchy: `BLOCK` beats `APPROVAL`, `APPROVAL` beats `WARN`, `WARN` beats `ALLOW`.

### ADR-010: Native OpenInference & OTLP Protocol Mapping
- **Context**: Enterprise applications use diverse framework abstractions (LangChain, LlamaIndex, custom OpenAI API wrappers).
- **Decision**: Map all ingress telemetry into a unified standard model (`CanonicalVantageSpan`) adhering to OpenTelemetry GenAI semantic conventions (`gen_ai.usage.input_tokens`, `gen_ai.input.messages`).
- **Consequences**: Vantage maintains total independence from agent framework implementation details.
- **Plain-Language Summary**: Vantage uses open standard telemetry formats so it works with any agent framework without requiring custom plugins.


