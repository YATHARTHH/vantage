# Vantage Security Threat Model & Active Enforcement Architecture

## 1. OWASP Top 10 for LLM Applications (2025) Mapping

Vantage provides active security enforcement specifically tailored to the OWASP 2025 Top 10 LLM Application Vulnerabilities.

| OWASP 2025 Category | Threat Description | Vantage Active Defense Mechanism | Implementation Status |
| :--- | :--- | :--- | :--- |
| **LLM01:2025 Prompt Injection** | Direct user prompts or indirect RAG inputs hijack model instructions. | `JailbreakDetector` + Multi-Signal Policy Engine + `SecurityContext` trust boundaries. | **Currently Enforced** |
| **LLM02:2025 Sensitive Information Disclosure** | Unintentional leakage of PII, credit cards, or internal API keys. | `PIIMasker` in-flight redaction with Luhn validation + Data Classification Engine (`RESTRICTED`). | **Currently Enforced** |
| **LLM05:2025 Improper Output Handling** | Unsanitized model output executed by downstream tools or rendered in UI. | `OutputInspector` + Parameterized Query Enforcement + Path Traversal Stripping (`../`). | **Currently Enforced** |
| **LLM06:2025 Excessive Agency** | AI agents invoke unauthorized tools, write to production DBs, or bypass business logic. | Deny-by-Default Capability Matrix (`Action+Resource+Env`) + `ExecutionController` choke point. | **Currently Enforced** |
| **LLM10:2025 Unbounded Consumption** | Infinite agent loops, excessive token usage, or DoS attacks on external APIs. | Multi-dimensional Rate/Concurrency Limiter + `TraceActionCircuitBreaker` action budgets. | **Currently Enforced** |
| **LLM03:2025 Supply Chain** | Compromised third-party packages, datasets, or external model endpoints. | Package provenance hashing & HMAC webhook dispatch signatures. | Planned |
| **LLM04:2025 Data & Model Poisoning** | Malicious fine-tuning data or poisoned RAG vector embeddings. | Dataset fingerprinting & distance metric thresholding. | Planned |
| **LLM07:2025 System Prompt Leakage** | Extraction of confidential developer system prompts. | Prompt fingerprinting & output leakage regular expression scanners. | Planned |
| **LLM08:2025 Vector & Embedding Risks** | Unauthorized access or injection into RAG vector databases. | Project-isolated namespace query scoping. | Planned |
| **LLM09:2025 Misinformation** | Hallucinations resulting in incorrect business decisions or output. | Groundedness evaluators & offline trace replay validation. | Planned |

---

## 2. Mandatory Execution Controller Choke-Point

The `ExecutionController` (`vantage/security/execution_controller.py`) is the sole execution choke-point in Vantage. **No tool invocation anywhere in Vantage occurs outside `ExecutionController.execute(...)`.**

```text
                        UNTRUSTED AGENT / LLM OUTPUT
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ SecurityContext (v1.2)  │
                        └────────────┬────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  Trust Provenance           Output Inspector &          Multi-Signal Threat
(TRUSTED / UNTRUSTED)        Schema Validation           Detector Scanner
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │     Tool Authorizer     │
                        │(Action + Resource + Env)│
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ Data & Destination Guard│
                        │(Classification & Trust) │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ Multi-Signal Policy Gate│
                        │ (BLOCK > APPROVAL > WARN)│
                        └────────────┬────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
      ALLOW                   REQUIRE_APPROVAL                  BLOCK
        │                            │                            │
        │                  Human Approval Workflow                │
        │                  (Single-Use + Hash)                    │
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │  Execution Controller   │
                        │  (Sole Tool Choke Point)│
                        └────────────┬────────────┘
                                     │
                                     ▼
                                TARGET TOOL
                                     │
                                     ▼
                          Hash-Chained Audit Log
```

### Execution Lifecycle Steps
1. **Identity & Capability Verification**: `ToolAuthorizer.is_authorized(ctx)` verifies if `(principal_id, agent_id)` possesses explicit permission for `action:resource:environment`. Unauthorized attempts immediately yield `decision = "BLOCK"` with `reason_code = "TOOL_CAPABILITY_DENIED"`.
2. **Argument & Data Exfiltration Inspection**: `OutputInspector.inspect_and_sanitize()` classifies payload sensitivity (`PUBLIC` to `RESTRICTED`) and destination trust (`TRUSTED_INTERNAL` to `BLOCKED`). If `RESTRICTED` data is routed to `UNKNOWN_EXTERNAL`, execution is blocked with `reason_code = "DATA_EXFILTRATION_PREVENTED"`.
3. **Deterministic Policy Gate Evaluation**: `MultiSignalPolicyGate.evaluate()` combines all signals using strict precedence rules (`BLOCK > REQUIRE_APPROVAL > WARN > ALLOW`).
4. **TOCTOU Human Approval Verification**: If the decision is `REQUIRE_APPROVAL`, execution pauses until a single-use approval token is verified and atomically consumed (`consumed_at = time.time()`).
5. **Tool Execution & Audit Logging**: Upon successful validation, the tool function is executed, and an immutable audit log record is created linking `request_id -> trace_id -> span_id -> decision_id -> approval_id -> audit_event_id`.

---

## 3. In-Flight PII & Secret Redaction Engine

