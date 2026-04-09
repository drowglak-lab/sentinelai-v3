import uuid
import json
import asyncio

# 💥 ИМПОРТИРУЕМ НАШ КРИПТО-АУДИТ
from security.audit_chain import CryptographicAuditChain


class TransactionManager:
    def __init__(self, db_conn):
        self.db = db_conn

    async def _append_outbox(self, aggregate_id: str, event_type: str, payload: dict):
        """Пишет событие в Outbox-таблицу"""
        event_id = str(uuid.uuid4())
        await self.db.execute("""
                              INSERT INTO outbox_events (id, aggregate_id, event_type, payload)
                              VALUES (?, ?, ?, ?)
                              """, (event_id, aggregate_id, event_type, json.dumps(payload)))

    async def authorize_transfer(self, idempotency_key: str, user_id: str, amount: float, target: str) -> dict:
        intent_id = str(uuid.uuid4())

        # 1. ОТКРЫВАЕМ ТРАНЗАКЦИЮ
        await self.db.execute("BEGIN")
        try:
            # Пытаемся создать платеж. Если idempotency_key уже есть, SQLite выдаст ошибку IntegrityError
            await self.db.execute("""
                                  INSERT INTO payment_intents (id, idempotency_key, user_id, amount, target, status)
                                  VALUES (?, ?, ?, ?, ?, 'AUTHORIZING')
                                  """, (intent_id, idempotency_key, user_id, amount, target))

            # В ЭТОЙ ЖЕ ТРАНЗАКЦИИ пишем событие
            await self._append_outbox(intent_id, "AUTH_STARTED", {"amount": amount, "target": target})

            # 💥 НОВОЕ: Намертво вшиваем операцию в криптографическую цепь
            audit = CryptographicAuditChain(self.db)
            await audit.append_record(
                tx_id=intent_id,
                action="INTENT_CREATED",
                payload={"user": user_id, "amount": amount, "target": target}
            )

            await self.db.commit()  # Фиксируем атомарно!
        except Exception as e:
            await self.db.execute("ROLLBACK")
            # Ищем существующий платеж по ключу идемпотентности
            cursor = await self.db.execute("SELECT id, status FROM payment_intents WHERE idempotency_key = ?",
                                           (idempotency_key,))
            existing = await cursor.fetchone()
            if existing:
                return dict(existing)
            raise e

        # --- ГРАНИЦА ТРАНЗАКЦИИ ---
        # Здесь мы бы делали реальный HTTP запрос в банк (эквайринг).
        # Эмулируем ответ банка с задержкой:
        await asyncio.sleep(0.5)
        bank_approved = True

        # 2. ФИКСИРУЕМ ОТВЕТ БАНКА
        await self.db.execute("BEGIN")
        try:
            new_status = "AUTHORIZED" if bank_approved else "FAILED"
            event_type = "AUTH_APPROVED" if bank_approved else "AUTH_FAILED"

            await self.db.execute("UPDATE payment_intents SET status = ? WHERE id = ?", (new_status, intent_id))
            await self._append_outbox(intent_id, event_type, {"bank_ref": "REF-999"})

            # 💥 НОВОЕ: Логируем результат в крипто-цепь
            audit = CryptographicAuditChain(self.db)
            await audit.append_record(
                tx_id=intent_id,
                action=event_type,
                payload={"bank_ref": "REF-999", "final_status": new_status}
            )

            await self.db.commit()
        except Exception as e:
            await self.db.execute("ROLLBACK")
            raise e

        return {"id": intent_id, "status": new_status}
