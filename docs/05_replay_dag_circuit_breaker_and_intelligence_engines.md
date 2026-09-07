# Vantage Replay Engine, DAG Visualizer, Circuit Breaker, & Intelligence Engines

Welcome to **Document 05**! This document explains Vantage's **Replay Engine**, **DAG Visualizer**, **Circuit Breaker**, and **Statistical Anomaly Intelligence Engines**.

---

## ❓ What is Document 05 in Simple Language?

Document 05 solves 3 major operational challenges when running AI agents in production:

1. **How do you debug an AI bug offline?**
   > 💡 **Simple Analogy (Flight Simulator)**: In video games or pilot training, you record a flight trajectory. If something goes wrong, you don't crash a real plane to figure out why—you load the flight data into a **flight simulator**. You can change the pilot controls (prompts) while simulating the instruments (tool stubs) safely. 
   > Vantage's **Replay Engine** records trace data and mocks external APIs so developers can test prompt changes offline with **zero real-world side effects** (no real API calls, no real database changes).

2. **How do you see what an AI agent is thinking?**
   > Vantage's **SVG DAG Visualizer** draws an interactive tree showing every prompt, LLM call, and tool execution in step-by-step sequence.

3. **How do you stop an AI agent from burning $1,000 in an infinite loop?**
   > 💡 **Simple Analogy (Electrical Circuit Breaker)**: Just like the electrical panel in your home trips `OPEN` if a toaster draws too much current, Vantage's **TraceActionCircuitBreaker** trips `OPEN` if an AI agent makes too many tool calls or burns too many tokens.

---

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

Vantage incorporates **5 specialized statistical anomaly detectors** (`vantage/anomaly/`) that scan aggregated telemetry hourly or in real-time streams to detect performance degradation, cost anomalies, and security threats.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                            STATISTICAL ANOMALY DETECTORS                                 │
├───────────────────────┬───────────────────────────────────┬──────────────────────────────┤
│ Detector Name         │ Algorithm / Formula               │ Use Case (Plain English)     │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 1. Z-Score Anomaly    │ Z = (x - μ) / σ                   │ Detects unusual latency or   │
│    Detector           │ Triggers if Z > warn_z (2.0)      │ cost spikes compared to a    │
│                       │ or Z > crit_z (3.0)               │ 7-day average baseline.      │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 2. Threshold Exceeded │ Hard Cap Comparison               │ Enforces hard max dollar caps│
│    Detector           │ Triggers if value > threshold     │ (e.g. max $5.00/hour).       │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 3. Rate of Change     │ Delta = (v_now - v_prev) / v_prev │ Catches sudden 200% leaps in │
│    Detector           │ Triggers if Delta > factor (1.5)  │ tool call volume in 5 mins.  │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 4. Error Rate %       │ ErrPct = (n_err / n_total) * 100  │ Catches cascading downstream │
│    Detector           │ Triggers if ErrPct > limit (5%)   │ API connection failures.     │
├───────────────────────┼───────────────────────────────────┼──────────────────────────────┤
│ 5. Volume Spike       │ VolRatio = v_current / μ_historical│ Spots botnet traffic spikes  │
│    Detector           │ Triggers if VolRatio > limit (3.0)│ or DDoS prompt injection spam.│
└───────────────────────┴───────────────────────────────────┴──────────────────────────────┘
```

### Anomaly Suppression Workflow
To eliminate alert fatigue, `AlertSuppressionRuleModel` allows administrators to suppress recurring alerts based on `incident_key` or `pattern_text` for a configurable expiration window. Suppressed alerts are logged in `alert_records` with `severity = "info"` and `notified = false`.

