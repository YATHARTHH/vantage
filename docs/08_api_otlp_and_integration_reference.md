# Vantage REST API, OTLP Specification, & Integration Reference

Welcome to **Document 08**! This document is your complete guide to using the Vantage API. It covers:
- **What is OTLP and why we use it** (plain English)
- **How to authenticate** (getting and using API keys)
- **Every API endpoint** with sample request and response examples
- **Error codes** and what they mean
- **Python SDK examples** (not just curl)
- **How to integrate** your existing AI application with Vantage in under 10 minutes

---

## ❓ What is an API? What is OTLP? (Simple Explanation)

### What is an API?
An **API (Application Programming Interface)** is a way for two software systems to talk to each other. Think of it like a restaurant menu — it lists exactly what you can order (the endpoints), how to order it (the HTTP method and parameters), and what you'll receive back (the response).

The Vantage API lets your AI agents and monitoring tools:
- **Send** telemetry data (what the AI did, how many tokens it used, what tool it called)
- **Query** that data back (show me all spans from the last 24 hours)
- **Manage** security rules, API keys, and projects
- **Trigger** replays, alerts, and webhook notifications

### What is OTLP?
**OTLP (OpenTelemetry Protocol)** is a universal standard format for sending telemetry data (traces, logs, metrics) between systems.

> 💡 **Simple Analogy**: Think of OTLP like a universal plug adapter. If you travel to different countries, your device (monitoring tool) might have a different plug shape, but a universal adapter lets it work anywhere. OTLP is that universal adapter — any AI framework (LangChain, LlamaIndex, OpenAI, Anthropic) that supports OpenTelemetry can send data to Vantage **without writing custom code**.

### Why Do We Use It?
- **No vendor lock-in**: Your agent code doesn't need to know anything about Vantage's internal storage.
- **Works with everything**: LangChain, LlamaIndex, OpenAI SDK, Anthropic SDK, and any custom Python/TypeScript agent all speak OTLP.
- **Industry standard**: Maintained by the Cloud Native Computing Foundation (CNCF), used by Google, Microsoft, Amazon.

---

## 1. How to Authenticate (Getting & Using API Keys)

### Step 1: Get Your API Key
All Vantage API endpoints (except `/health` and `/ready`) require an API key. There are two ways to get one:

**Option A: Use the default development key** (already created by `setup_project_and_seed.py`):
```
dev-local-key
```
This key has `admin` role and is only for local development.

**Option B: Create a new key via the API** (requires an existing `admin` key):
```bash
curl -X POST "http://localhost:8000/api/v1/api-keys" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "My Production Agent",
    "role": "developer",
    "project_id": "proj_alpha",
    "expires_in_days": 365
  }'
```

**Sample Response (201 Created)**:
```json
{
  "key_id": "vg_key_9f8a3b2c",
  "secret_key": "vg_sk_a1b2c3d4e5f6...",
  "display_name": "My Production Agent",
  "role": "developer",
  "project_id": "proj_alpha",
  "expires_at": "2027-09-07T00:00:00Z",
  "status": "active"
}
```
> ⚠️ **Important**: Copy the `secret_key` now — it is shown **only once** and never stored in plain text.

---

### Step 2: Use the API Key in Requests
You can authenticate using either header format — both work identically:

```
# Format 1 (Bearer Token)
Authorization: Bearer vg_sk_a1b2c3d4e5f6...

# Format 2 (API Key Header)
X-API-Key: vg_sk_a1b2c3d4e5f6...
```

---

### API Key Roles & Permissions

| Role | What It Can Do |
|:-----|:---------------|
| `viewer` | Read metrics, view trace trees, inspect metadata (read-only) |
| `developer` | All viewer permissions + ingest telemetry, run offline replays, use What-If evaluation |
| `admin` | Full access: create/revoke API keys, update security policies, inspect audit logs |

---

## 2. Comprehensive API Endpoint Reference

### All Endpoints at a Glance

