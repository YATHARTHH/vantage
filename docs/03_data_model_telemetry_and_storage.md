# Vantage Telemetry, Storage Architecture, & Database Schemas

Welcome to **Document 03**! This document explains exactly how Vantage stores data, why we use two separate databases instead of one, and the purpose of every table and field in the system.

---

## ❓ Quick Concepts to Understand First

### What is OLAP vs OLTP? (Simple Explanation)

These are two completely different types of database workloads:

| Term | Full Name | What It Does | Best For |
|:-----|:----------|:-------------|:---------|
| **OLAP** | Online Analytical Processing | Reads huge amounts of data very fast to answer questions like "What was the average cost over the last 7 days?" | Analytics, dashboards, aggregations |
| **OLTP** | Online Transactional Processing | Handles frequent small reads and writes with strict accuracy guarantees. Must always be consistent. | Creating/updating API keys, recording approvals, writing audit logs |

> 💡 **Simple Analogy**: OLAP is like a library where you scan thousands of books quickly to find a theme. OLTP is like a bank teller — every transaction must be perfectly accurate, no room for errors.

---

### Why Do We Use Two Databases Instead of One?

This is one of the most important architectural decisions in Vantage. Here is the problem with using just one database:

- If you use **PostgreSQL for everything**, then heavy analytical queries (scanning millions of spans) block and slow down security operations (checking API keys, recording audit logs). During peak traffic, this causes the entire system to crawl.
- If you use **DuckDB for everything**, it is great at analytics but does not support the strict transactional guarantees needed to safely manage API keys, approvals, and security audit logs.

**Our Solution**: Use each database for what it is best at:
- 🦆 **DuckDB** → Fast analytical queries over millions of telemetry spans (OLAP workload)
- 🗄️ **SQLite** → Strict transactional accuracy for security metadata (OLTP workload)

This eliminates database lock contention and gives us sub-second analytics without slowing down security enforcement.

---

## 1. Dual-Database Subsystem Architecture

Vantage employs a specialized dual-database storage subsystem. By decoupling high-throughput streaming telemetry from relational application state, Vantage achieves sub-second analytical query performance across millions of spans while maintaining strict ACID transaction guarantees for security and compliance metadata.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                            DUAL-DATABASE SUBSYSTEM ARCHITECTURE                          │
├───────────────────────────────────────────┬──────────────────────────────────────────────┤
│ DuckDB OLAP Columnar Backend              │ SQLite / SQLAlchemy 2.0 OLTP Backend         │
├───────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Immutable streaming telemetry spans       │ Relational application state & metadata      │
│ High-cardinality analytical aggregations  │ API keys, RBAC roles, & project isolation    │
│ Parquet-backed columnar file storage      │ Alerting rules & security suppression states  │
│ Vectorized SIMD query execution           │ Cryptographic SHA-256 hash-chained audit log │
└───────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 2. Telemetry & OTLP Protocol Mapping

### CanonicalVantageSpan Data Model

#### Why Does This Model Exist?
Different AI frameworks name things differently. LangChain might call token count `llm.usage.prompt_tokens`. LlamaIndex might call it `gen_ai.usage.input_tokens`. OpenAI's SDK might use a completely different field name.

If Vantage stored each framework's raw format, every query and analytics feature would need to know about every framework's quirks. That would be a maintenance nightmare.

**The solution**: We normalize everything into one single standard model — `CanonicalVantageSpan`. No matter which framework or SDK sends the data, it is always transformed into this same shape before being stored in DuckDB. All queries and analytics then work against this single, predictable model.

All incoming telemetry spans (via OTLP/REST, OpenInference, or custom SDK connectors) are normalized into the `CanonicalVantageSpan` domain entity (`vantage/domain/models.py`) before buffering or persistence.

```python
class CanonicalVantageSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: str  # LLM, TOOL, AGENT, CHAIN, RETRIEVER
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status_code: str  # OK, ERROR, UNSET
    status_message: Optional[str] = None

    project_id: str
    source_tool: str
    source_identifier: str

    # GenAI Semantic Conventions
    model_name: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    # Prompts & Completions (Subject to log_prompts setting & PII Masker)
    prompt_text: Optional[str] = None
    completion_text: Optional[str] = None

    # Security & Audit Attributes
    pii_scrubbed: bool = False
    pii_types: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
```

