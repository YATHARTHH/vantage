# Vantage System Architecture & Decision Guide (Simple Language)

Welcome to **Document 02**! This document explains how Vantage's backend system is structured, why we chose specific technologies (and rejected others), and what **Architecture Decision Records (ADRs)** are in simple, plain English.

---

## ❓ What is an ADR (Architecture Decision Record)?

Before looking at the backend design, let's understand what an **ADR** is:

> 💡 **Simple Analogy**: Imagine a team of architects building a house. They have to decide: *"Should we use a wooden roof or a concrete roof?"* They choose concrete because it survives heavy storms. To make sure future builders don't replace it with wood without knowing why, they write down a quick note: **"We chose concrete because of storms."**

In software development, an **Architecture Decision Record (ADR)** is that exact note! It is a short written document capturing:
1. **The Context**: What problem were we trying to solve?
2. **The Decision**: What technology or design did we choose?
3. **The Consequence**: What are the benefits and trade-offs of this choice?

We use ADRs so that any engineer, intern, or manager looking at Vantage can instantly understand **WHY** we built things the way we did.

---

## 1. System Architecture: How Vantage Works (Simple Factory Analogy)

Think of Vantage's backend as an **automated security & analytics factory** with 6 connected rooms:

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             THE VANTAGE BACKEND FACTORY                                  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Room 1: SOURCES          AI agents (LangChain, LlamaIndex, Python) send activity data.   │
│         │                                                                                │
│         ▼                                                                                │
│ Room 2: INGESTION        FastAPI receives data, authenticates it, masks secrets (PII),    │
│         │                and buffers incoming spans safely in memory.                    │
│         │                                                                                │
│         ├──────────────────────────────┐                                                 │
│         ▼                              ▼                                                 │
│ Room 3: DUAL STORAGE     DuckDB (Fast analytical queries) + SQLite (Transactional data).   │
│         │                                                                                │
│         ▼                                                                                │
│ Room 4: SECURITY ENGINE  ExecutionController intercepts AI tool calls before they run.   │
│         │                Checks user permissions, scans for prompt injection & data leaks.│
│         │                                                                                │
│         ▼                                                                                │
│ Room 5: REPLAY & ANOMALY Analyzes traces offline, detects price spikes, and allows       │
│         │                "What-If" testing without touching production.                  │
│         ▼                                                                                │
│ Room 6: DASHBOARD        React frontend displays live traces, DAG visualizer, & approvals.│
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack Choices: Why We Chose These Tools

Here is why we picked our exact technologies in plain language:

### 🐍 Python 3.12+ (Backend Language)
* **Why**: Python is the universal language of AI. All major AI frameworks (LangChain, OpenAI, LlamaIndex, PyTorch) are native to Python.
* **Why not Node.js or Go**: Node.js and Go lack deep AI library support and math tools needed for anomaly detection.

### ⚡ FastAPI (API Web Framework)
* **Why**: It is extremely fast, handles async tasks easily, and automatically generates interactive API documentation (`http://localhost:8000/docs`).
* **Why not Flask or Django**: Flask and Django lock up when handling thousands of streaming trace events per second.

### 🦆 DuckDB (Analytics Database for Spans)
* **Why**: DuckDB is an "in-memory columnar database"—think of it like SQLite specifically designed for super-fast analytics. It can calculate average cost or token count across 1,000,000 trace rows in milliseconds without needing an expensive database server.
* **Why not PostgreSQL or ClickHouse**: PostgreSQL gets slow on huge analytics queries, while ClickHouse requires complex server clusters to set up.

### 🗄️ SQLite + SQLAlchemy 2.0 (Transactional Database)
* **Why**: Used for storing standard operational data (API keys, user project names, human approval tokens, and audit logs). It is zero-setup, reliable, and transactional.
* **Why DuckDB + SQLite together?** We separate high-volume analytics (DuckDB) from transactional rules (SQLite) so analytics queries never lock up security policy updates.

### ⚛️ React 18 + Vite (Frontend Web Portal)
* **Why**: Vite gives lightning-fast page loading, and React makes interactive charts and visual trace trees (DAGs) smooth and easy to use.

---

## 3. Our 10 Architecture Decision Records (ADRs) Explained Simply

1. **ADR-001 (Dual Database Separation)**: We use DuckDB for fast telemetry analytics and SQLite for security rules so analytics queries don't slow down security checks.
2. **ADR-002 (Dead-Letter Queue Buffer)**: If traffic spikes suddenly, telemetry is buffered safely in memory. If memory fills up, excess spans are written to disk (`.dlq_spans.jsonl`) so no data is ever lost.
3. **ADR-003 (ExecutionController Choke Point)**: ALL AI tool executions must go through ONE single gateway (`ExecutionController`). No tool can run without passing security checks first.
4. **ADR-004 (TOCTOU Action Fingerprinting)**: When a manager approves an AI action, we fingerprint the exact arguments with a SHA-256 hash. If the AI changes the parameters right before execution, it is blocked.
5. **ADR-005 (Fail-Closed Security)**: If a security scanner crashes or fails, Vantage defaults to **BLOCKING** the action to keep your system safe.
6. **ADR-006 (In-Flight PII Redaction)**: Credit cards and passwords are masked *before* telemetry is saved to disk so sensitive user data is never stored.
7. **ADR-007 (Cryptographic Audit Trail)**: Every audit log entry is cryptographically linked to the previous entry using SHA-256 hashes. If anyone tries to alter past logs in the database, the hash chain breaks instantly.
8. **ADR-008 (SSRF Webhook Firewall)**: Webhook notifications re-verify destination IP addresses before sending data to prevent hackers from targeting internal private networks.
9. **ADR-009 (Multi-Signal Precedence)**: Security decisions follow a strict hierarchy: `BLOCK` beats `APPROVAL`, `APPROVAL` beats `WARN`, `WARN` beats `ALLOW`.
10. **ADR-010 (OpenTelemetry Protocol Mapping)**: Vantage ingests standard OpenTelemetry format so it works with any agent framework without custom plugins.

