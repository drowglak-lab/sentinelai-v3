import json
import asyncio
import hashlib
import time
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis

IDEMPOTENCY_TTL = 86400  # 24 часа (стандарт финтеха для хранения ключей)
LOCK_TTL = 15            # Максимальное время на транзакцию (защита от Deadlock)
POLL_INTERVAL = 0.2      # Как часто проверять лок
MAX_WAIT_TIME = 10       # Максимум ждем параллельный запрос

class FinTechIdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: Redis, strict_mode: bool = True):
        super().__init__(app)
        self.redis = redis_client
        self.strict_mode = strict_mode  # Если True, отклоняет POST без Idempotency-Key

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Идемпотентность нужна только для мутирующих запросов
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            if self.strict_mode:
                return Response(
                    content=json.dumps({"error": "Idempotency-Key header is required"}),
                    status_code=400,
                    media_type="application/json"
                )
            return await call_next(request)

        # 💥 Хак уровня FastAPI: Читаем body безопасно 
        # Если прочитать request.body() напрямую, endpoint зависнет. Мы обязаны восстановить stream.
        body = await request.body()
        payload_hash = hashlib.sha256(body).hexdigest()

        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive

        # 🔐 Scoping: Привязываем ключ к пользователю (в демо берем IP) и URL
        # В проде вместо IP должен быть user_id из проверенного JWT токена
        client_identity = request.client.host if request.client else "unknown"
        scope = f"{request.url.path}:{client_identity}"
        
        redis_key = f"idem:state:{scope}:{idempotency_key}"
        lock_key = f"idem:lock:{scope}:{idempotency_key}"

        start_time = time.time()

        # ⏳ 1. SMART POLLING & LOCK ACQUISITION
        while True:
            # Пытаемся взять эксклюзивный лок (SET NX)
            lock_acquired = await self.redis.set(lock_key, "1", nx=True, ex=LOCK_TTL)
            
            if lock_acquired:
                break  # Лок наш, идем выполнять логику
            
            # Если лок занят, возможно запрос УЖЕ выполнен и сохранен.
            # Если это так - нет смысла ждать лок, просто берем результат и отдаем.
            existing_state_raw = await self.redis.get(redis_key)
            if existing_state_raw:
                state = json.loads(existing_state_raw)
                if state.get("status") == "COMPLETED":
                    break # Выходим из цикла ожидания

            # Защита от вечного зависания
            if time.time() - start_time > MAX_WAIT_TIME:
                return Response(
                    content=json.dumps({"error": "Timeout: another request is processing this key"}),
                    status_code=408,
                    media_type="application/json"
                )
            
            await asyncio.sleep(POLL_INTERVAL)

        try:
            # 🛡️ 2. СТРОГАЯ ПРОВЕРКА СОСТОЯНИЯ (State Machine)
            existing_state_raw = await self.redis.get(redis_key)
            if existing_state_raw:
                state = json.loads(existing_state_raw)
                
                # 🔴 Payload Mismatch Check (Защита от подмены)
                if state.get("payload_hash") != payload_hash:
                    return Response(
                        content=json.dumps({"error": "Idempotency mismatch: payload modified"}),
                        status_code=409,
                        media_type="application/json"
                    )
                
                if state.get("status") == "COMPLETED":
                    # Возвращаем закэшированный УСПЕШНЫЙ ответ
                    return Response(
                        content=state["response_body"],
                        status_code=state["response_status"],
                        headers=state["response_headers"]
                    )
                elif state.get("status") == "STARTED":
                    # 🔴 Crash Recovery:
                    # Если статус STARTED, но мы смогли взять lock (он истек), 
                    # значит предыдущий воркер умер (OOM, Restart) прямо во время обработки.
                    # Позволяем запросу пройти дальше и перезапустить процесс.
                    pass

            # 🚀 3. ФИКСИРУЕМ НАЧАЛО (STARTED)
            await self.redis.set(
                redis_key,
                json.dumps({
                    "status": "STARTED",
                    "payload_hash": payload_hash,
                    "timestamp": time.time()
                }),
                ex=IDEMPOTENCY_TTL
            )

            # ⚡ 4. ВЫПОЛНЯЕМ БИЗНЕС-ЛОГИКУ
            response = await call_next(request)

            # 📦 Перехватываем Body ответа
            res_body = b""
            async for chunk in response.body_iterator:
                res_body += chunk

            # 💾 5. СОХРАНЯЕМ РЕЗУЛЬТАТ (COMPLETED)
            # Внимание: мы кэшируем только успехи (2xx) и ошибки бизнес-логики (4xx).
            # 5xx (падение БД/сети) мы НЕ кэшируем, чтобы клиент мог безопасно сделать retry!
            if response.status_code < 500:
                completed_state = {
                    "status": "COMPLETED",
                    "payload_hash": payload_hash,
                    "response_status": response.status_code,
                    "response_body": res_body.decode('utf-8', errors='ignore'),
                    "response_headers": {k: v for k, v in response.headers.items() if k.lower() not in ('content-length', 'content-encoding')},
                    "timestamp": time.time()
                }
                await self.redis.set(redis_key, json.dumps(completed_state), ex=IDEMPOTENCY_TTL)

            return Response(
                content=res_body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )

        finally:
            # 🔓 6. ГАРАНТИРОВАННОЕ СНЯТИЕ ЛОКА
            await self.redis.delete(lock_key)