### OpenTelemetry GenAI Semantic Convention Attributes
Vantage maps standard OpenTelemetry span attributes directly to analytical fields:
- `gen_ai.system` / `gen_ai.request.model` $\rightarrow$ `model_name`
- `gen_ai.usage.input_tokens` / `llm.usage.prompt_tokens` $\rightarrow$ `input_tokens`
- `gen_ai.usage.output_tokens` / `llm.usage.completion_tokens` $\rightarrow$ `output_tokens`
- `gen_ai.input.messages` / `input.value` $\rightarrow$ `prompt_text`
- `gen_ai.output.choices` / `output.value` $\rightarrow$ `completion_text`

---

## 3. SQLite Transactional Metadata Schema (SQLAlchemy 2.0)

### Why SQLite for This?
SQLite stores all the "rules" and "state" of the system — things like who has access, what limits are set, and what actions were taken. These records are small (a few rows at a time) but must be 100% accurate (no data loss, no inconsistency). SQLite with SQLAlchemy 2.0 gives us strict ACID guarantees with an async API that fits perfectly alongside FastAPI.

The relational SQLite database (managed via SQLAlchemy 2.0 async ORM) enforces enterprise governance, access control, and audit compliance across 10 core tables:

### 1. `projects` Table
**What is this for?** Vantage is multi-tenant — multiple teams or AI applications can use the same Vantage server, but their data must be isolated from each other. The `projects` table defines these isolation boundaries. Every span, API key, alert rule, and policy is scoped to a `project_id`.

- `id` (`VARCHAR`, PK): Unique project identifier (e.g. `proj_alpha`).
- `display_name` (`VARCHAR`, Not Null): Human-readable name.
- `project_type` (`VARCHAR`, Not Null): Domain type (`LLM_APPLICATION`, `AGENT_WORKFLOW`, `MODEL_SERVICE`).
- `owner_team` (`VARCHAR`, Not Null): Team assignment.
- `owner_email` (`VARCHAR`, Not Null): Primary contact email.
- `description` (`TEXT`): Project description.
- `log_prompts` (`BOOLEAN`, Default `False`): **Privacy flag** — if `False`, prompt text and completion text are never stored. Token counts and costs are still tracked. Use this for HIPAA or GDPR-sensitive projects.
- `active` (`BOOLEAN`, Default `True`): Active lifecycle status.
- `created_at` (`DATETIME`): Project creation timestamp.

### 2. `project_source_mappings` Table
**What is this for?** Multiple agents from different frameworks can send data into the same project. This table maps external SDK identifiers (e.g. `langchain:my-agent-v2`) to the correct internal project so incoming spans are automatically routed to the right project without the SDK needing to know internal IDs.

- `id` (`INTEGER`, PK, Autoincrement)
- `project_id` (`VARCHAR`, FK `projects.id`): Associated project.
- `source_tool` (`VARCHAR`, Not Null): Instrumenting tool (e.g. `langchain`, `llamaindex`, `openai`).
- `source_identifier` (`VARCHAR`, Not Null): Source identifier string.
- `display_label` (`VARCHAR`): Friendly display name.
- `created_at` (`DATETIME`)
- *Constraint*: `UniqueConstraint("source_tool", "source_identifier")` — prevents duplicate source registrations.

### 3. `experiments` Table
**What is this for?** Before deploying a new prompt version or switching AI models, engineering teams run A/B experiments offline. This table stores experiment metadata — the hypothesis, the model configurations being compared, the results, and the learnings. Think of it as a scientific notebook for prompt engineering.

- `id` (`VARCHAR`, PK)
- `title` (`VARCHAR`, Not Null), `slug` (`VARCHAR`, Unique, Not Null)
- `project_id` (`VARCHAR`, FK `projects.id`)
- `status` (`VARCHAR`): `planned`, `running`, `completed`, `archived`.
- `hypothesis` (`TEXT`), `objective` (`TEXT`), `owner_name` (`VARCHAR`), `owner_team` (`VARCHAR`), `owner_email` (`VARCHAR`)
- `start_date` (`DATE`), `expected_end` (`DATE`), `actual_end` (`DATE`)
- `dataset_description` (`TEXT`), `baseline_description` (`TEXT`), `model_configurations` (`TEXT` JSON)
- `outcome` (`VARCHAR`), `result_summary` (`TEXT`), `metrics_json` (`TEXT`), `learnings` (`TEXT`), `recommendations` (`TEXT`), `artefacts_json` (`TEXT`), `tags_json` (`TEXT`)
- `created_at` (`DATETIME`), `updated_at` (`DATETIME`)

