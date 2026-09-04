# Vantage Telemetry, Storage Architecture, & Database Schemas

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

The relational SQLite database (managed via SQLAlchemy 2.0 async ORM) enforces enterprise governance, access control, and audit compliance across 9 core tables:

### 1. `projects` Table
Stores enterprise project isolation boundaries and privacy log settings.
- `id` (`VARCHAR`, PK): Unique project identifier (e.g. `proj_alpha`).
- `display_name` (`VARCHAR`, Not Null): Human-readable name.
- `project_type` (`VARCHAR`, Not Null): Domain type (`LLM_APPLICATION`, `AGENT_WORKFLOW`, `MODEL_SERVICE`).
- `owner_team` (`VARCHAR`, Not Null): Team assignment.
- `owner_email` (`VARCHAR`, Not Null): Primary contact email.
- `description` (`TEXT`): Project description.
- `log_prompts` (`BOOLEAN`, Default `False`): Privacy flag toggling prompt/completion persistence.
- `active` (`BOOLEAN`, Default `True`): Active lifecycle status.
- `created_at` (`DATETIME`): Project creation timestamp.

### 2. `project_source_mappings` Table
Maps external SDK instrumentation source tools to internal projects.
- `id` (`INTEGER`, PK, Autoincrement)
- `project_id` (`VARCHAR`, FK `projects.id`): Associated project.
- `source_tool` (`VARCHAR`, Not Null): Instrumenting tool (e.g. `langchain`, `llamaindex`, `openai`).
- `source_identifier` (`VARCHAR`, Not Null): Source identifier string.
- `display_label` (`VARCHAR`): Friendly display name.
- `created_at` (`DATETIME`)
- *Constraint*: `UniqueConstraint("source_tool", "source_identifier")`.

### 3. `experiments` Table
Manages offline prompt evaluation, model comparison, and benchmark experiments.
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
Configures multi-signal statistical anomaly detector thresholds per project.
- `id` (`INTEGER`, PK, Autoincrement)
- `project_id` (`VARCHAR`, Not Null)
- `detector_type` (`VARCHAR`, Not Null): `z_score`, `threshold`, `rate_of_change`, `error_rate`, `volume_spike`.
- `metric_name` (`VARCHAR`, Not Null): Target metric (e.g. `latency_ms`, `token_cost_usd`, `error_rate_pct`).
- `warn_z` (`FLOAT`, Default `2.0`): Warning Z-score multiplier.
- `crit_z` (`FLOAT`, Default `3.0`): Critical Z-score multiplier.
- `absolute_threshold` (`FLOAT`): Hard static threshold.
- `rate_change_factor` (`FLOAT`, Default `1.5`): Multiplicative rate-of-change limit.
- `error_rate_pct` (`FLOAT`, Default `5.0`): Error percentage threshold.
- `enabled` (`BOOLEAN`, Default `True`)
- *Constraint*: `UniqueConstraint("project_id", "detector_type", "metric_name")`.

### 5. `alert_records` Table
Stores historical alert notifications and security incidents.
- `id` (`INTEGER`, PK, Autoincrement)
- `alert_uuid` (`VARCHAR`, Unique, Not Null)
- `project_id` (`VARCHAR`, Not Null)
- `detector_type` (`VARCHAR`, Not Null), `metric_name` (`VARCHAR`, Not Null)
- `severity` (`VARCHAR`, Not Null): `info`, `warning`, `critical`.
- `message` (`TEXT`, Not Null), `current_value` (`FLOAT`), `baseline_value` (`FLOAT`)
- `fired_at` (`DATETIME`), `resolved_at` (`DATETIME`), `notified` (`BOOLEAN`)
- `category` (`VARCHAR`, Default `"observability"`): `observability` or `security`.
- `security_incident_key` (`VARCHAR`), `trace_id` (`VARCHAR`), `span_id` (`VARCHAR`), `threat_types_json` (`TEXT`)

