# SentinelAI v3.0: The Action Firewall for Autonomous Agents 🛡️🤖[![SentinelAI CI](https://github.com/drowglak-lab/sentinelai-v3/actions/workflows/test.yml/badge.svg)](https://github.com/drowglak-lab/sentinelai-v3/actions/workflows/test.yml)

**The High-Performance Security Layer for AI-Driven Banking Operations.**

SentinelAI is an Enterprise-grade **Action Firewall** designed to bridge the gap between autonomous AI agents and strict financial security requirements. In an era where LLMs execute code and handle transactions, SentinelAI ensures every action is validated, anonymized, and cryptographically logged before it touches the core banking system.



---

## 🏛️ The Three-Tier Zero-Trust Architecture

SentinelAI v3.0 has evolved from a simple proxy into a distributed, fault-tolerant gateway operating on three distinct layers:

1. **L2 - Business Logic (Dynamic Policy Engine):** * Reads declarative rules from `policies.yaml`.
   * Evaluates ABAC (Attribute-Based Access Control) and RBAC rules dynamically via Pydantic schemas. 
   * *Zero hardcode:* Security limits can be updated without recompiling or redeploying the service.
2. **L1 - Control Plane (FastAPI + Redis):**
   * Acts as the traffic orchestrator with strict Dependency Injection and Graceful Lifespan management.
   * Connects to a Redis cluster to monitor system state. 
   * Implements an **Adaptive Recovery Protocol (Ramp-Up)**, mitigating "Thundering Herd" attacks by slowly allowing traffic (e.g., 20% throughput) during system revival.
3. **L0 - Data Plane & Enforcer (Rust + RocksDB):**
   * A sub-15ms core engine written in Rust.
   * Utilizes an embedded RocksDB instance as an immutable memory layer.
   * **Autonomous Self-Defense:** If the Rust Enforcer detects a cryptographic mismatch between incoming data and the RocksDB log, it triggers an atomic, local `FAIL_SAFE` kill-switch, freezing the node instantly without waiting for human intervention.



---

## 🧪 The Engineering Journey & Experiments

Building SentinelAI was not a straight path. It was an iterative process of stress-testing, failing, and evolving. Here is the post-mortem of our architectural experiments:

* **Experiment 1: Overcoming the Python GIL**
  * *Challenge:* Standard Python threading hit a "glass ceiling" during load testing (capped at ~280 RPS with heavy latency).
  * *Solution:* We bypassed the Global Interpreter Lock (GIL) by utilizing PEP 734 concepts (Multiple Interpreters) and rewriting the heavy cryptographic evaluation in Rust via `pyo3`/`maturin`.
* **Experiment 2: The Distributed Kill-Switch**
  * *Challenge:* A compromised agent could flood the system before an admin could manually shut down the FastAPI server.
  * *Solution:* Built a two-tier kill-switch. An external `admin_panel.py` broadcasts emergency states via Redis (L1). Simultaneously, the Rust core maintains an atomic boolean in memory (L0). If either trips, the system immediately returns `503 SYSTEM_FROZEN`.
* **Experiment 3: Surviving the "AI Code Audit" (Enterprise Refactoring)**
  * *Challenge:* Early versions relied on global variables, hardcoded security policies (`dict`), and lacked safe lifecycle management—classic prototyping technical debt.
  * *Solution:* Conducted a massive Enterprise Refactoring. Implemented Dependency Injection (`Depends()`), replaced dictionaries with strict Pydantic `BaseModel` schemas for request validation, introduced `Enum` for state safety, and moved all configurations to `.env` using `pydantic-settings`.

---

## ⚖️ Regulatory Compliance (EU DORA Ready)

Designed with the **Digital Operational Resilience Act (DORA)** in mind:
* **Integrity:** SHA-256 Merkle Chaining ensures audit data remains cryptographically tamper-proof.
* **Recoverability:** Redis state-sync allows the gateway to gracefully resume the audit chain after system failures via controlled Ramp-Up phases.
* **Performance:** High-frequency trading requirements are met by isolating the slow I/O operations from the Rust validation core.

---

## 📂 Tech Stack
* **Language:** Python 3.12+ & **Rust** (Safety & Microsecond Speed).
* **Frameworks:** FastAPI (Asynchronous Orchestration), Pydantic (Validation), Maturin (Rust-Python bridge).
* **Infrastructure:** Docker & Docker Compose, **Redis** (State Management), **RocksDB** (Embedded High-Speed Storage).
* **Security:** RSA Signing, SHA-256 Chaining, ABAC/RBAC Policy Engine.

---

## 🚀 Quick Start (Enterprise Deployment)

The entire ecosystem is containerized for consistent deployment.

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/sentinel-ai.git

# 2. Start the Secure Gateway, Redis, and SIEM Audit Service
docker-compose up --build
```

### 🎮 Live Demonstration: The Control Plane

You can interact with the distributed Kill-Switch and Policy Engine in real-time using the included CLI Admin tool:

```bash
# Trigger an immediate global lockdown (returns 503 SYSTEM_FROZEN)
python admin_panel.py FROZEN

# Slowly revive the system, allowing only 20% of traffic (returns 429 for blocked requests)
python admin_panel.py RAMP_UP 0.2

# Return to full capacity
python admin_panel.py NORMAL
```

---

## 👨‍💻 Developer
**Aleksei** | *AI Software Engineer*
Specializing in AI Execution Security, Distributed Systems, and High-Performance Backend Architecture.
📍 Valencia, Spain (Ready for complex EU Fintech challenges).