### 4. `alert_rules` Table
**What is this for?** This table stores the configuration for each anomaly detector — specifically, at what threshold level should an alert fire? For example: "For project `proj_alpha`, send a WARNING alert if the average LLM latency is more than 2 standard deviations above normal."

Without this table, the anomaly detectors would have no thresholds to compare against. Every project can have its own custom thresholds.

- `id` (`INTEGER`, PK, Autoincrement)
- `project_id` (`VARCHAR`, Not Null)
- `detector_type` (`VARCHAR`, Not Null): `z_score`, `threshold`, `rate_of_change`, `error_rate`, `volume_spike`.
- `metric_name` (`VARCHAR`, Not Null): Target metric (e.g. `latency_ms`, `token_cost_usd`, `error_rate_pct`).
- `warn_z` (`FLOAT`, Default `2.0`): Warning Z-score threshold (2 standard deviations = unusual).
- `crit_z` (`FLOAT`, Default `3.0`): Critical Z-score threshold (3 standard deviations = very unusual).
- `absolute_threshold` (`FLOAT`): Hard cap — e.g. always alert if cost > $5.00, regardless of historical baseline.
- `rate_change_factor` (`FLOAT`, Default `1.5`): Alert if a metric jumps by 150% in one period.
- `error_rate_pct` (`FLOAT`, Default `5.0`): Alert if error rate exceeds 5% of all spans.
- `enabled` (`BOOLEAN`, Default `True`)
- *Constraint*: `UniqueConstraint("project_id", "detector_type", "metric_name")` — one rule per metric per project.

### 5. `alert_records` Table
**What is this for?** Every time an anomaly detector fires (or a security policy blocks a tool call), the event is recorded here as an `alert_record`. This creates a full history of every incident — both observability incidents (cost spike, latency spike) and security incidents (prompt injection blocked). The security dashboard reads from this table to show the incident feed.

- `id` (`INTEGER`, PK, Autoincrement)
- `alert_uuid` (`VARCHAR`, Unique, Not Null)
- `project_id` (`VARCHAR`, Not Null)
- `detector_type` (`VARCHAR`, Not Null), `metric_name` (`VARCHAR`, Not Null)
- `severity` (`VARCHAR`, Not Null): `info`, `warning`, `critical`.
- `message` (`TEXT`, Not Null), `current_value` (`FLOAT`), `baseline_value` (`FLOAT`): The actual value that triggered the alert and the historical baseline for comparison.
- `fired_at` (`DATETIME`), `resolved_at` (`DATETIME`), `notified` (`BOOLEAN`): Tracks when the alert fired, when it was resolved, and whether a webhook notification was sent.
- `category` (`VARCHAR`, Default `"observability"`): `observability` (performance) or `security` (threat events).
- `security_incident_key` (`VARCHAR`), `trace_id` (`VARCHAR`), `span_id` (`VARCHAR`), `threat_types_json` (`TEXT`): Links a security alert back to the exact span and threat types that triggered it.

### 6. `alert_suppression_rules` Table
**What is this for?** Imagine the same alert fires 200 times per day because a known, non-critical issue keeps recurring (e.g. a third-party API is always slow on weekends). Without suppression, engineers get flooded with 200 identical notifications and start ignoring all alerts — known as "alert fatigue."

Suppression rules let admins say: "Mute this specific alert pattern until Monday." The alert is still logged (with `severity = "info"` and `notified = false`), but no webhook notification is sent.

- `id` (`INTEGER`, PK, Autoincrement)
- `rule_id` (`VARCHAR`, Unique, Not Null)
- `project_id` (`VARCHAR`, Not Null), `detector_type` (`VARCHAR`, Not Null), `incident_key` (`VARCHAR`, Not Null)
- `pattern_text` (`TEXT`): Optional pattern to match against alert messages.
- `expires_at` (`DATETIME`): When the suppression rule expires and alerts resume.
- `scope` (`VARCHAR`), `created_at` (`DATETIME`)

### 7. `local_cache_records` Table
**What is this for?** LLM API calls are expensive. If 100 users ask the same question (e.g. "What are your business hours?"), calling GPT-4o 100 times wastes money. This table caches LLM responses so identical prompts are served from cache instead of making a new API call.

