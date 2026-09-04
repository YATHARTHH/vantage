# Vantage: Project Vision, Use Cases, & Systems Requirements

## 1. Executive Summary & Domain Background

### The Paradigm Shift to Non-Deterministic Software Architecture
Modern enterprise applications are rapidly transitioning from deterministic code execution (where execution paths are strictly compiled or scripted) to **non-deterministic AI agent systems**. In an agentic architecture, Large Language Models (LLMs) act as reasoning engines that dynamically inspect inputs, construct multi-step execution plans, call external tools (databases, REST APIs, bash scripts), process intermediate outputs, and iterate until a goal is completed.

While this non-determinism provides unprecedented flexibility, it breaks the core assumptions of legacy observability and monitoring platforms.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             THE AI OBSERVABILITY CRISIS                                  │
├───────────────────────────────────────┬──────────────────────────────────────────────────┤
│ Traditional APM Assumptions           │ AI Agent Realities                               │
├───────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Static, deterministic execution paths │ Dynamic, autonomous LLM-generated plan graphs    │
│ Low-cardinality HTTP status codes     │ High-cardinality, unstructured text & tool calls │
│ Fixed memory & CPU resource bounds    │ Unbounded token consumption & dynamic loops      │
│ Post-hoc telemetry logging ("detect") │ Active runtime security enforcement ("block")    │
│ Input parameters fully sanitized upfront│ Prompt injections embedded in untrusted RAG data │
└───────────────────────────────────────┴──────────────────────────────────────────────────┘
```

### Why Legacy APM Tools Fail for AI Agents
1. **Opaque Multi-Step Execution Graphs (DAGs)**: Legacy APMs (Datadog, New Relic, AppDynamics) record HTTP endpoints and SQL query execution times. They cannot reconstruct parent-child DAG step dependencies, LLM prompt/completion metadata, dynamic tool invocation arguments, or agent iteration loops.
2. **Post-Hoc Observation vs. Inline Active Security Enforcement**: Legacy APMs operate entirely via passive background logging. When an AI agent suffers a prompt injection attack and issues an unauthorized `database.delete` command, passive logging merely records the data loss after the event occurs.
3. **Lack of Cryptographic Provenance & TOCTOU Protections**: Traditional APMs treat all incoming spans as trusted telemetry. They cannot differentiate developer system instructions from untrusted user inputs or third-party web content, exposing agents to indirect prompt injection and Time-Of-Check-To-Time-Of-Use (TOCTOU) argument tampering.
4. **No Deterministic Replay Capabilities**: Debugging a failed agent run in traditional tools is nearly impossible because LLM outputs are probabilistic. Without mocking downstream tool outputs and pinning model states, developers cannot reproduce bugs offline.

---

## 2. The Big Idea: Unified Real-Time AI Observability & Enforcement

**Vantage** is a production-grade AI & Engineering Observability and Active Security Enforcement platform. It bridges the gap between observability ("detect and report") and runtime control ("authorize and enforce").

```text
                    LLM / AGENT EXECUTION PATH
                                │
                                ▼
                   ┌───────────────────────────┐
                   │   SecurityContext (v1.2)  │
                   └────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
 Trust Provenance       Output Inspector &     Multi-Signal Threat
(TRUSTED / UNTRUSTED)   Schema Validation       Detection Scanner
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                   ┌───────────────────────────┐
                   │    Tool Authorizer        │
                   │ (Action + Resource + Env) │
                   └────────────┬──────────────┘
                                │
                                ▼
                   ┌───────────────────────────┐
                   │ Data & Destination Guard  │
                   │ (Classification & Trust)  │
                   └────────────┬──────────────┘
                                │
                                ▼
                   ┌───────────────────────────┐
                   │ Multi-Signal Policy Engine│
                   │ (BLOCK > APPROVAL > WARN) │
                   └────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
      ALLOW              REQUIRE_APPROVAL             BLOCK
        │                       │                       │
        │              Human Approval Workflow          │
        │              (Single-Use + TOCTOU Hash)       │
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                   ┌───────────────────────────┐
                   │   Execution Controller    │
                   │   (Sole Tool Choke Point) │
                   └────────────┬──────────────┘
                                │
                                ▼
                           TARGET TOOL
                                │
                                ▼
                   Hash-Chained Audit Trail
