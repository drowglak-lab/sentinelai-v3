import sentinel_core
import json
import logging
import asyncio
import httpx
import hashlib
import os
from datetime import datetime
from core.crypto_audit import MerkleManager

logger = logging.getLogger("sentinel-ai")

# Настройки инфраструктуры
SIEM_URL = os.getenv("SIEM_URL", "http://127.0.0.1:9000")

# Настройки аудита
AUDIT_BUFFER = []
AUDIT_LOCK = asyncio.Lock()
MAX_BUFFER_SIZE = 10000
FLUSH_THRESHOLD = 5
WAL_FILE = "audit_wal.json" 

merkle_manager = MerkleManager()

async def flush_batch(batch: list):
    """Сборка Merkle Root и отправка в SIEM с бэкапом в WAL"""
    current_root = merkle_manager.build_merkle_root(batch)
    chain_hash = hashlib.sha256((merkle_manager.prev_root + current_root).encode()).hexdigest()
    
    payload = {
        "root_hash": chain_hash,
        "prev_hash": merkle_manager.prev_root,
        "timestamp": datetime.utcnow().isoformat(),
        "signature": merkle_manager.sign_hash(chain_hash)
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Используем динамический URL
            await client.post(f"{SIEM_URL}/ingest", json=payload, timeout=2.0)
            merkle_manager.prev_root = chain_hash # Синхронизируем цепь
        except Exception as e:
            logger.error(f"[NETWORK_ERROR] SIEM unreachable at {SIEM_URL}: {e}. Moving to WAL.")
            with open(WAL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")

async def periodic_flush():
    """Фоновый таймер: сброс логов при низком трафике"""
    while True:
        await asyncio.sleep(3.0)
        async with AUDIT_LOCK:
            if AUDIT_BUFFER:
                batch = list(AUDIT_BUFFER)
                AUDIT_BUFFER.clear()
                asyncio.create_task(flush_batch(batch))

async def retry_worker():
    """Фоновый регенератор: досылает данные из WAL при восстановлении связи"""
    while True:
        await asyncio.sleep(10.0) 
        if not os.path.exists(WAL_FILE) or os.path.getsize(WAL_FILE) == 0:
            continue

        async with httpx.AsyncClient() as client:
            remaining = []
            try:
                with open(WAL_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines:
                    if not line.strip(): continue
                    data = json.loads(line)
                    try:
                        # Используем динамический URL
                        await client.post(f"{SIEM_URL}/ingest", json=data, timeout=3.0)
                        merkle_manager.prev_root = data["root_hash"]
                        logger.info(f"[RECOVERY] Synced WAL batch: {data['root_hash'][:12]}")
                    except Exception:
                        remaining.append(line)
                with open(WAL_FILE, "w", encoding="utf-8") as f:
                    f.writelines(remaining)
            except Exception as e:
                logger.error(f"[WAL_ERROR] Recovery worker failed: {e}")

class EnrichmentStage:
    async def process(self, ctx):
        mock_db = {"standard": {"kyc_status": "verified", "account_age_days": 365.0},
                   "unverified": {"kyc_status": "pending", "account_age_days": 2.0}}
        tier = ctx.raw_payload.get("user_tier", "unverified")
        profile = mock_db.get(tier, {"kyc_status": "none", "account_age_days": 0.0})
        ctx.domain_data.update(profile)
        return ctx

class RustEvaluationStage:
    async def process(self, ctx):
        res = sentinel_core.fast_evaluate(tool_name="transfer_funds", context=ctx.domain_data)
        ctx.decision = "SUCCESS" if res.decision == sentinel_core.Decision.Allow else "DENIED"
        ctx.policy_id, ctx.traces = res.policy_id, res.traces
        return ctx

class ExplainStage:
    async def process(self, ctx):
        if ctx.decision == "DENIED":
            for t in ctx.traces:
                if t.matched and "Enforce" in str(t.mode):
                    ctx.reasons.append(f"Block by policy: {t.policy_id}")
        return ctx

class ForensicAuditStage:
    async def process(self, ctx):
        event = {"tx_id": ctx.tx_id, "decision": ctx.decision, "policy": ctx.policy_id}
        event_hash = hashlib.sha256(json.dumps(event).encode()).hexdigest()
        async with AUDIT_LOCK:
            if len(AUDIT_BUFFER) >= MAX_BUFFER_SIZE: raise RuntimeError("Audit buffer full")
            AUDIT_BUFFER.append(event_hash)
            if len(AUDIT_BUFFER) >= FLUSH_THRESHOLD:
                batch = list(AUDIT_BUFFER); AUDIT_BUFFER.clear()
                asyncio.create_task(flush_batch(batch))
        return ctx
