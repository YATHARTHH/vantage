# Vantage Developer Guide: Codebase Map & Testing (Simple Guide)

Welcome to **Document 06**! This document is a simple blueprint for developers, hiring managers, or interns who want to explore the Vantage codebase, run the project locally, or run the test suite.

---

## 1. What is Document 06 in Simple Language?

Document 06 answers three practical questions:
1. **Where is everything?** (A clean map of all folders and files in `vantage/`).
2. **How do I run it on my machine?** (Step-by-step terminal commands).
3. **How do we test it?** (Explaining how our 69 automated Pytest tests verify that Vantage works 100%).

---

## 2. Codebase Map: Where Core Logic Lives

Here is how the `vantage/` Python folder is organized:

```text
d:\vantage\vantage\
├── security/              # 🛡️ THE SECURITY ENGINE
│   ├── execution_controller.py  # Sole gateway that intercepts tool calls before execution.
│   ├── pii_masker.py            # Redacts credit cards & secrets in real time.
│   ├── jailbreak_detector.py    # Detects prompt injections & DAN bypass attempts.
│   ├── output_inspector.py      # Prevents sensitive data leaks to unapproved URLs.
│   ├── policy_gate.py           # Multi-signal decision gate (BLOCK / APPROVAL / ALLOW).
│   └── approval_workflow.py     # Manages human approval tokens & TOCTOU fingerprints.
│
├── storage/               # 🗄️ THE DUAL DATABASE LAYER
│   ├── duckdb/                  # Fast analytics engine for trace spans.
│   └── sqlalchemy/              # SQLite database for API keys, policies, and audit logs.
│
├── api/                   # ⚡ FASTAPI REST API ROUTERS
│   ├── app.py                   # Main FastAPI server entry point.
│   └── v1/                      # Endpoints (/traces, /security, /audit, /otlp).
│
├── ingest/                # 📥 TELEMETRY INGESTION PIPELINE
│   ├── buffer.py                # In-memory buffer queue & Dead-Letter Queue (DLQ).
│   └── normalizer.py            # Converts OpenTelemetry data into standard Vantage format.
│
├── replay/                # 🔄 DETERMINISTIC REPLAY ENGINE
│   └── engine.py                # Reconstructs past agent executions for offline debugging.
│
└── anomaly/               # 📊 STATISTICAL ANOMALY DETECTORS
    ├── z_score.py               # Detects latency & cost spikes.
    └── error_rate.py            # Detects sudden increases in AI error rates.
```

---

## 3. How to Run Vantage Locally (5 Simple Commands)

Open your terminal and run these commands to launch Vantage:

```bash
# 1. Navigate to directory
cd vantage

# 2. Activate Python Virtual Environment
.\.venv\Scripts\Activate.ps1   # (Windows)
# source .venv/bin/activate    # (Linux/Mac)

# 3. Seed Database with Demo Traces
python setup_project_and_seed.py

# 4. Start FastAPI Backend Server
python -m uvicorn vantage.api.app:app --reload

# 5. Open http://localhost:8000 in your browser!
```

---

## 4. How Testing Works in Vantage (69/69 Passing Pytest Suite)

To ensure Vantage is rock-solid and secure, we wrote **69 automated Pytest tests**.

### 💡 Why We Test
If a developer changes a line of code in `execution_controller.py`, we must be 100% sure that hackers cannot bypass security checks or leak data.

### ⚙️ The 3 Types of Tests in Vantage
1. **Unit Tests** (`tests/unit/`): Tests individual functions in isolation (e.g. testing if `PIIMasker` properly redacts a 16-digit credit card number).
2. **Integration Tests** (`tests/integration/`): Tests database connections, DuckDB queries, and API endpoints working together.
3. **Security Attack Simulations** (`tests/security/test_attack_simulations.py`): Simulates real-world hacker attacks:
   - Hacker tries prompt injection ("ignore previous rules").
   - Hacker tries to change approval arguments right before execution (TOCTOU attack).
   - Hacker tries to leak restricted customer data to an untrusted external URL.

### 🧪 Command to Run All Tests
```bash
cmd.exe /c ".venv\Scripts\python.exe -m pytest -v"
```
*(Result: 69 passed in 4.5 seconds!)*
: List[CanonicalVantageSpan]) -> List[AlertRecord]` method.
3. Register the detector string key in `vantage/domain/alerts.py`.
4. Add unit test verification in `tests/unit/test_anomaly_detectors.py`.

### Recipe 2: Adding a Custom Security Policy Rule
To add a custom policy rule (e.g. blocking database drops in any environment):
1. Open `vantage/security/policy_gate.py`.
2. Add rule check inside `MultiSignalPolicyGate.evaluate()`:
   ```python
   if ctx.action == "database.drop":
       matched_rules.append("HARD_BLOCK_DATABASE_DROP")
       return SecurityPolicyDecision(
           decision="BLOCK",
           reason_code="DATABASE_DROP_PROHIBITED",
           reason="Database drop operations are strictly prohibited across all environments",
           matched_rules=matched_rules,
           ...
       )
   ```
3. Add a test case in `tests/security/test_attack_simulations.py`.
