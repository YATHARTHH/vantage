# Vantage: Project Vision, Use Cases, & Requirements (Simple Guide)

Welcome to **Vantage**! This document explains what Vantage is, why traditional monitoring tools fail when AI is introduced, how Vantage protects AI applications, and the real-world problems Vantage solves.

---

## 1. What is APM and Why Does AI Break It?

### What is APM?
**APM** stands for **Application Performance Monitoring**. 

Think of APM as a health dashboard or speedometer for standard software applications (like a web store, mobile app, or banking site). Popular APM tools include **Datadog**, **New Relic**, **Dynatrace**, and **AppDynamics**.

Standard APM tools track basic metrics like:
- How fast a web page loads (Latency).
- How much CPU and memory your servers are using.
- Database query speeds.
- Server error codes (like `404 Not Found` or `500 Internal Server Error`).

---

### How Traditional Apps Work vs. How AI Agents Work

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             TRADITIONAL SOFTWARE VS. AI AGENTS                           │
├───────────────────────────────────────┬──────────────────────────────────────────────────┤
│ Traditional Software Apps             │ AI Agent Applications                            │
├───────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Fixed, predictable code written by    │ Non-deterministic (AI decides on the fly what to │
│ human programmers.                    │ do, step-by-step).                               │
├───────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Simple HTTP status codes & database   │ Complex text prompts, completion outputs, and    │
│ queries.                              │ dynamic tool invocations.                        │
├───────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Predictable memory and server costs.  │ Unbounded token usage and dynamic looping loops  │
│                                       │ that can cost real money per minute.             │
├───────────────────────────────────────┼──────────────────────────────────────────────────┤
│ Passive monitoring: Logs errors AFTER │ Active enforcement needed: Must BLOCK dangerous   │
│ damage is already done.               │ AI actions BEFORE they happen.                   │
└───────────────────────────────────────┴──────────────────────────────────────────────────┘
```

---

### Why Legacy APM Tools Fail for AI Agents

1. **They Cannot Understand AI Workflows**: Standard APM tools only see raw network connections. They cannot see LLM prompts, token consumption, AI tool choices, or step-by-step agent reasoning loops.
2. **They Only Watch, They Never Stop**: Traditional APM tools log events *after* they happen. If a malicious user tricks an AI agent into deleting a customer database, traditional APM tools merely record a log saying "Database was deleted at 2:00 PM." They cannot stop the action before it occurs.
3. **They Cannot Redact Sensitive AI Secrets in Real-Time**: AI prompts often contain sensitive user text, credit card numbers, or passwords. Traditional APM tools store raw text or require complex manual setup.
4. **They Cannot Replay Failed Runs**: Because LLMs produce probabilistic text, reproducing a bug offline is difficult. Standard APM tools offer no way to record and mock tool outputs to test prompt changes safely offline.

---

## 2. The Vantage Solution: Real-Time AI Observability + Active Security

**Vantage** is a unified platform that combines **Real-Time AI Telemetry Monitoring** with **Active Security Enforcement**.

```text
                       AI AGENT EXECUTION PATH
                                  │
                                  ▼
                     ┌───────────────────────────┐
                     │   SecurityContext (v1.2)  │
                     └────────────┬──────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   Trust Provenance       Output Inspector &     Multi-Signal Threat
 (System vs. User Text)   Schema Validation       Detection Scanner
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
          │              (Single-Use + Hash Check)        │
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

### The Simple Rule Behind Vantage
> **"Detection provides evidence. Policy makes the decision. Authorization determines capability. Enforcement controls the side effect. Audit records why."**

### How Vantage Works in 5 Easy Steps:
1. **OpenTelemetry (OTLP) Ingestion**: Collects standard AI traces from any framework (LangChain, LlamaIndex, OpenAI, Anthropic).
2. **In-Flight PII Redaction**: Automatically hides credit cards (validated using mathematical Luhn checksums), Social Security Numbers, API keys, and email addresses *before* telemetry is saved.
3. **Dual-Database Engine**: Uses **DuckDB** for lighting-fast analytical queries over millions of spans, and **SQLite** for managing API keys, security rules, and audit logs.
4. **Mandatory Security Choke-Point (`ExecutionController`)**: Intercepts every single tool request made by an AI agent. Evaluates permissions, data sensitivity, and human approval rules.
5. **Deterministic Trace Replay**: Allows developers to record an agent run, mock tool responses, and re-run modified prompts offline with zero risk of real-world side effects.

---

## 3. Real-World Industry Use Cases (Simple Stories)

