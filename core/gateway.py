import random
import asyncio
import redis.asyncio as async_redis
from enum import Enum
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from sentinel_core import SentinelCore
from execution.policy_engine import PolicyEngine

from core.idempotency import FinTechIdempotencyMiddleware

# 💥 ИМПОРТЫ ДЛЯ OUTBOX ПАТТЕРНА И ZERO-TRUST
from core.database import init_db, get_db_connection
from core.transaction import TransactionManager
from core.relay import outbox_relay_worker
from security.enforcer import DeterministicEnforcer


# ==========================================
# 1. КОНФИГУРАЦИЯ И СТРОГИЕ ТИПЫ
# ==========================================
class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    rocksdb_path: str = "/app/data/rocksdb"

settings = Settings()

class SystemMode(str, Enum):
    NORMAL = "NORMAL"
    FROZEN = "FROZEN"
    READ_ONLY = "READ_ONLY"
    RAMP_UP = "RAMP_UP"

class RecoveryState:
    def __init__(self):
        self.mode = SystemMode.NORMAL
        self.rate_limit = 1.0

class TransferRequest(BaseModel):
    tx_id: str = Field(..., description="Уникальный ID транзакции")
    tx_hash: str = Field(..., description="Хэш данных для проверки в Rust")
    role: str = Field(default="USER", description="Роль инициатора")
    amount: float = Field(..., gt=0, description="Сумма перевода")
    target: str = Field(..., description="Счет назначения (теперь это должен быть UUID из белого списка)")


# ==========================================
# 2. ФОНОВЫЕ ПРОЦЕССЫ
# ==========================================
async def sync_with_redis(redis_client: async_redis.Redis, state: RecoveryState):
    print("📡 Sentinel Sync: Connected to Redis Control Plane")
    while True:
        try:
            mode_val = await redis_client.get("sentinel:mode")
            rate_val = await redis_client.get("sentinel:rate_limit")

            if mode_val:
                try:
                    state.mode = SystemMode(mode_val)
                except ValueError:
                    pass
            if rate_val:
                state.rate_limit = float(rate_val)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Redis Sync Error: {e}")
        await asyncio.sleep(1)


# ==========================================
# 3. GLOBAL CONNECTIONS & LIFECYCLE
# ==========================================
shared_redis_client = async_redis.from_url(settings.redis_url, decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.core = SentinelCore(settings.rocksdb_path, settings.redis_url)
    app.state.redis = shared_redis_client
    app.state.recovery = RecoveryState()
    # Оставляем PolicyEngine в памяти для других модулей, но убираем из критического пути платежей
    app.state.policy_engine = PolicyEngine("config/policies.yaml") 

    # 💥 ИНИЦИАЛИЗАЦИЯ ФИНТЕХ-ЯДРА
    await init_db()
    app.state.relay_task = asyncio.create_task(outbox_relay_worker())

    app.state.sync_task = asyncio.create_task(
        sync_with_redis(app.state.redis, app.state.recovery)
    )
    yield

    app.state.sync_task.cancel()
    app.state.relay_task.cancel()  # Гасим релей при выключении
    try:
        await app.state.sync_task
        await app.state.relay_task
    except asyncio.CancelledError:
        pass
    await app.state.redis.close()


app = FastAPI(title="SentinelAI v3.0 - Enterprise Edition", lifespan=lifespan)

# ==========================================
# 4. MIDDLEWARE CHAIN
# ==========================================
app.add_middleware(
    FinTechIdempotencyMiddleware,
    redis_client=shared_redis_client,
    strict_mode=False
)

@app.middleware("http")
async def security_gate(request: Request, call_next):
    if not hasattr(request.app.state, "recovery"):
        return await call_next(request)

    core: SentinelCore = request.app.state.core
    state: RecoveryState = request.app.state.recovery

    if core.is_frozen() or state.mode == SystemMode.FROZEN:
        return JSONResponse(status_code=503, content={"detail": "SYSTEM_FROZEN"})

    if state.mode == SystemMode.READ_ONLY and request.method != "GET":
        return JSONResponse(status_code=403, content={"detail": "SYSTEM_READ_ONLY"})

    if state.mode == SystemMode.RAMP_UP:
        if random.random() > state.rate_limit:
            return JSONResponse(status_code=429, content={"detail": "RECOVERY_RAMP_UP"})

    return await call_next(request)


# ==========================================
# 5. DEPENDENCY INJECTION & ENDPOINTS
# ==========================================
def get_sentinel_core(request: Request) -> SentinelCore:
    return request.app.state.core

@app.post("/v1/banking/transfer")
async def handle_transfer(
        req: TransferRequest,
        request: Request,  
        core: SentinelCore = Depends(get_sentinel_core)
):
    # 1. Извлекаем Correlation ID для трейсинга
    trace_id = request.headers.get("X-Correlation-ID", "unknown")
    idem_key = request.headers.get("Idempotency-Key", req.tx_id)

    db_conn = await get_db_connection()
    enforcer = DeterministicEnforcer(db_conn)
    tx_manager = TransactionManager(db_conn)

    try:
        # 2. 🛡️ ZERO-TRUST AI: Проверяем намерения, а не сырой payload
        # Теперь req.target должен быть UUID из белого списка, а не IBAN!
        is_safe, reason, safe_context = await enforcer.validate_transfer_intent(
            user_id=req.role,
            ai_payload={"amount": req.amount, "target_beneficiary_id": req.target}
        )

        if not is_safe:
            return JSONResponse(
                status_code=403, 
                content={"status": "error", "detail": "SECURITY_INTERVENTION", "reason": reason}
            )

        # 3. ⚙️ Аппаратная проверка Rust (оставляем для защиты памяти/целостности)
        is_valid = core.audit_and_verify(req.tx_id, req.tx_hash)
        if not is_valid:
            return JSONResponse(status_code=400, content={"status": "error", "detail": "INTEGRITY_MISMATCH"})

        # 4. 💸 ФИНАНСОВАЯ ТРАНЗАКЦИЯ (Только с БЕЗОПАСНЫМ контекстом)
        payment_result = await tx_manager.authorize_transfer(
            idempotency_key=idem_key,
            user_id=safe_context["user_id"],
            amount=safe_context["amount"],
            target=safe_context["target_iban"] # Берем НАСТОЯЩИЙ IBAN из БД
        )
    finally:
        await db_conn.close()  # Обязательно возвращаем коннект в пул

    return {
        "status": "success",
        "trace_id": trace_id,
        "payment": payment_result,
        "engine": "DeterministicEnforcer + TransactionManager"
    }
    return {
        "status": "success",
        "trace_id": trace_id,
        "payment": payment_result,
        "engine": "TransactionManager + Outbox Pattern"
    }