```

### The Core Architectural Imperative
> **"Detection provides evidence. Policy makes the decision. Authorization determines capability. Enforcement controls the side effect. Audit records why."**

Vantage achieves this through 5 core pillars:
1. **OpenTelemetry (OTLP) Native Telemetry Ingestion**: Direct support for standard OTLP/REST and OpenInference protocols with automatic PII/Secret redaction (Luhn checksum validation for credit cards, regex pattern scanning for SSNs, Bearer tokens, and API keys).
2. **Dual-Database Storage Engine**: High-performance DuckDB OLAP engine for sub-second analytical queries across millions of spans paired with SQLite/SQLAlchemy 2.0 for transactional metadata, API key management, and hash-chained audit trails.
3. **Mandatory Execution Controller Choke-Point**: A single enforcement point (`ExecutionController.execute(...)`) that intercepts all tool calls, verifying capabilities, data classifications, destination trust levels, and human approval status before tool execution occurs.
4. **Cryptographic Human-in-the-Loop Approval Workflow**: Single-use approval state machine with Time-Of-Check-To-Time-Of-Use (TOCTOU) action fingerprinting:
   $$\text{approval\_fingerprint} = \text{SHA256}(\text{canonical\_json}(\{\text{tool}, \text{action}, \text{resource}, \text{environment}, \text{arguments}\}))$$
5. **Deterministic Trace Replay Engine**: Reconstructs complete execution state from recorded spans and mocks downstream tool responses to allow offline debugging and "What-If" prompt tuning without side-effects.

---

## 3. Real-World Industry Use Cases

### Scenario A: Autonomous Financial Analyst Agent
* **Domain**: Hedge Fund / Investment Banking.
* **Workflow**: Agent ingests SEC 10-K filings, queries internal financial databases, computes valuation metrics, and posts summary alerts to external slack channels.
* **Vantage Role**:
  - Classifies internal financial metrics as `CONFIDENTIAL`/`RESTRICTED`.
  - Blocks data exfiltration if the agent attempts to route restricted financial figures to an `UNKNOWN_EXTERNAL` domain.
  - Limits execution budget via circuit breaker (`max_tool_calls_per_trace = 20`) to prevent infinite calculation loops.

### Scenario B: Enterprise Customer Support Bot
* **Domain**: Telecommunications / SaaS.
* **Workflow**: Customer support bot reads user tickets, queries order tables, and issues refund vouchers or account resets.
* **Vantage Role**:
  - Automatically redacts customer credit cards and SSNs via `PIIMasker` using Luhn validation before telemetry is stored.
  - Requires human approval (`REQUIRE_APPROVAL`) whenever the bot attempts to issue refunds exceeding $100 (`action="billing.refund"`).
  - Validates single-use approval so a granted refund approval cannot be replayed for subsequent transactions.

### Scenario C: Healthcare Medical Record Processing Agent
* **Domain**: Hospital Network / Health Insurance.
* **Workflow**: AI agent extracts patient diagnoses from clinical notes and submits claims to insurance portals.
* **Vantage Role**:
  - Enforces strict PII/PHI masking across all span attributes and prompt payload inputs.
  - Validates destination endpoints via dispatch-time DNS resolution and firewall checks to prevent SSRF attacks when connecting to external clearinghouses.
  - Generates tamper-evident, SHA-256 hash-chained audit trails for HIPAA compliance auditing.

### Scenario D: E-Commerce Autonomous Purchasing & Inventory Bot
* **Domain**: E-Commerce / Supply Chain Logistics.
* **Workflow**: Bot continuously monitors inventory levels and places automated purchase orders with external vendors.
* **Vantage Role**:
  - Enforces capability scoping (`inventory.read:warehouse_a:production` $\rightarrow$ `ALLOW`; `inventory.delete:*:production` $\rightarrow$ `BLOCK`).
  - Implements concurrency limits (`max_concurrent_agent_runs = 5`) and token rate limits to prevent runaway automated purchasing under inventory spikes.
  - Provides deterministic offline trace replays to diagnose why the agent selected vendor A over vendor B.

---

## 4. Differentiators Matrix

| Feature / Capability | Legacy APM (Datadog, New Relic) | Tracing Tools (LangSmith, Phoenix) | Static Guardrails (NeMo, LlamaGuard) | Vantage Active Enforcement Platform |
| :--- | :--- | :--- | :--- | :--- |
| **OTLP / OpenInference Native** | Generic HTTP Spans | Proprietary / Partial | None | **Native OTLP/REST & OpenTelemetry** |
| **In-Flight PII Redaction** | Server-side / Post-ingest | Partial / Client SDK | Stream filtering only | **In-flight Luhn & Regex before persistence** |
| **Inline Action Enforcement** | None (Passive Logging) | None (Passive Observability)| Pre-LLM / Post-LLM text only | **ExecutionController mandatory choke-point** |
| **Capability Model (RBAC)** | User UI roles only | User project access | None | **Principal $\rightarrow$ Agent $\rightarrow$ Action+Resource+Env** |
| **TOCTOU Action Fingerprinting** | None | None | None | **SHA-256 Canonical JSON Action Hash** |
| **Human Approval Semantics** | None | Basic UI review | None | **Single-use, atomic consume & stale policy check** |
| **Data Exfiltration Control** | None | None | Regex keyword block | **Data Sensitivity + Destination Trust Matrix** |
| **Deterministic Offline Replay** | None | Re-run prompt only | None | **Full State & Mock Tool Replay Engine** |
| **Audit Trail Tampering** | Standard database logs | Standard database logs | Log streams | **Cryptographic SHA-256 Hash Chain** |

---

## 5. Requirements & Scope Boundaries

### Functional Requirements
1. **OTLP Telemetry Ingestion**: Accept standard OTLP/HTTP JSON payloads at `/api/v1/otlp/v1/traces`, parse spans into `CanonicalVantageSpan`, and store in DuckDB.
2. **In-Flight PII/Secret Masking**: Scrub credit cards (Luhn valid), SSNs, API keys (`sk-...`, `vg_live_...`), and emails prior to queue buffering.
3. **Active Tool Security Enforcement**: Intercept all agent tool calls via `ExecutionController.execute(...)`. Evaluate capabilities, policy rules (`BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`), and exfiltration risks.
4. **TOCTOU Human Approval Workflow**: Implement approval requests with single-use consumption (`consumed_at`) and stale-policy version checks (`approved_policy_version == current_policy_version`).
5. **Deterministic Trace Replay**: Parse recorded DAG spans into a `ReplayManifest`, mock tool calls, and execute replay sessions with token cost tracking.
6. **Multi-State Circuit Breaking & Anomaly Detection**: Track trace budgets (`max_tool_calls_per_trace`, `max_high_risk_actions_per_trace`) and statistical anomalies (Z-score, error rates, volume spikes).

### Non-Functional Requirements
1. **Latency Targets**: Ingestion API endpoint response p95 $\le 15\text{ ms}$; `ExecutionController` policy evaluation overhead $\le 2\text{ ms}$.
2. **Buffer Losslessness & Resilience**: In-memory ring buffer with capacity `max_capacity=10000`. Overflows routed atomically to Dead-Letter Queue (`.dlq_spans.jsonl`).
3. **Fail-Closed Execution & Safe Degradation**: Security enforcement path fails closed (`BLOCK` on scanner failure). Telemetry ingestion path degrades safely.
4. **Data Isolation**: Strict multi-tenant isolation by `project_id` across database queries and API keys.

### Out-of-Scope Boundaries (Planned for Future Releases)
- Direct training set modification or model fine-tuning validation (`LLM04:2025 Data Poisoning`).
- Hardware-level GPU memory/kernel profilers (handled by NVIDIA DCGM).
- Automated legal compliance document generation (e.g. EU AI Act automated filing PDF generators).

---

## 6. Technical Challenges & Architectural Resolutions

Throughout the development of Vantage, critical engineering challenges arose when moving from passive telemetry to active runtime enforcement. Below is an explicit record of these problems, root cause analyses, and architectural fixes:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                      KEY TECHNICAL CHALLENGES & RESOLUTIONS                              │
├──────────────────────────┬─────────────────────────────────┬─────────────────────────────┤
│ Issue Encountered        │ Root Cause Analysis             │ Architectural Fix           │
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 1. TOCTOU Argument       │ LLM generated tool args in      │ Implemented SHA-256         │
│    Tampering             │ staging, obtained approval, then│ canonical JSON fingerprinting│
│                          │ modified args for production.   │ over Action+Resource+Env+Args│
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 2. Replay Approval Reuse │ Approvals were stored as static │ Added atomic single-use     │
│    Race Condition        │ booleans, allowing concurrent   │ consumption (consumed_at)   │
│                          │ requests to reuse one approval. │ & stale policy checks.      │
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 3. Ingestion Bottlenecks │ Synchronous DB writes blocked   │ Implemented bounded queue   │
│    Under Burst Load      │ HTTP worker threads under       │ with async background batch │
│                          │ 10,000 req/sec telemetry bursts.│ flusher & Dead-Letter Queue.│
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 4. Single Threat Score   │ Security decisions relied on a  │ Architected Multi-Signal    │
│    Bypasses              │ single threat score heuristic   │ Policy Engine with hard     │
│                          │ easily tricked by obfuscation.  │ precedence: BLOCK > APPROVAL│
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 5. Scanner Outage Crash  │ Security scanner failures threw │ Enforced fail-closed choke  │
│    Bypassing Gate        │ exceptions, causing default     │ point returning BLOCK with  │
│                          │ execution fallthrough.          │ SECURITY_ENGINE_FAILURE.    │
└──────────────────────────┴─────────────────────────────────┴─────────────────────────────┘
```

