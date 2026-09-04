# Vantage Replay Engine, DAG Visualizer, Circuit Breaker, & Intelligence Engines

## 1. Deterministic Replay & What-If Engine

Debugging non-deterministic LLM applications is notoriously difficult because model outputs vary across executions. Vantage provides a deterministic **Replay & What-If Intelligence Engine** (`vantage/services/replay_service.py` & `vantage/replay/engine.py`) that reconstructs past agent executions, mocks downstream tool side-effects, and allows developers to test modified prompt templates offline.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             DETERMINISTIC REPLAY PIPELINE                                │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Historical Trace Spans (DuckDB OLAP Columnar Storage)                                │
│                                    │                                                     │
│                                    ▼                                                     │
│ 2. ReplayManifest Construction (Step Hierarchy, Tool Stubs, Prompts)                     │
│                                    │                                                     │
│                                    ▼                                                     │
│ 3. Mock Downstream Tools (Zero External API Side-Effects)                                │
│                                    │                                                     │
│                                    ▼                                                     │
│ 4. Execute What-If Prompt Fork (Modified System Prompts / Models)                        │
│                                    │                                                     │
│                                    ▼                                                     │
│ 5. Calculate Cost Delta & Output Divergence Analysis                                     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### The `ReplayManifest` Data Model
```python
class ReplayStepMock(BaseModel):
    step_id: str
    tool_name: str
    input_args: Dict[str, Any]
    mocked_output: Any
    latency_ms: float

class ReplayManifest(BaseModel):
    manifest_id: str
    original_trace_id: str
    project_id: str
    initial_prompt: str
    system_instruction: str
    model_name: str
    temperature: float
    step_mocks: List[ReplayStepMock]
```

### Execution Flow & Zero Side-Effect Guarantee
1. **Manifest Extraction**: Extracts the recorded parent-child DAG hierarchy for a target `trace_id` from DuckDB.
2. **Tool Mock Inserter**: Replaces live network dependencies (database queries, HTTP dispatches, credit card APIs) with recorded historical outputs (`ReplayStepMock`).
3. **What-If Prompt Injection**: Executes the agent loop using a candidate system prompt (e.g. testing prompt `v2.1` against prompt `v1.0`).
4. **Divergence Analysis**: Compares token counts, latency deltas, tool call choices, and final execution outputs against baseline traces without triggering real-world external side-effects.

---

## 2. Dynamic Frontend SVG DAG Visualizer

The Vantage SPA (`frontend/src/components/DAGVisualizer.tsx`) renders interactive, dynamic Directed Acyclic Graphs (DAGs) representing complex multi-step agent execution trees.

```text
  [Root Agent Execution] (1,450ms | 1,200 tokens | $0.024)
          │
          ├──► [LLM Step 1: Query Planner] (320ms | 450 tokens)
          │         │
          │         └──► [Tool: database.read] (45ms | 0 tokens)
          │
          └──► [LLM Step 2: Summarizer] (850ms | 750 tokens)
                    │
                    └──► [Tool: http.post] (180ms | 0 tokens) -- [BLOCKED BY POLICY]
```

### Visualizer Key Capabilities
- **Hierarchical Layout Algorithm**: Computes vertical and horizontal node positioning dynamically based on `parent_span_id` relationships and start timestamps.
- **Cost & Token Heatmapping**: Colors nodes dynamically (green to orange to red) based on token cost thresholds and execution duration relative to trace totals.
- **Interactive Security Highlights**: Nodes intercepted by `ExecutionController` are highlighted with status badges (`ALLOW`, `WARN`, `REQUIRE_APPROVAL`, `BLOCK`).
- **Span Inspection Panel**: Clicking a DAG node opens a side drawer displaying raw input JSON, PII scrubbing indicators, sanitized arguments, and matched security policy rules.

---

## 3. Multi-State Policy Circuit Breaker

The `TraceActionCircuitBreaker` (`vantage/core/circuit_breaker.py`) and project cost policies protect agent deployments against runaway cost spikes, infinite tool execution loops, and unbounded resource consumption (`LLM10:2025`).

```text
             ┌──────────────────────────────────────────────┐
             │                   CLOSED                     │
             │         (Normal Execution Operating)         │
             └──────────────────────┬───────────────────────┘
                                    │
                       Metric Z-Score > 3.0 /
                    Trace Budget Exceeded (50 calls)
                                    │
                                    ▼
             ┌──────────────────────────────────────────────┐
             │                    OPEN                      │
             │     (Hard Block: Requests Rejected)          │
             └──────────────────────┬───────────────────────┘
                                    │
                      Cooldown Window Expires (60s)
                                    │
                                    ▼
             ┌──────────────────────────────────────────────┐
             │                  HALF-OPEN                   │
             │       (Probe Traffic / Trial Execution)      │
             └──────────────────────────────────────────────┘
```

### Circuit Breaker Action Budgets (per Trace)
- `max_tool_calls_per_trace`: Default `50` calls. Prevents infinite looping agents.
- `max_high_risk_actions_per_trace`: Default `5` high-risk operations (e.g. database updates).
- `max_external_calls_per_trace`: Default `10` external API dispatches.
- `max_cost_per_trace_usd`: Default `$0.50` maximum budget per single trace sequence.

When a budget limit is exceeded during a trace, `record_and_check()` immediately trips the breaker, returning `is_allowed = False` with `reason_code = "CIRCUIT_BREAKER_TOTAL_TOOL_LIMIT_EXCEEDED"`.

---

## 4. Statistical Anomaly Detection Engines

Vantage incorporates 5 specialized statistical anomaly detectors (`vantage/anomaly/`) that scan aggregated telemetry hourly or in real-time streams to detect performance degradation, cost anomalies, and security threats.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                            STATISTICAL ANOMALY DETECTORS                                 │
├───────────────────────┬───────────────────────────────────┬──────────────────────────────┤
│ Detector Name         │ Algorithm / Formula               │ Use Case                     │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 1. Z-Score Anomaly    │ Z = (x - μ) / σ                   │ Latency spikes & token cost  │
│    Detector           │ Triggers if Z > warn_z (2.0)      │ anomalies relative to 7-day  │
│                       │ or Z > crit_z (3.0)               │ baseline.                    │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 2. Threshold Exceeded │ Hard Cap Comparison               │ Enforcing hard cost caps     │
│    Detector           │ Triggers if value > threshold     │ (e.g. max $5.00/hour).       │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 3. Rate of Change     │ Delta = (v_now - v_prev) / v_prev │ Detecting sudden 200% spikes │
│    Detector           │ Triggers if Delta > factor (1.5)  │ in tool execution volume.    │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 4. Error Rate %       │ ErrPct = (n_err / n_total) * 100  │ Catching cascading downstream│
│    Detector           │ Triggers if ErrPct > limit (5%)   │ API connection failures.     │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 5. Volume Spike       │ VolRatio = v_current / μ_historical│ Spotting DDoS or botnet-driven│
│    Detector           │ Triggers if VolRatio > limit (3.0)│ prompt injection spams.      │
└───────────────────────┴───────────────────────────────────┴──────────────────────────────┘
```

### Anomaly Suppression Workflow
To eliminate alert fatigue, `AlertSuppressionRuleModel` allows administrators to suppress recurring alerts based on `incident_key` or `pattern_text` for a configurable expiration window. Suppressed alerts are logged in `alert_records` with `severity = "info"` and `notified = false`.