| Category | Method | Path | Auth Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/health` | None | Liveness probe — is the server alive? |
| **Health** | `GET` | `/ready` | None | Readiness probe — are databases connected? |
| **Ingestion** | `POST` | `/api/v1/ingest/spans` | developer | Ingest an array of Vantage span objects |
| **Ingestion** | `POST` | `/api/v1/otlp/v1/traces` | developer | Native OTLP/REST endpoint (standard OpenTelemetry format) |
| **Projects** | `GET` | `/api/v1/projects` | developer | List all projects |
| **Projects** | `POST` | `/api/v1/projects` | admin | Create a new project boundary |
| **Projects** | `GET` | `/api/v1/projects/{id}` | developer | Retrieve a single project's metadata |
| **Query** | `GET` | `/api/v1/query/spans` | developer | Query telemetry spans with filters |
| **Analytics** | `GET` | `/api/v1/analytics/rollups` | developer | Get hourly metric rollups (tokens, cost, latency) |
| **Policy** | `GET` | `/api/v1/policy/{project_id}` | developer | Get a project's circuit breaker policy rules |
| **Policy** | `PUT` | `/api/v1/policy/{project_id}` | admin | Update a project's circuit breaker policy rules |
| **Alerts** | `GET` | `/api/v1/alerts/rules` | developer | List configured anomaly alert rules |
| **Alerts** | `POST` | `/api/v1/alerts/rules` | admin | Create or update an alert rule |
| **Alerts** | `GET` | `/api/v1/alerts/records` | developer | List active and historical alert incidents |
| **Replay** | `POST` | `/api/v1/replay/manifest` | developer | Generate a ReplayManifest for a past trace |
| **Replay** | `POST` | `/api/v1/replay/execute` | developer | Execute a deterministic offline replay session |
| **API Keys** | `GET` | `/api/v1/api-keys` | admin | List all enterprise API keys |
| **API Keys** | `POST` | `/api/v1/api-keys` | admin | Generate a new secret API key |
| **API Keys** | `DELETE` | `/api/v1/api-keys/{key_id}` | admin | Soft-revoke a secret API key |
| **Audit** | `GET` | `/api/v1/audit/logs` | admin | Fetch cryptographic hash-chained audit logs |
| **Webhooks** | `GET` | `/api/v1/webhooks` | admin | List active webhook subscriptions |
| **Webhooks** | `POST` | `/api/v1/webhooks` | admin | Register a new webhook endpoint |
| **Webhooks** | `DELETE` | `/api/v1/webhooks/{id}` | admin | Revoke a webhook subscription |

---

## 3. Error Responses — What Every Error Code Means

Every API error returns a consistent JSON body. Here is what each status code means and how to fix it:

```json
{
  "error": "TOOL_CAPABILITY_DENIED",
  "message": "Agent agent_007 does not have permission for action database.delete on resource users in environment production",
  "http_status": 403
}
```

| HTTP Code | Error Code | What Happened | How to Fix It |
|:----------|:-----------|:--------------|:--------------|
| `401 Unauthorized` | `INVALID_API_KEY` | API key is missing or invalid | Check your `Authorization` header. Use `GET /api/v1/api-keys` to list active keys. |
| `401 Unauthorized` | `API_KEY_EXPIRED` | API key has passed its `expires_at` date | Generate a new key with `POST /api/v1/api-keys`. |
| `401 Unauthorized` | `API_KEY_REVOKED` | API key was manually revoked | Use an active key. Contact your admin. |
| `403 Forbidden` | `INSUFFICIENT_ROLE` | Your key's role does not have permission for this endpoint | Example: a `viewer` key trying to create a project. Use an `admin` or `developer` key. |
| `403 Forbidden` | `TOOL_CAPABILITY_DENIED` | The agent tried to run a tool it has no capability grant for | Update capability grants in `tool_authorizer.py` or the security policy. |
| `403 Forbidden` | `DATA_EXFILTRATION_PREVENTED` | Agent tried to send `RESTRICTED` data to an `UNKNOWN_EXTERNAL` URL | Update the destination trust list or lower the data sensitivity classification. |
| `403 Forbidden` | `APPROVAL_FINGERPRINT_MISMATCH` | Tool arguments were changed after human approval was granted (TOCTOU attack) | Re-submit the request for fresh human approval without modifying arguments. |
| `403 Forbidden` | `APPROVAL_ALREADY_CONSUMED` | A single-use approval token was used more than once (replay attack) | Request a new human approval. |
| `403 Forbidden` | `APPROVAL_EXPIRED` | Human approval request expired (TTL = 300 seconds) | Request a new human approval. |
| `403 Forbidden` | `SECURITY_ENGINE_FAILURE` | A security scanner crashed (fail-closed policy) | Check server logs. Restart the Vantage server if scanners are unhealthy. |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | This API key exceeded 100 req/min for ingestion | Wait and retry with exponential backoff. Contact admin to increase limits. |
| `422 Unprocessable Entity` | `VALIDATION_ERROR` | Request body is missing required fields or has invalid data types | Check the request body against the API spec below. |
| `503 Service Unavailable` | `DATABASE_UNAVAILABLE` | DuckDB or SQLite is not connected | Check `/ready` probe. Verify disk space and database file permissions. |

---

## 4. Detailed Endpoint Examples with Sample Responses

### Endpoint 1: Health Check
```bash
# Liveness check — is the server process alive?
curl http://localhost:8000/health
```
```json
{ "status": "healthy" }
```

```bash
# Readiness check — are DuckDB and SQLite connected?
curl http://localhost:8000/ready
```
```json
{ "status": "ready", "duckdb": "connected", "sqlite": "connected" }
```
> If `/ready` returns `503`, DuckDB or SQLite is unavailable. Check disk space and file permissions.

---

### Endpoint 2: Ingest via OTLP (OpenTelemetry Native Format)

**Why use this endpoint?** If your agent uses LangChain, LlamaIndex, or any OpenTelemetry-compatible instrumentation library, use this endpoint. The data format matches the OpenTelemetry standard exactly — no custom transformation needed.

```bash
curl -X POST "http://localhost:8000/api/v1/otlp/v1/traces" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceSpans": [{
      "resource": {
        "attributes": [
          { "key": "service.name", "value": { "stringValue": "order-agent-service" } },
          { "key": "vantage.project_id", "value": { "stringValue": "proj_alpha" } }
        ]
      },
      "scopeSpans": [{
        "spans": [{
          "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
          "spanId": "00f067aa0ba902b7",
          "parentSpanId": "",
          "name": "ChatOpenAI.invoke",
          "kind": 3,
          "startTimeUnixNano": "1725436800000000000",
          "endTimeUnixNano": "1725436801200000000",
          "attributes": [
            { "key": "gen_ai.system", "value": { "stringValue": "openai" } },
            { "key": "gen_ai.request.model", "value": { "stringValue": "gpt-4o" } },
            { "key": "gen_ai.usage.input_tokens", "value": { "intValue": 450 } },
            { "key": "gen_ai.usage.output_tokens", "value": { "intValue": 150 } },
            { "key": "gen_ai.input.messages", "value": { "stringValue": "User asked to refund order #1234" } },
            { "key": "gen_ai.output.choices", "value": { "stringValue": "I will proceed with refunding order #1234" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        }]
      }]
    }]
  }'
