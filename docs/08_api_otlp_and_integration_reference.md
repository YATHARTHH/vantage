# Vantage REST API, OTLP Specification, & Integration Reference

## 1. Comprehensive API Endpoint Reference Table

| Category | Method | Path | Auth Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/health` | No | Liveness status probe |
| **Health** | `GET` | `/ready` | No | Readiness status probe |
| **Ingestion** | `POST` | `/api/v1/ingest/spans` | Yes | Ingest array of Vantage telemetry spans |
| **Ingestion** | `POST` | `/api/v1/otlp/v1/traces` | Yes | OpenTelemetry OTLP/REST Protobuf/JSON endpoint |
| **Projects** | `GET` | `/api/v1/projects` | Yes | List all projects |
| **Projects** | `POST` | `/api/v1/projects` | Yes | Create a new project boundary |
| **Projects** | `GET` | `/api/v1/projects/{id}` | Yes | Retrieve single project metadata |
| **Query** | `GET` | `/api/v1/query/spans` | Yes | Query telemetry spans with filters |
| **Query** | `GET` | `/api/v1/analytics/rollups` | Yes | Get hourly metric rollups (tokens, latency) |
| **Policy** | `GET` | `/api/v1/policy/{project_id}` | Yes | Retrieve project policy circuit breaker rules |
| **Policy** | `PUT` | `/api/v1/policy/{project_id}` | Yes | Update project policy circuit breaker rules |
| **Alerts** | `GET` | `/api/v1/alerts/rules` | Yes | List configured alert rules |
| **Alerts** | `POST` | `/api/v1/alerts/rules` | Yes | Create or update alert rule |
| **Alerts** | `GET` | `/api/v1/alerts/records` | Yes | List active and historical alert incidents |
| **Replay** | `POST` | `/api/v1/replay/manifest` | Yes | Generate ReplayManifest for a trace |
| **Replay** | `POST` | `/api/v1/replay/execute` | Yes | Execute deterministic offline replay session |
| **API Keys** | `GET` | `/api/v1/api-keys` | Yes (`admin`) | List enterprise API keys |
| **API Keys** | `POST` | `/api/v1/api-keys` | Yes (`admin`) | Generate secret API key |
| **API Keys** | `DELETE` | `/api/v1/api-keys/{key_id}`| Yes (`admin`) | Soft-revoke secret API key |
| **Audit** | `GET` | `/api/v1/audit/logs` | Yes (`admin`) | Fetch cryptographic hash-chained audit logs |
| **Webhooks** | `GET` | `/api/v1/webhooks` | Yes (`admin`) | List active webhook subscriptions |
| **Webhooks** | `POST` | `/api/v1/webhooks` | Yes (`admin`) | Register new push webhook endpoint |
| **Webhooks** | `DELETE` | `/api/v1/webhooks/{id}` | Yes (`admin`) | Revoke webhook subscription |

---

## 2. OpenTelemetry (OTLP/REST) Ingestion Specification

Endpoint: `POST /api/v1/otlp/v1/traces`

### Request Headers
- `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`
- `Content-Type: application/json`
- `Content-Encoding: gzip` (Optional, automatically decompressed up to 10MB)

### Sample OTLP JSON Payload
```json
{
  "resourceSpans": [
    {
      "resource": {
        "attributes": [
          { "key": "service.name", "value": { "stringValue": "order-agent-service" } },
          { "key": "vantage.project_id", "value": { "stringValue": "proj_alpha" } }
        ]
      },
      "scopeSpans": [
        {
          "spans": [
            {
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
            }
          ]
        }
      ]
    }
  ]
}
```

### Response Payload (202 Accepted)
```json
{
  "status": "accepted",
  "spans_processed": 1,
  "pii_scrubbed_count": 0,
  "rejected_count": 0
}
```

---

## 3. Working `curl` Commands Reference

### 1. Ingest OTLP Telemetry Span
```bash
curl -X POST "http://localhost:8000/api/v1/otlp/v1/traces" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceSpans": [{
      "resource": { "attributes": [{ "key": "vantage.project_id", "value": { "stringValue": "proj_alpha" } }] },
      "scopeSpans": [{
        "spans": [{
          "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
          "spanId": "00f067aa0ba902b7",
          "name": "executor.run",
          "kind": 1,
          "startTimeUnixNano": "1725436800000000000",
          "endTimeUnixNano": "1725436800500000000",
          "attributes": [
            { "key": "gen_ai.usage.input_tokens", "value": { "intValue": 120 } },
            { "key": "gen_ai.usage.output_tokens", "value": { "intValue": 40 } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        }]
      }]
    }]
  }'
```

### 2. Query Project Telemetry Spans
```bash
curl -X GET "http://localhost:8000/api/v1/query/spans?project_id=proj_alpha&limit=10" \
  -H "Authorization: Bearer dev-local-key"
```

### 3. Generate New Secret API Key (Admin Role Required)
```bash
curl -X POST "http://localhost:8000/api/v1/api-keys" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Production Agent Worker",
    "role": "developer",
    "project_id": "proj_alpha",
    "expires_in_days": 365
  }'
```

### 4. Fetch Cryptographic Audit Log & Verify Hash Chain
```bash
curl -X GET "http://localhost:8000/api/v1/audit/logs" \
  -H "Authorization: Bearer dev-local-key"
```

### 5. Register Webhook Subscription Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks" \
  -H "Authorization: Bearer dev-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Security Incident Alert Webhook",
    "endpoint_url": "https://api.company.com/webhooks/vantage",
    "provider": "generic"
  }'
```