How it works: When a prompt arrives, Vantage computes a SHA-256 hash of the normalized prompt text. If the same hash already exists in this table, the cached response is returned instantly — zero token cost, zero latency.

- `id` (`INTEGER`, PK, Autoincrement)
- `cache_id` (`VARCHAR`, Unique, Not Null), `project_id` (`VARCHAR`, Not Null), `model_name` (`VARCHAR`, Not Null)
- `exact_hash` (`VARCHAR`, Not Null, Indexed): SHA-256 hash of normalized prompt input — this is the cache lookup key.
- `prompt_template_version` (`VARCHAR`), `context_fingerprint` (`VARCHAR`)
- `prompt_text` (`TEXT`), `response_text` (`TEXT`): The original prompt and cached answer.
- `tokens_input` (`INTEGER`), `tokens_output` (`INTEGER`), `original_cost_usd` (`FLOAT`): Stored so cost savings can be calculated as `hit_count × original_cost_usd`.
- `hit_count` (`INTEGER`), `created_at` (`DATETIME`), `last_hit_at` (`DATETIME`), `expires_at` (`DATETIME`)

### 8. `project_policies` Table
**What is this for?** This table defines the circuit breaker limits for each project. Without it, a runaway AI agent could burn unlimited tokens in a single trace (one continuous agent execution flow). By setting limits here, the `TraceActionCircuitBreaker` knows when to trip and halt execution.

Example: If `max_cost_per_trace_usd = 0.50`, any single agent trace that accumulates more than $0.50 in token costs will be immediately halted.

- `project_id` (`VARCHAR`, PK)
- `max_cost_per_trace_usd` (`FLOAT`, Default `0.50`): Max USD budget per trace sequence.
- `max_tokens_per_trace` (`INTEGER`, Default `30000`): Max token budget per trace sequence.
- `max_retry_loops` (`INTEGER`, Default `3`): Max permitted agent loop iterations before halting.
- `enabled` (`BOOLEAN`, Default `True`), `updated_at` (`DATETIME`)

### 9. `api_keys` Table
**What is this for?** Every API request to Vantage must carry a valid API key. This table stores the keys — but critically, it **never stores the raw secret key**. Only a SHA-256 hash of the key is stored. This means even if the database is compromised, attackers cannot extract usable API keys.

How authentication works: When a request arrives with `Authorization: Bearer vg_sk_abc123...`, Vantage computes `SHA256("vg_sk_abc123...")` and checks if that hash exists and has `status = "active"` in this table.

- `key_id` (`VARCHAR`, PK): Public identifier (e.g. `vg_key_9f8a...`) — safe to share, not secret.
- `key_hash` (`VARCHAR`, Unique, Not Null, Indexed): SHA-256 digest of secret API key — the actual secret is never stored.
- `display_name` (`VARCHAR`, Not Null)
- `role` (`VARCHAR`, Default `"developer"`): RBAC role (`admin`, `developer`, `viewer`).
- `project_id` (`VARCHAR`): Optional project isolation scope — if set, this key can only access data for this project.
- `status` (`VARCHAR`, Default `"active"`): `active` or `revoked`. Revocation is a soft-delete (the row stays for audit purposes).
- `created_at` (`DATETIME`), `expires_at` (`DATETIME`), `revoked_at` (`DATETIME`), `last_used_at` (`DATETIME`)

### 10. `audit_logs` Table
**What is this for?** This is the compliance log — every sensitive administrative action (creating API keys, updating policies, blocking a security threat) is permanently recorded here. But unlike a normal log table, these entries are **cryptographically chained** so that if anyone modifies or deletes a past record, it is immediately detectable.

How the chain works: Each new log entry includes the SHA-256 hash of the PREVIOUS entry. So entry #5's hash depends on entry #4's hash, which depends on entry #3's hash, and so on. If someone goes into the database and changes entry #3 directly, entries #4, #5, and every entry after it will have broken hash values. The integrity check at `GET /api/v1/audit/logs` will immediately report `chain_valid: false`.

This is the same technique used by blockchains — each block includes the hash of the previous block.