### Scenario A: The Autonomous Financial Analyst Bot
- **The Story**: A hedge fund uses an AI bot to read company financial reports, calculate metrics, and post summaries to Slack.
- **The Risk**: A malicious user hides a prompt injection inside a PDF report, asking the bot to read confidential financial figures and send them to an external hacker website.
- **How Vantage Protects It**:
  - Classifies internal financial metrics as `CONFIDENTIAL` or `RESTRICTED`.
  - Automatically **BLOCKS** the request if the bot tries to send restricted financial figures to an unknown external web domain.
  - Limits execution steps so the bot cannot get stuck in an infinite calculation loop.

---

### Scenario B: The Customer Support Bot
- **The Story**: A telecom company uses an AI bot to handle customer billing tickets and issue refund vouchers.
- **The Risk**: A customer tricks the bot into issuing a $10,000 cash refund or leaks another customer's credit card number.
- **How Vantage Protects It**:
  - Automatically scrubs credit card numbers and SSNs before saving telemetry logs.
  - Requires explicit **Human Approval (`REQUIRE_APPROVAL`)** whenever the bot tries to issue a refund over $100.
  - Ensures the human approval is **single-use** so it cannot be reused for another unauthorized transaction.

---

### Scenario C: The Medical Record Processing Bot
- **The Story**: A hospital system uses an AI bot to extract doctor notes and submit health insurance claims.
- **The Risk**: The bot exposes sensitive patient health data or gets tricked by malicious links into connecting to fake web servers.
- **How Vantage Protects It**:
  - Enforces strict PII/PHI masking across all prompts and AI outputs.
  - Performs DNS firewall checks right before socket connection to prevent web redirection attacks.
  - Keeps a tamper-evident, cryptographically chained audit log for HIPAA compliance.

---

### Scenario D: The E-Commerce Purchasing Bot
- **The Story**: An e-commerce store uses an AI bot to monitor warehouse stock and automatically order inventory from suppliers.
- **The Risk**: A bug causes the bot to place 500 duplicate orders for $50,000 worth of stock in 10 minutes.
- **How Vantage Protects It**:
  - Sets strict permission limits (`inventory.read:warehouse_a:production` $\rightarrow$ `ALLOW`; `inventory.delete:*:production` $\rightarrow$ `BLOCK`).
  - Enforces rate and concurrency limits to cap automated purchases.
  - Provides deterministic trace replays so engineers can see exactly why the bot made a specific purchasing choice.

---

## 4. How Vantage Compares to Other Tools

| Feature | Legacy APM (Datadog) | AI Tracing (LangSmith) | Static Guardrails (NeMo) | Vantage Active Security Engine |
| :--- | :--- | :--- | :--- | :--- |
| **OpenTelemetry Standard** | Standard Web Spans | Proprietary / Partial | None | **Native OTLP/REST & OpenTelemetry** |
| **In-Flight PII Redaction** | Server-side / Post-ingest | Partial | Text filtering only | **In-flight Luhn & Regex scrubbing** |
| **Inline Action Blocking** | None (Log only) | None (Observe only) | Text filtering only | **ExecutionController mandatory choke-point** |
| **Capability Scope (RBAC)** | UI roles only | User access | None | **Principal $\rightarrow$ Agent $\rightarrow$ Action+Resource+Env** |
| **Single-Use Approvals** | None | Basic UI check | None | **Atomic consume & single-use tokens** |
| **Data Exfiltration Block** | None | None | Simple keyword block | **Data Sensitivity + Destination Trust Matrix** |
| **Deterministic Replay** | None | Re-run prompt only | None | **Full State & Mock Tool Replay Engine** |
| **Tamper-Evident Audits** | Standard logs | Standard logs | Text logs | **Cryptographic SHA-256 Hash Chain** |

---

## 5. System Requirements & Scope

### What Vantage Does (Functional Scope):
1. **OTLP Telemetry Ingestion**: Accepts standard OTLP JSON traces at `/api/v1/otlp/v1/traces`, parses spans, and stores them in DuckDB.
2. **In-Flight PII Masking**: Automatically scrubs credit cards (Luhn valid), SSNs, API keys, and emails before buffering.
3. **Active Tool Security Enforcement**: Intercepts all AI tool calls via `ExecutionController.execute()`. Applies rules (`BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`).
4. **Human Approval Workflow**: Handles single-use approval tokens with TOCTOU action fingerprinting.
5. **Deterministic Replay**: Reconstructs recorded traces, mocks tool outputs, and runs offline What-If evaluation sessions.
6. **Anomaly Detection & Circuit Breaking**: Tracks trace budgets (`max_tool_calls_per_trace`) and statistical anomaly metrics.