The `PIIMasker` (`vantage/security/pii_masker.py`) inspects and scrubs incoming telemetry streams prior to memory buffering or DuckDB storage.

```python
# In-Flight Scrubbing Example
raw_input = "User requested refund for card 4532-0151-1234-5678, SSN 000-12-3456"
scrubbed_input = pii_masker.mask(raw_input)
# Result: "User requested refund for card [REDACTED_CREDIT_CARD], SSN [REDACTED_SSN]"
```

### Supported Masking Rule Specifications
- **Credit Card Numbers**: Matches 13 to 19 digit sequences and verifies valid Luhn algorithm checksum before redaction, eliminating false positives from random 16-digit IDs.
- **Social Security Numbers (SSN)**: Scans for 9-digit US SSN patterns (`XXX-XX-XXXX`).
- **Secret Keys & Bearer Tokens**: Detects OpenAI keys (`sk-...`), Vantage live keys (`vg_live_...`), GitHub tokens (`ghp_...`), and HTTP Auth headers (`Bearer eyJ...`).
- **Email Addresses**: Detects standard email formats (`user@domain.com`).
- **Telemetry Metadata Preservation**: The raw secret is never stored. Non-sensitive tags (`pii_scrubbed=true`, `pii_types=["credit_card", "ssn"]`) are attached to span attributes for auditing.

---

## 4. Threat Detection Engines

### 1. `JailbreakDetector` (`vantage/security/jailbreak_detector.py`)
Analyzes raw prompt text and RAG context using multi-pattern regex matching, unicode normalization (`TextNormalizer`), and base64/hex payload decoding (`PayloadDecoder`).
- **Instruction Overrides**: Detects phrases like `"ignore previous instructions"`, `"system override"`, or `"disregard safety guidelines"`.
- **Roleplay Bypasses**: Detects DAN (Do Anything Now) prompts, developer mode exploits, and persona impersonation.
- **Encoded Payload Decoders**: Automatically decodes base64 strings and hex encodings to inspect hidden malicious payloads before evaluation.

### 2. Data Exfiltration & Destination Trust Engine (`vantage/security/output_inspector.py`)
Classifies payload sensitivity into 5 formal tiers and destinations into 4 trust levels:

```text
Data Sensitivity Tiers:
  PUBLIC < INTERNAL < CONFIDENTIAL < SENSITIVE < RESTRICTED

Destination Trust Categories:
  TRUSTED_INTERNAL: Internal services (e.g. localhost, api.company.com)
  APPROVED_EXTERNAL: Project-allowlisted third-party APIs (e.g. analytics.company.com)
  UNKNOWN_EXTERNAL: Unrecognized external domain endpoints
  BLOCKED: Known malicious or explicitly blacklisted hostnames

Policy Enforcement Rule:
  (SENSITIVE or RESTRICTED payload) + (UNKNOWN_EXTERNAL or BLOCKED destination) ==> BLOCK
```

---

## 5. Human-in-the-Loop & Audit Governance

### TOCTOU Action Fingerprinting & Single-Use Approvals
To prevent Time-Of-Check-To-Time-Of-Use (TOCTOU) argument tampering and approval replay attacks, `HumanApprovalWorkflow` generates a SHA-256 fingerprint:

$$\text{approval\_fingerprint} = \text{SHA256}(\text{canonical\_json}(\{\text{tool}, \text{action}, \text{resource}, \text{environment}, \text{arguments}\}, \text{sort\_keys}=\text{True}))$$

- **Single-Use Semantics**: When `ExecutionController` processes an approved request, `consume_approval()` checks `consumed_at is None` and atomically sets `consumed_at = time.time()`. Subsequent attempts using the same approval ID are blocked (`APPROVAL_ALREADY_CONSUMED`).
- **Stale Policy Protection**: Verifies `approved_policy_version == current_policy_version`. If an admin updates the security policy from `v1.2.0` to `v1.3.0` while an approval is pending, execution returns `BLOCK` with `reason_code = "APPROVAL_POLICY_STALE"`.

### Role-Based Access Control (RBAC)
Vantage enforces 3 strict role permission levels:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                  ROLE CAPABILITY MATRIX                                  │
├───────────────────┬──────────────────────────────────────────────────────────────────────┤
│ Role              │ Granted System Capabilities                                          │
├───────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Viewer            │ Read metrics, view execution DAG traces, inspect project metadata.   │
├───────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Developer         │ Ingest telemetry, run offline replays, evaluate What-If forks.       │
├───────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Admin             │ Full access: Create/revoke API keys, modify policies, inspect audit. │
└───────────────────┴──────────────────────────────────────────────────────────────────────┘
```

### Cryptographic Tamper-Evident Audit Logging
All administrative security actions (API key creation, policy changes, human approvals, security blocks) write an entry to `audit_logs` using a cryptographic SHA-256 hash chain:

$$\text{record\_hash}_i = \text{SHA256}(\text{actor\_key\_id} + \text{action} + \text{resource\_type} + \text{details\_json} + \text{record\_hash}_{i-1})$$

If an attacker modifies or deletes a historical audit entry in the database, verifying the hash chain via `GET /api/v1/audit/logs` immediately flags `chain_valid = false` and highlights the exact index where tampering occurred.
