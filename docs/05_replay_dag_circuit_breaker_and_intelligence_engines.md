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

### Why We Built This
Debugging non-deterministic AI agents is hard because you cannot reproduce the same bug twice — the LLM gives a different answer every time you re-run. Without the Replay Engine, a developer would have to:
1. Wait for the bug to happen again in production (risky)
2. Manually reconstruct the agent state (slow and error-prone)
3. Call real external APIs while debugging (costs money and has side effects)

The Replay Engine solves this by **recording the exact state of a past execution** and letting you re-run it offline with mocked tool responses.

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

### How to Use the Replay Engine (Code Example)

Here is how a developer actually triggers the replay in practice:

**Step 1 — Generate the ReplayManifest from a past trace** (via the API):
```python
import requests

# Generate a replay manifest from a historical trace
response = requests.post(
    "http://localhost:8000/api/v1/replay/manifest",
    headers={"Authorization": "Bearer dev-local-key"},
    json={"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "project_id": "proj_alpha"}
)
manifest = response.json()
print(f"Manifest ID: {manifest['manifest_id']}")
print(f"Original prompt: {manifest['initial_prompt']}")
print(f"Tool mocks available: {len(manifest['step_mocks'])}")
```

**Step 2 — Execute a What-If replay with a different system prompt**:
```python
# Run the replay with a candidate new system prompt
replay_response = requests.post(
    "http://localhost:8000/api/v1/replay/execute",
    headers={"Authorization": "Bearer dev-local-key"},
    json={
        "manifest_id": manifest["manifest_id"],
        "candidate_system_prompt": "You are a strict billing assistant. Require manager approval for all refunds over $50."
    }
)
result = replay_response.json()
print(f"Token change: {result['token_delta']} tokens")
print(f"Cost change: ${result['cost_delta_usd']:.4f}")
print(f"Tool call differences: {result['tool_divergence']}")
```

> 💡 **Key benefit**: All tool calls in the replay use **mocked historical responses** — no real database queries, no real API calls, no real money spent.

---

## 2. Dynamic Frontend SVG DAG Visualizer

### Why We Built This
Without the DAG Visualizer, a developer debugging a complex multi-hop agent would only see raw log lines like:
```
[10:00:01] Span abc123 - LLM call - 450ms
[10:00:01] Span def456 - Tool: database.read - 45ms  
[10:00:02] Span ghi789 - LLM call - 850ms
[10:00:02] Span jkl012 - Tool: http.post - 180ms [BLOCKED]
```

This is hard to understand. The DAG Visualizer turns this into a visual tree that clearly shows **which LLM step triggered which tool call**, the cost and timing of each node, and exactly which step was blocked by the security policy.

### How the DAG is Built (Technical Detail)
The frontend queries `/api/v1/query/spans?project_id=proj_alpha&trace_id=4bf92f...` to retrieve all spans for a trace. Each span has a `trace_id`, a `span_id`, and an optional `parent_span_id`.

The React component then:
1. Groups all spans by `trace_id`
2. Builds a tree structure using `parent_span_id` as the edge (child → parent link)
3. Computes SVG node positions in depth-first order (root at top, children below)
4. Colors each node based on cost relative to trace total (green = cheap, orange = moderate, red = expensive)
5. Attaches security policy badges (`ALLOW`, `WARN`, `REQUIRE_APPROVAL`, `BLOCK`) to nodes where `ExecutionController` intercepted the call

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

### The 3 States Explained Simply

The circuit breaker has 3 states, just like the electrical circuit breaker in your home's fuse box:

| State | What It Means | What Happens to Requests |
|:------|:--------------|:-------------------------|
| 🟢 **CLOSED** | Everything is working normally. All checks passed. | Requests are allowed through and processed normally. |
| 🔴 **OPEN** | Too many errors or too much budget consumed. Gate is shut. | ALL requests are immediately rejected without being processed. Returns HTTP 503. |
| 🟡 **HALF-OPEN** | The cooldown window (60 seconds) has expired. We're testing if the problem is fixed. | A single trial request is let through. If it succeeds, the breaker returns to CLOSED. If it fails, it goes back to OPEN. |

> 💡 **Real Example**: Imagine an AI agent loops 50 times in 10 seconds calling an external search API. Vantage's circuit breaker trips to **OPEN** after the 50th call, immediately halting all further tool calls for that trace. After 60 seconds, it moves to **HALF-OPEN** and allows one probe request to verify if the underlying issue is resolved.

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

### Anomaly Alert Delivery Pathway
When an anomaly detector fires, here is the complete path the alert travels from detection to notification:

```text
 ANOMALY DETECTOR FIRES
         │
         ▼
  ┌──────────────────────────────────────┐
  │ 1. Alert stored in `alert_records`   │
  │    table in SQLite                   │
  │    (severity, metric, current_value) │
  └──────────────────┬───────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────┐
  │ 2. Check `alert_suppression_rules`   │
  │    Is this alert suppressed?         │
  └────────────┬────────────────┬────────┘
     YES ──────┘                └──── NO
  (log as info,                        │
   no notification)                    ▼
                        ┌──────────────────────────┐
                        │ 3. WebhookNotifier fires  │
                        │    HMAC-signed payload to │
                        │    registered webhooks    │
                        └────────────┬─────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
              Slack Webhook    Teams Webhook    Custom Webhook
```

### Anomaly Suppression Workflow
To eliminate alert fatigue, `AlertSuppressionRuleModel` allows administrators to suppress recurring alerts based on `incident_key` or `pattern_text` for a configurable expiration window. Suppressed alerts are logged in `alert_records` with `severity = "info"` and `notified = false`.

