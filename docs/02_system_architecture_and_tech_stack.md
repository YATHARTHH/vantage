# Vantage System Architecture, Tech Stack Justifications, & Architecture Decision Records (ADRs)

## 1. High-Resolution System Architecture Diagram

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

## 2. Tech Stack Justifications & Rejected Alternatives

Vantage was architected with explicit performance, security, and developer velocity trade-offs. Below is the exhaustive engineering justification for every technology selected vs. alternatives rejected.

### A. Core Runtime: Python 3.12+
* **Why Selected**: Python 3.12 provides standard `asyncio` performance enhancements, per-interpreter GIL improvements, and native interoperability with modern AI frameworks (LangChain, LlamaIndex, OpenAI, Anthropic, HuggingFace).
* **Alternatives Rejected**:
  - *Node.js / TypeScript*: Lacks native deep-learning ecosystem integration and complex scientific computing packages (NumPy, SciPy) required for advanced Z-score anomaly detection algorithms.
  - *Go / Rust*: Excellent raw execution speed, but lacks rapid AI model connector bindings and standard schema definitions present in Python's AI ecosystem.

### B. API Framework: FastAPI
* **Why Selected**: Built on Starlette and Pydantic v2. Provides high-throughput async I/O handling, automatic OpenAPI/Swagger documentation generation, strict data validation via Pydantic models, and low overhead (<2ms router overhead).
* **Alternatives Rejected**:
  - *Flask / Django*: Synchronous execution models lock worker threads during async DuckDB queries and HTTP webhook dispatches, causing severe ingestion bottlenecks under heavy telemetry load.
  - *NestJS*: Adds unnecessary TypeScript transpilation complexity to a backend heavily integrated with Python data science tools.

### C. Analytical Storage Engine: DuckDB
* **Why Selected**: In-process vectorized columnar OLAP database engine. Achieves sub-second analytical aggregations across tens of millions of spans without requiring dedicated server infrastructure. Supports native Parquet file persistence, vectorized SQL processing, and ultra-fast memory scans.
* **Alternatives Rejected**:
  - *ClickHouse / Snowflake*: Incredible scale, but requires complex multi-node infrastructure, zookeeper/ch-keeper setup, and high maintenance costs. Unsuited for lightweight local deployment or embedded single-binary distribution.
  - *PostgreSQL (Standard B-Tree)*: Row-oriented layout degrades rapidly when performing OLAP aggregations (`AVG(latency)`, `SUM(tokens)`, `PERCENTILE(duration, 0.95)`) across millions of unstructured JSON span attributes.

### D. Transactional Storage Engine: SQLite + SQLAlchemy 2.0 (Async)
* **Why Selected**: Zero-configuration, ACID-compliant transactional engine for application state (projects, API keys, alert rules, human approval tokens, hash-chained audit logs). Paired with SQLAlchemy 2.0 using clean async sessions and Alembic migrations.
* **Alternatives Rejected**:
  - *PostgreSQL-only for everything*: Mixing high-frequency streaming telemetry writes with ACID-strict transactional schema updates leads to severe table lock contention and WAL bloat in SQLite/Postgres.
  - *MongoDB / Document DB*: Lack of strict ACID transaction guarantees across multi-row API key revocations and hash-chained audit trails violates security compliance requirements.

### E. Frontend Application: React 18 + Vite + TypeScript
* **Why Selected**: Vite provides instant HMR (Hot Module Replacement) and optimized production bundles. React 18's concurrent rendering allows smooth updates of real-time trace graphs, interactive DAG visualizations, and fast tab navigation. TypeScript ensures zero type-mismatch bugs across frontend API integrations.
* **Alternatives Rejected**:
  - *Next.js (Server-Side Rendering)*: Adds unnecessary SSR server infrastructure complexity for an internal enterprise security and analytics portal where client-side rendering with SPA static bundles hosted directly by FastAPI is cleaner and faster.
  - *Vue / Angular*: React possesses the largest enterprise ecosystem for interactive visualization libraries and SVG graph renderers.

### F. Telemetry Standard: OpenTelemetry (OTLP) + OpenInference
* **Why Selected**: Vendor-neutral industry standard for trace and metric collection. Eliminates vendor lock-in, enabling enterprise agents built with any language or framework to send spans directly to Vantage.
* **Alternatives Rejected**:
  - *Proprietary Custom SDK-only*: Forces developers to re-instrument existing applications and locked telemetry into a single vendor ecosystem.

---

## 3. Architecture Decision Records (ADRs)

