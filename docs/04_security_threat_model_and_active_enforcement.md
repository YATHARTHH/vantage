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

## 3. In-Flight PII & Secret Redaction Engine (`PIIMasker`)

### 💡 Why We Use It
When users interact with an AI agent (e.g. asking a customer support bot for help), their text prompts often contain sensitive personal information: credit card numbers, Social Security Numbers (SSNs), passwords, email addresses, or API keys.
If Vantage stored raw prompt data in telemetry databases without redacting it, companies would violate data privacy regulations like **GDPR**, **HIPAA**, and **PCI-DSS**.

### ⚙️ How It Works & Implementation (`vantage/security/pii_masker.py`)
`PIIMasker` acts like an **automatic black marker** sitting inside the ingestion conveyor belt:

1. **Before Saving to Storage**: Every span string (prompt text, tool argument, completion output) is sent through `pii_masker.mask(...)` *before* hitting DuckDB or SQLite.
2. **Regex Pattern Scanners**: Matches standard formats for SSNs (`000-00-0000`), API keys (`sk-...`, `ghp_...`), Bearer tokens (`Bearer eyJ...`), and email addresses.
3. **Luhn Checksum Verification (Credit Cards)**:
   - Random 16-digit IDs (like an order number `1000-2000-3000-4000`) look like credit cards.
   - To avoid falsely redacting order numbers, `PIIMasker` runs the **Luhn Algorithm** (a mathematical checksum used by Visa/Mastercard).
   - If the Luhn check passes, it's a real credit card and gets replaced with `[REDACTED_CREDIT_CARD]`. If it fails, the order number is left intact!

```python
# Example Input:
"Please refund card 4532-0151-1234-5678, SSN 000-12-3456"

# Scrubbed Output saved to Database:
"Please refund card [REDACTED_CREDIT_CARD], SSN [REDACTED_SSN]"
```

---

## 4. Threat Detection Engines

### 💡 Why We Use It
AI models do not distinguish between instructions written by developers vs. instructions typed by malicious users. A hacker can trick an AI agent into doing bad things (like deleting data or emailing private customer lists to an external site).

### ⚙️ How It Works & Implementation

#### 1. `JailbreakDetector` (`vantage/security/jailbreak_detector.py`)
Scans user prompts and RAG context to detect prompt injection attacks:
* **Obfuscation Removal**: First, `TextNormalizer` and `PayloadDecoder` decode base64 strings or hex tricks that hackers use to hide malicious text.
* **Pattern Scanner**: Checks for jailbreak signatures like `"ignore previous instructions"`, `"DAN mode"`, `"disregard safety guidelines"`, or `"system override"`.
* **Action**: If a jailbreak attempt is detected, `JailbreakDetector` flags the prompt, raising a high threat signal to the policy gate.

#### 2. Data Exfiltration & Destination Trust Guard (`vantage/security/output_inspector.py`)
Prevents sensitive company data from being sent to untrusted external URLs:
* **Sensitivity Classification**: Ranks data into 5 tiers: `PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `SENSITIVE` < `RESTRICTED`.
* **Destination Trust Rating**: Categorizes destination URLs into 4 levels: `TRUSTED_INTERNAL`, `APPROVED_EXTERNAL`, `UNKNOWN_EXTERNAL`, or `BLOCKED`.
* **Enforcement Rule**: If an agent tries to send `RESTRICTED` or `SENSITIVE` data to an `UNKNOWN_EXTERNAL` or `BLOCKED` URL, execution is **BLOCKED** immediately (`reason_code = "DATA_EXFILTRATION_PREVENTED"`).

---

## 5. Human-in-the-Loop & Audit Governance

### 💡 Why We Use It
High-risk AI actions (like sending a \$10,000 wire transfer or running a raw SQL `DELETE` query) should never happen automatically. They require a human manager's explicit approval.
However, two major security threats exist here:
1. **TOCTOU Attack (Time-Of-Check-To-Time-Of-Use)**: A manager approves paying \$100. But right before execution, the AI swaps the argument to \$10,000.
2. **Audit Tampering**: A hacker compromises the database and deletes audit logs showing their malicious actions.

### ⚙️ How It Works & Implementation

#### 1. Single-Use TOCTOU Action Fingerprinting (`vantage/security/approval_workflow.py`)
To prevent argument tampering:
* **SHA-256 Fingerprint**: When a human approval is requested, Vantage creates a cryptographic fingerprint of the *exact* request parameters:
  `approval_fingerprint = SHA256({tool, action, resource, environment, arguments})`
* **Single-Use Consumption**: When `ExecutionController` runs the approved tool, it verifies the hash matches the approved request AND atomically marks `consumed_at = timestamp`. If the approval is used again or arguments are changed, execution is blocked (`APPROVAL_ALREADY_CONSUMED`).

#### 2. Cryptographic Hash-Chained Audit Trail (`vantage/storage/sqlalchemy/models.py`)
Every administrative action (policy change, approval, security block) is logged using a **SHA-256 cryptographic chain**:
`record_hash[i] = SHA256(actor + action + details + record_hash[i-1])`

> 💡 **Simple Analogy**: Think of it like a chain of physical locks where key $N$ depends on lock $N-1$. If an attacker alters row #5 in SQLite, lock #5 breaks, causing locks #6, #7, #8, and every future lock to fail validation. Calling `GET /api/v1/audit/logs` instantly flags `chain_valid = false`.