```

**Sample Response (202 Accepted)**:
```json
{
  "status": "accepted",
  "spans_processed": 1,
  "pii_scrubbed_count": 0,
  "rejected_count": 0
}
```
> `pii_scrubbed_count` tells you how many spans had PII (credit cards, SSNs, secrets) automatically removed before storage.

---

### Endpoint 3: Query Telemetry Spans
```bash
curl -X GET "http://localhost:8000/api/v1/query/spans?project_id=proj_alpha&limit=10&kind=LLM" \
  -H "Authorization: Bearer dev-local-key"
```
**Sample Response (200 OK)**:
```json
{
  "spans": [
    {
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
      "span_id": "00f067aa0ba902b7",
      "name": "ChatOpenAI.invoke",
      "kind": "LLM",
      "model_name": "gpt-4o",
      "duration_ms": 1200.0,
      "input_tokens": 450,
      "output_tokens": 150,
      "cost_usd": 0.0045,
      "pii_scrubbed": false,
      "status_code": "OK"
    }
  ],
  "total_count": 1
}
```

---

### Endpoint 4: Get Hourly Metric Rollups (Analytics)
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/rollups?project_id=proj_alpha" \
  -H "Authorization: Bearer dev-local-key"
```
**What this returns**: Hourly aggregated summaries of token usage, cost, latency, and error rates. Use this to power dashboards or Grafana charts.

**Sample Response (200 OK)**:
```json
{
  "rollups": [
    {
      "hour": "2026-09-07T14:00:00Z",
      "project_id": "proj_alpha",
      "model_name": "gpt-4o",
      "total_spans": 142,
      "total_tokens": 85400,
      "total_cost_usd": 2.34,
      "avg_latency_ms": 870.5,
      "p95_latency_ms": 1450.0,
      "error_count": 3
    }
  ]
}
```

---