### ADR-001: Dual-Database Separation (DuckDB OLAP + SQLite OLTP)
- **Context**: Vantage must ingest thousands of telemetry spans per second while simultaneously handling strict ACID transactional operations for API keys, security policies, and audit logs.
- **Decision**: Separate data storage into two specialized engines: DuckDB for immutable, high-volume columnar span telemetry; SQLite/SQLAlchemy for relational transactional entities.
- **Consequences**: Eliminates database lock contention. Allows analytical queries to scan millions of spans in milliseconds without impacting API key validation or security policy checks.

### ADR-002: In-Memory Bounded Queue with Dead-Letter Queue (DLQ)
- **Context**: Ingestion spikes can overwhelm storage backends, causing dropped HTTP connections.
- **Decision**: Implement an in-memory ring buffer (`max_capacity=10000`) with an async background worker flushing every 500ms. Overflows write atomically to `.dlq_spans.jsonl`.
- **Consequences**: Guarantees zero dropped telemetry spans during traffic bursts without requiring a Redis broker for single-instance deployments.

### ADR-003: Mandatory ExecutionController Choke Point
- **Context**: Untrusted LLM code could potentially bypass security checks if tool invocation is scattered across various agent modules.
- **Decision**: Route ALL tool executions through a single, unified method: `ExecutionController.execute(...)`.
- **Consequences**: Provides complete mediation. Ensures capability authorization, data sensitivity checks, TOCTOU fingerprint validation, and human approvals are enforced without exception.

### ADR-004: Single-Use TOCTOU Action Fingerprinting
- **Context**: An attacker could modify tool arguments or target environments after human approval was granted.
- **Decision**: Hash the complete action context (`tool`, `action`, `resource`, `environment`, `arguments`) into a SHA-256 fingerprint, and enforce atomic single-use approval consumption (`consumed_at`).
- **Consequences**: Completely eliminates Time-Of-Check-To-Time-Of-Use (TOCTOU) tampering and approval replay attacks.

### ADR-005: Fail-Closed Security Enforcement vs. Fail-Safe Telemetry Ingestion
- **Context**: A failure in a security scanner or policy gate could either halt the application or allow unauthorized execution.
- **Decision**: Enforce Fail-Closed (`BLOCK`) for agent tool execution when security scanners fail; enforce Fail-Safe (safe buffer degradation) for telemetry ingestion.
- **Consequences**: Prevents security breaches during component outages while ensuring observability collection does not bring down the host platform.

### ADR-006: In-Flight PII Redaction Before Persistence
- **Context**: Storing raw PII (credit cards, SSNs, secrets) in telemetry storage violates HIPAA, GDPR, and PCI-DSS compliance.
- **Decision**: Execute `PIIMasker` directly in the ingestion pipeline before buffering or writing spans to DuckDB.
- **Consequences**: Telemetry storage never retains raw sensitive secrets. Non-sensitive tags (`pii_scrubbed=true`, `pii_types=[...]`) are retained for auditing.

### ADR-007: Cryptographic Hash-Chained Audit Trail
- **Context**: Audit logs stored in standard database tables can be silently altered or deleted by a compromised admin or database user.
- **Decision**: Chain audit log entries using SHA-256 hashes where `hash_i = SHA256(entry_i + hash_{i-1})`.
- **Consequences**: Any modification, insertion, or deletion of past audit entries immediately invalidates the cryptographic chain, providing tamper-evident forensic compliance.

### ADR-008: Dispatch-Time DNS Resolution for Webhooks (SSRF Firewall)
- **Context**: Webhooks pointing to external URLs can be exploited via Server-Side Request Forgery (SSRF) or DNS rebinding to access internal private networks (`127.0.0.1`, `169.254.169.254`).
- **Decision**: Re-resolve target hostnames to IP addresses immediately before socket connection in `webhook_notifier.py`, rejecting loopback, RFC1918, or cloud metadata IPs. Disable HTTP redirects (`follow_redirects=False`).
- **Consequences**: Completely blocks SSRF and DNS rebinding attacks on outbound webhooks.

### ADR-009: Multi-Signal Deterministic Precedence Policy Engine
- **Context**: Heuristic threat scores alone are easily obfuscated by adversarial prompt injection.
- **Decision**: Implement a policy engine combining threat scores, tool risk, data classification, and capability scope into a strict precedence hierarchy: `BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`.
- **Consequences**: Negative security signals hard-deny execution regardless of positive heuristics, creating a robust defense-in-depth model.

### ADR-010: Native OpenInference & OTLP Protocol Mapping
- **Context**: Enterprise applications use diverse framework abstractions (LangChain, LlamaIndex, custom OpenAI API wrappers).
- **Decision**: Map all ingress telemetry into a unified standard model (`CanonicalVantageSpan`) adhering to OpenTelemetry GenAI semantic conventions (`gen_ai.usage.input_tokens`, `gen_ai.input.messages`).
- **Consequences**: Vantage maintains total independence from agent framework implementation details.
