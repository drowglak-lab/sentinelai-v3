# SentinelAI v3.0: The Zero-Trust Action Firewall for Autonomous Agents 🛡️🤖
[![SentinelAI CI](https://github.com/drowglak-lab/sentinelai-v3/actions/workflows/test.yml/badge.svg)](https://github.com/drowglak-lab/sentinelai-v3/actions/workflows/test.yml)

**The Production-Grade Security Layer for AI-Driven Financial Operations.**

SentinelAI is an Enterprise-grade **Action Firewall** designed to bridge the critical "Semantic Gap" between autonomous AI agents and strict financial security boundaries. In an era where LLMs suffer from prompt injections and hallucinate payloads, SentinelAI ensures every execution intent is deterministically validated, stripped of AI-generated artifacts, and cryptographically audited before it touches the core banking ledger.

---

## 🏛️ The Zero-Trust Architecture (Staff-Level Design)

SentinelAI v3.0 evolved from a simple proxy into a distributed, fault-tolerant execution boundary. It completely distrusts the LLM, relying on a strict three-tier separation of concerns:

### 1. Deterministic Enforcement (Semantic Gap Protection)
AI models dictate *intent*, never *execution parameters*.
* **Strict Payload Mapping:** The LLM only operates with whitelisted UUIDs. The Enforcer securely maps these UUIDs to real, sanitized banking data (e.g., IBANs) from an isolated, trusted database.
* **Prompt Injection Neutralization:** Even if an attacker compromises the LLM to alter the JSON payload (e.g., `"destination": "attacker_account"`), the Deterministic Enforcer drops the transaction with a `SEMANTIC_VIOLATION` before it reaches the transactional core.

### 2. Policy-as-Code (Open Policy Agent Sidecar)
Business logic is completely decoupled from the Python monolith.
* **Rego v1 Policies:** Security thresholds, AML risk scores, and sanction lists are evaluated dynamically by an isolated **OPA (Open Policy Agent)** container.
* **Resilient Circuit Breaker:** The Gateway integrates with OPA via a fail-safe Circuit Breaker. If the policy engine experiences network degradation, the system trips the breaker and defaults to `Deny-by-Default` (503 Service Unavailable), preventing bypass attacks.

### 3. WORM-Compliant Cryptographic Audit Ledger
Audits must survive a root-level system compromise.
* **Cryptographic Hash Chain:** Every financial state transition (`INTENT_CREATED` -> `AUTH_APPROVED`) is permanently linked to the previous transaction using SHA-256 Merkle Chaining.
* **Tamper-Evident:** If a malicious administrator alters a database record to hide a fraudulent transfer, the hash chain breaks instantly, failing the `verify_chain.py` cryptographic audit. Designed for strict SOC2 and PSD2 compliance.

---

## 💳 Transactional Core & Financial Guarantees

SentinelAI goes beyond simple API routing by implementing strict financial state management, ensuring zero data loss and preventing double-spend anomalies under severe concurrency.

* **Distributed Idempotency:** A Redis-backed idempotency layer strictly prevents race conditions and replay attacks during parallel transaction requests.
* **ACID Boundaries & Locking:** Utilizes strict database row-locking (`FOR UPDATE`) to ensure state transitions are atomic.
* **Transactional Outbox Pattern:** Solves the dual-write problem. Database updates (payment_intents) and event publishing (outbox_events) are bound within a single ACID transaction.
* **Asynchronous Message Relay:** A decoupled background worker guarantees at-least-once delivery of transaction events to downstream consumers (Kafka simulators).

---

## 📂 Tech Stack
* **Language:** Python 3.12+ & **Rust** (Safety & Microsecond Core Verification).
* **Frameworks:** FastAPI (Asynchronous Orchestration), Pydantic (Validation).
* **Security & Policy:** **Open Policy Agent (OPA)**, Rego v1, Circuit Breaker Pattern.
* **Infrastructure:** Docker & Docker Compose, **Redis** (State Management), **SQLite/RocksDB** (Transactional Core & Embedded Fast-Storage).

---

## 🚀 Quick Start (Enterprise Deployment)

The entire decoupled ecosystem is containerized for consistent deployment.

```bash
# 1. Clone the repository
git clone [https://github.com/your-repo/sentinel-ai.git](https://github.com/your-repo/sentinel-ai.git)

# 2. Start the Secure Gateway, OPA Policy Engine, Redis, and SIEM Audit Service
docker-compose up --build