### Performance & Security Targets (Non-Functional Scope):
- **Ingestion Latency**: Fast response time (p95 <= 15 ms).
- **Security Latency**: Policy check overhead <= 2 ms per tool call.
- **Buffer Reliability**: In-memory ring buffer (`capacity=10000`) with automatic Dead-Letter Queue (`.dlq_spans.jsonl`) overflow logging.
- **Fail-Closed Security**: If a security scanner crashes, Vantage defaults to `BLOCK` to keep downstream tools safe. Telemetry ingestion, meanwhile, degrades safely without crashing the platform.

---

## 6. Real Technical Problems & How Vantage Solved Them

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                      KEY TECHNICAL PROBLEMS & HOW VANTAGE SOLVED THEM                     │
├──────────────────────────┬─────────────────────────────────┬─────────────────────────────┤
│ Problem Encountered      │ Root Cause                      │ How Vantage Solved It       │
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 1. Parameter Tampering   │ AI agent got approval in        │ Created SHA-256 canonical   │
│    (TOCTOU Attacks)      │ staging, then changed args to   │ JSON action fingerprinting  │
│                          │ production before running.      │ over Action+Resource+Env+Args│
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 2. Approval Replay       │ Approvals were simple true/false│ Built atomic single-use     │
│    Race Condition        │ flags, allowing re-use of one   │ consumption (`consumed_at`) │
│                          │ approval multiple times.        │ and stale policy checks.    │
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 3. Database Bottlenecks  │ Heavy DB writes locked web      │ Built a bounded ring buffer │
│    Under Traffic Spikes  │ worker threads during high      │ with async background batch │
│                          │ 10,000 req/sec telemetry load.  │ flushes & Dead-Letter Queue.│
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 4. Single-Score Security │ Security relied on a single     │ Designed Multi-Signal Policy│
│    Flaws                 │ threat score that prompt        │ Engine with hard precedence:│
│                          │ injections could bypass.        │ BLOCK > APPROVAL > WARN.    │
├──────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ 5. Scanner Outage Crashes│ Security scanner errors allowed │ Built fail-closed choke     │
│    Bypassing Gate        │ requests to fall through.       │ point returning BLOCK with  │
│                          │                                 │ `SECURITY_ENGINE_FAILURE`.  │
└──────────────────────────┴─────────────────────────────────┴─────────────────────────────┘
```

1. **Problem 1: Argument Tampering (TOCTOU Attacks)**
   - *The Problem*: An AI agent requested human approval for `database.write:orders:staging`. After approval was granted, the agent changed the target environment to `production` while keeping the same approval ID.
   - *Vantage Solution*: Created `compute_action_fingerprint()` which hashes the complete action context (`tool`, `action`, `resource`, `environment`, `arguments`) into a SHA-256 fingerprint using sorted JSON keys. If any parameter changes at execution time, `ExecutionController` blocks execution with `reason_code = "APPROVAL_FINGERPRINT_MISMATCH"`.

2. **Problem 2: Approval Replay & Double Spending**
   - *The Problem*: Approvals were simple boolean flags (`is_approved = true`), allowing concurrent worker requests to reuse one approval multiple times.
   - *Vantage Solution*: Built atomic single-use approval consumption in `HumanApprovalWorkflow.consume_approval()`. It verifies `consumed_at is None`, atomically sets `consumed_at = time.time()`, and verifies `approved_policy_version == current_policy_version`.

3. **Problem 3: Database Writes Blocking Ingestion Traffic**
   - *The Problem*: Under heavy telemetry traffic, synchronous database writes locked web worker threads, dropping incoming requests.
   - *Vantage Solution*: Implemented `BoundedIngestBuffer` with `deque(maxlen=10000)` and background async batch workers flushing every 500ms or 100 items. Spans exceeding capacity write safely to `.dlq_spans.jsonl`.

4. **Problem 4: Single Threat Score Vulnerabilities**
   - *The Problem*: Relying on a single AI threat score (e.g. 0.72) allowed prompt injections wrapped in unicode or base64 text to bypass checks.
   - *Vantage Solution*: Built `MultiSignalPolicyGate`. It combines threat scores, identity capabilities, data sensitivity, and destination trust into deterministic rules with strict decision precedence (`BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`).

5. **Problem 5: Scanner Backend Outages**
   - *The Problem*: If an external threat scanner backend crashed, uncaught exceptions allowed tool execution to proceed unmonitored.
   - *Vantage Solution*: Wrapped policy evaluation in `ExecutionController.execute()` in a fail-closed try-except block. Any scanner exception returns an immediate `status = "BLOCKED"` with `reason_code = "SECURITY_ENGINE_FAILURE"`. Telemetry ingestion, meanwhile, degrades safely without taking down the platform.