### Endpoint 5: Create a New Project
```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "proj_payments",
    "display_name": "Payments Agent",
    "project_type": "AGENT_WORKFLOW",
    "owner_team": "platform",
    "owner_email": "platform@company.com",
    "log_prompts": false
  }'
```
**Sample Response (201 Created)**:
```json
{
  "id": "proj_payments",
  "display_name": "Payments Agent",
  "project_type": "AGENT_WORKFLOW",
  "log_prompts": false,
  "active": true,
  "created_at": "2026-09-07T10:26:00Z"
}
```
> `log_prompts: false` means prompt text and completion text are **never stored** (privacy mode). Token counts and costs are still tracked.

---

### Endpoint 6: Generate & Execute a Replay
```bash
# Step 1: Generate the ReplayManifest from a historical trace
curl -X POST "http://localhost:8000/api/v1/replay/manifest" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "project_id": "proj_alpha"
  }'
```
**Sample Response (200 OK)**:
```json
{
  "manifest_id": "replay_manifest_9a3f",
  "original_trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "initial_prompt": "User asked to refund order #1234",
  "system_instruction": "You are a helpful billing assistant.",
  "model_name": "gpt-4o",
  "step_mocks": [
    { "step_id": "step_01", "tool_name": "database.read", "mocked_output": "{...order data...}" }
  ]
}
```

```bash
# Step 2: Run a What-If replay with a modified system prompt
curl -X POST "http://localhost:8000/api/v1/replay/execute" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest_id": "replay_manifest_9a3f",
    "candidate_system_prompt": "You are a strict billing assistant. Never issue refunds over $100 without manager approval."
  }'
```

---

### Endpoint 7: Fetch Audit Log & Verify Integrity
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs" \
  -H "Authorization: Bearer dev-local-key"
```
**Sample Response (200 OK)**:
```json
{
  "chain_valid": true,
  "total_entries": 24,
  "logs": [
    {
      "id": 1,
      "timestamp": "2026-09-07T08:00:00Z",
      "actor_key_id": "vg_key_admin",
      "action": "api_key.create",
      "resource_type": "api_key",
      "resource_id": "vg_key_9f8a3b2c",
      "record_hash": "a3f9b2...",
      "previous_hash": "000000..."
    }
  ]
}
```
> `chain_valid: true` means no audit log records have been tampered with. If `chain_valid: false`, the exact entry ID where tampering occurred is also returned.

---

### Endpoint 8: Register a Webhook
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Security Incident Slack Alert",
    "endpoint_url": "https://hooks.slack.com/services/T.../B.../xxx",
    "provider": "slack"
  }'
```
> Vantage will fire this webhook whenever a `CRITICAL` security alert or policy `BLOCK` event occurs. The payload is HMAC-signed with `X-Vantage-Signature` so your receiver can verify authenticity.

---

## 5. Python SDK Examples

Most AI engineers use Python. Here are complete, working Python examples using the `requests` library (or `httpx` for async).

### Install the library
```bash
pip install requests
# Or for async usage:
pip install httpx
```

### Example 1: Send a Telemetry Span from Python
```python
import requests
import time

VANTAGE_URL = "http://localhost:8000"
API_KEY = "dev-local-key"

def send_span(trace_id: str, span_id: str, model: str, input_tokens: int, output_tokens: int):
    """Send an LLM span to Vantage via OTLP format."""
    now_ns = str(int(time.time() * 1e9))
    
    payload = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "vantage.project_id", "value": {"stringValue": "proj_alpha"}}
                ]
            },
            "scopeSpans": [{
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": f"{model}.invoke",
                    "kind": 3,
                    "startTimeUnixNano": now_ns,
                    "endTimeUnixNano": str(int(time.time() * 1e9)),
                    "attributes": [
                        {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                        {"key": "gen_ai.request.model", "value": {"stringValue": model}},
                        {"key": "gen_ai.usage.input_tokens", "value": {"intValue": input_tokens}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": output_tokens}},
                    ],
                    "status": {"code": "STATUS_CODE_OK"}
                }]
            }]
        }]
    }
    
    response = requests.post(
        f"{VANTAGE_URL}/api/v1/otlp/v1/traces",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=payload
    )
    print(f"Status: {response.status_code}, Response: {response.json()}")

# Usage
send_span("abc123trace", "span001", "gpt-4o", input_tokens=320, output_tokens=85)
```

---