### 6. `alert_suppression_rules` Table
Stores alert suppression rules to prevent notification fatigue.
- `id` (`INTEGER`, PK, Autoincrement)
- `rule_id` (`VARCHAR`, Unique, Not Null)
- `project_id` (`VARCHAR`, Not Null), `detector_type` (`VARCHAR`, Not Null), `incident_key` (`VARCHAR`, Not Null)
- `pattern_text` (`TEXT`), `expires_at` (`DATETIME`), `scope` (`VARCHAR`), `created_at` (`DATETIME`)

### 7. `local_cache_records` Table
Stores exact-match LLM query cache hits and cost savings.
- `id` (`INTEGER`, PK, Autoincrement)
- `cache_id` (`VARCHAR`, Unique, Not Null), `project_id` (`VARCHAR`, Not Null), `model_name` (`VARCHAR`, Not Null)
- `exact_hash` (`VARCHAR`, Not Null, Indexed): SHA-256 hash of normalized prompt input.
- `prompt_template_version` (`VARCHAR`), `context_fingerprint` (`VARCHAR`)
- `prompt_text` (`TEXT`), `response_text` (`TEXT`)
- `tokens_input` (`INTEGER`), `tokens_output` (`INTEGER`), `original_cost_usd` (`FLOAT`)
- `hit_count` (`INTEGER`), `created_at` (`DATETIME`), `last_hit_at` (`DATETIME`), `expires_at` (`DATETIME`)

### 8. `project_policies` Table
Defines cost and token circuit breaker thresholds per project trace.
- `project_id` (`VARCHAR`, PK)
- `max_cost_per_trace_usd` (`FLOAT`, Default `0.50`): Max USD budget per trace sequence.
- `max_tokens_per_trace` (`INTEGER`, Default `30000`): Max token budget per trace sequence.
- `max_retry_loops` (`INTEGER`, Default `3`): Max permitted agent loop iterations.
- `enabled` (`BOOLEAN`, Default `True`), `updated_at` (`DATETIME`)

### 9. `api_keys` Table
Stores RBAC access control credentials and hashed API keys.
- `key_id` (`VARCHAR`, PK): Public identifier (e.g. `vg_key_9f8a...`).
- `key_hash` (`VARCHAR`, Unique, Not Null, Indexed): SHA-256 digest of secret API key.
- `display_name` (`VARCHAR`, Not Null)
- `role` (`VARCHAR`, Default `"developer"`): RBAC role (`admin`, `developer`, `viewer`).
- `project_id` (`VARCHAR`): Optional project isolation scope.
- `status` (`VARCHAR`, Default `"active"`): `active` or `revoked`.
- `created_at` (`DATETIME`), `expires_at` (`DATETIME`), `revoked_at` (`DATETIME`), `last_used_at` (`DATETIME`)

### 10. `audit_logs` Table
Tamper-evident, cryptographically chained compliance log table.
- `id` (`INTEGER`, PK, Autoincrement)
- `timestamp` (`DATETIME`, Indexed)
- `actor_key_id` (`VARCHAR`, Not Null): Key ID of performing principal.
- `project_id` (`VARCHAR`, Indexed): Target project ID.
- `action` (`VARCHAR`, Not Null): Action performed (e.g. `api_key.create`, `policy.update`).
- `resource_type` (`VARCHAR`, Not Null), `resource_id` (`VARCHAR`)
- `details_json` (`TEXT`): Redacted JSON action metadata.
- `previous_hash` (`VARCHAR`, Not Null): SHA-256 hash of preceding row entry (`hash_{i-1}`).
- `record_hash` (`VARCHAR`, Not Null): Cryptographic hash of current entry ($\text{SHA256}(\text{row\_contents} + \text{previous\_hash})$).

---

## 4. DuckDB OLAP Analytical Schema & SQL Aggregations

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

#### 1. Hourly Token Usage & Latency Quantiles per Model
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