- `id` (`INTEGER`, PK, Autoincrement)
- `timestamp` (`DATETIME`, Indexed)
- `actor_key_id` (`VARCHAR`, Not Null): Who performed this action (which API key).
- `project_id` (`VARCHAR`, Indexed): Which project was affected.
- `action` (`VARCHAR`, Not Null): What happened (e.g. `api_key.create`, `policy.update`, `tool.blocked`).
- `resource_type` (`VARCHAR`, Not Null), `resource_id` (`VARCHAR`)
- `details_json` (`TEXT`): Redacted JSON metadata about the action (PII already removed).
- `previous_hash` (`VARCHAR`, Not Null): SHA-256 hash of the preceding row (`hash_{i-1}`) — the chain link.
- `record_hash` (`VARCHAR`, Not Null): Cryptographic hash of this entry: `SHA256(row_contents + previous_hash)`.

---

## 4. DuckDB OLAP Analytical Schema & SQL Aggregations

### Why DuckDB for Telemetry?
Every time an AI agent makes an LLM call or invokes a tool, Vantage stores a record of it as a "span" in DuckDB. Over time, a busy AI system can produce millions of these spans per day.

Standard row-based databases (PostgreSQL, SQLite) store data row-by-row, so a query like `SELECT AVG(latency)` has to read EVERY field of EVERY row even though it only needs the `latency` column. This is slow.

DuckDB stores data column-by-column. For a query like `SELECT AVG(latency)`, it reads only the `latency` column from disk — skipping all other columns entirely. This is called **columnar storage** and it is 50-100x faster for analytics.

DuckDB maintains columnar Parquet-backed analytical tables in `vantage.duckdb` optimized for sub-second analytical queries.

### Table: `telemetry_spans`
```sql
CREATE TABLE IF NOT EXISTS telemetry_spans (
    trace_id VARCHAR NOT NULL,
    span_id VARCHAR NOT NULL,
    parent_span_id VARCHAR,
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_ms DOUBLE NOT NULL,
    status_code VARCHAR NOT NULL,
    status_message VARCHAR,
    project_id VARCHAR NOT NULL,
    source_tool VARCHAR NOT NULL,
    source_identifier VARCHAR NOT NULL,
    model_name VARCHAR,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd DOUBLE DEFAULT 0.0,
    prompt_text TEXT,
    completion_text TEXT,
    pii_scrubbed BOOLEAN DEFAULT FALSE,
    pii_types VARCHAR,
    attributes JSON,
    events JSON,
    PRIMARY KEY (trace_id, span_id)
);
```

### High-Performance Analytical Query Patterns

These are the actual SQL queries Vantage runs against DuckDB to power the analytics dashboard. They are triggered automatically by the `/api/v1/analytics/rollups` endpoint every hour, or on-demand when a user opens the dashboard.

#### 1. Hourly Token Usage & Latency Quantiles per Model
**What this tells us**: For each AI model (GPT-4o, Claude 3.5, etc.) in the last 24 hours — how many calls were made, how many tokens were consumed, what was the total cost, and what was the p95 (95th percentile) latency? This powers the cost breakdown chart in the dashboard.
```sql
SELECT
    model_name,
    COUNT(span_id) AS total_spans,
    SUM(total_tokens) AS total_tokens,
    SUM(cost_usd) AS total_cost_usd,
    AVG(duration_ms) AS avg_latency_ms,
    QUANTILE_CONT(duration_ms, 0.95) AS p95_latency_ms
FROM telemetry_spans
WHERE project_id = 'proj_alpha'
  AND start_time >= NOW() - INTERVAL '24 HOURS'
  AND kind = 'LLM'
GROUP BY model_name
ORDER BY total_cost_usd DESC;
```

#### 2. Agent Execution Loop & Error Rate Analysis
**What this tells us**: For each agent trace (a complete multi-step agent run), how many steps did it take, how many errored, what was the total cost, and what was the slowest step? This query helps identify runaway agents (high `total_steps`) and problematic traces (high `error_count`). The `HAVING total_steps > 10 OR error_count > 0` filter focuses attention only on traces that are expensive or failing.
```sql
SELECT
    trace_id,
    COUNT(span_id) AS total_steps,
    SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS error_count,
    SUM(cost_usd) AS total_trace_cost,
    MAX(duration_ms) AS max_step_duration
FROM telemetry_spans
WHERE project_id = 'proj_alpha'
GROUP BY trace_id
HAVING total_steps > 10 OR error_count > 0
ORDER BY total_trace_cost DESC;
```