### Example 2: Query Spans and Calculate Total Cost
```python
import requests

def get_daily_cost(project_id: str) -> float:
    """Fetch hourly rollups and sum up the last 24 hours of cost."""
    response = requests.get(
        f"http://localhost:8000/api/v1/analytics/rollups",
        headers={"Authorization": "Bearer dev-local-key"},
        params={"project_id": project_id}
    )
    data = response.json()
    total_cost = sum(r["total_cost_usd"] for r in data.get("rollups", []))
    return total_cost

cost = get_daily_cost("proj_alpha")
print(f"Total cost last 24 hours: ${cost:.4f}")
```

---

### Example 3: Create an API Key Programmatically
```python
import requests

def create_developer_key(display_name: str, project_id: str) -> str:
    """Create a new developer API key scoped to a project."""
    response = requests.post(
        "http://localhost:8000/api/v1/api-keys",
        headers={"Authorization": "Bearer dev-local-key", "Content-Type": "application/json"},
        json={
            "display_name": display_name,
            "role": "developer",
            "project_id": project_id,
            "expires_in_days": 90
        }
    )
    data = response.json()
    secret = data["secret_key"]
    print(f"New key created: {data['key_id']} — Save this secret: {secret}")
    return secret

new_key = create_developer_key("CI/CD Pipeline Key", "proj_alpha")
```

---

### Example 4: Async Ingestion with httpx (for high-throughput agents)
```python
import asyncio
import httpx

async def send_span_async(span_data: dict):
    """Send a span asynchronously — ideal for high-throughput LangChain agents."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/otlp/v1/traces",
            headers={"Authorization": "Bearer dev-local-key"},
            json=span_data,
            timeout=5.0
        )
        return response.json()

# Run it
asyncio.run(send_span_async({...}))  # Pass your OTLP payload here
```

---

## 6. Integration Guide: Connect Your Existing AI App in 10 Minutes

If you already have a LangChain, LlamaIndex, or OpenAI Python agent, here is how to connect it to Vantage with zero code changes to your agent logic.

### Option A: Auto-Instrument with OpenTelemetry (Zero Code Change)

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

```python
# Add these 5 lines at the top of your agent's entry point
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Point OpenTelemetry exporter to Vantage
provider = TracerProvider()
exporter = OTLPSpanExporter(
    endpoint="http://localhost:8000/api/v1/otlp/v1/traces",
    headers={"Authorization": "Bearer dev-local-key"}
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# Your existing agent code runs UNCHANGED below this line
```

This is it! Your existing LangChain, LlamaIndex, or custom Python agent now automatically sends all spans to Vantage. No other changes needed.

---

### Option B: Manual Span Submission (for custom integrations)

If you want explicit control over what data is sent, call the REST API directly after each LLM call:

```python
import requests, time, uuid

def vantage_trace(func):
    """Decorator to automatically send Vantage spans for any LLM function."""
    def wrapper(*args, **kwargs):
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        start = time.time()
        
        result = func(*args, **kwargs)  # Call the actual LLM function
        
        duration_ms = (time.time() - start) * 1000
        
        # Send the span to Vantage
        requests.post(
            "http://localhost:8000/api/v1/otlp/v1/traces",
            headers={"Authorization": "Bearer dev-local-key"},
            json={"resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "vantage.project_id", "value": {"stringValue": "proj_alpha"}}
                ]},
                "scopeSpans": [{"spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": func.__name__,
                    "kind": 3,
                    "startTimeUnixNano": str(int(start * 1e9)),
                    "endTimeUnixNano": str(int(time.time() * 1e9)),
                    "status": {"code": "STATUS_CODE_OK"}
                }]}]
            }]}
        )
        return result
    return wrapper

# Apply the decorator to any LLM call
@vantage_trace
def call_llm(prompt: str) -> str:
    # Your existing LLM call here
    ...
```

---

## 7. Request Size Limits & Performance Characteristics

| Constraint | Value | Notes |
|:-----------|:------|:------|
| Max payload size | 10 MB | Gzip-compressed payloads are automatically decompressed |
| Ingestion p95 latency | ≤ 15 ms | Because heavy DB writes happen async in the background |
| Policy enforcement overhead | ≤ 2 ms | `ExecutionController` adds <2ms per tool call |
| Max spans per batch | 1,000 | Send multiple batches for larger trace payloads |
| Rate limit (ingestion) | 100 req/min per API key | Returns HTTP 429 if exceeded |
| Approval token TTL | 300 seconds | Human approvals expire after 5 minutes |
| Jailbreak scan character limit | 4,096 chars | First 4,096 characters of each prompt are scanned |