1. **Challenge 1: Time-Of-Check-To-Time-Of-Use (TOCTOU) Argument Tampering**
   - *Problem*: An LLM agent requested human approval for `database.write:orders:staging`, but after human approval was granted, the agent altered the environment parameter to `production` or changed the SQL payload while keeping the same approval ID.
   - *Fix*: Designed `compute_action_fingerprint()` which computes a cryptographic SHA-256 hash over canonical JSON encompassing `tool`, `action`, `resource`, `environment`, and `arguments` with `sort_keys=True`. If any field differs at execution time, `ExecutionController` blocks execution with `reason_code = "APPROVAL_FINGERPRINT_MISMATCH"`.

2. **Challenge 2: Approval Replay Race Condition across Concurrent Workers**
   - *Problem*: Approval records used boolean flags (`is_approved = true`), allowing two fast concurrent requests to execute the same privileged action twice.
   - *Fix*: Implemented atomic single-use consumption semantics in `HumanApprovalWorkflow.consume_approval()`. The workflow verifies `consumed_at is None`, atomically writes `consumed_at = time.time()`, and verifies `approved_policy_version == current_policy_version`.

3. **Challenge 3: Telemetry Ingestion Bottlenecks & Worker Blocking**
   - *Problem*: Under high-throughput span ingestion bursts, synchronous DuckDB writes locked the HTTP thread pool, dropping connections.
   - *Fix*: Built `BoundedIngestBuffer` with `collections.deque(maxlen=10000)` and background async batch worker flushing every 500ms or 100 spans. Overflows are safely offloaded to an atomic Dead-Letter Queue (`.dlq_spans.jsonl`).

4. **Challenge 4: Vulnerability of Single-Heuristic Threat Scoring**
   - *Problem*: Relying solely on a model threat score (e.g. 0.72) allowed prompt injections wrapped in complex base64 or unicode obfuscation to bypass security gates.
   - *Fix*: Replaced score-only decisions with the `MultiSignalPolicyGate`. The engine combines threat scores, provenance classifications, tool capability grants, data sensitivity, and destination trust into deterministic rules with strict decision precedence (`BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`).

5. **Challenge 5: Scanner Failures Bypassing Security Gates**
   - *Problem*: If an external threat scanner backend crashed or timed out, the system raised uncaught exceptions that bypassed security enforcement.
   - *Fix*: Wrapped policy evaluation in `ExecutionController.execute()` in a fail-closed try-except block. Any scanner exception returns an immediate `status = "BLOCKED"` with `reason_code = "SECURITY_ENGINE_FAILURE"`. Telemetry ingestion, conversely, degrades safely without crashing the platform.
