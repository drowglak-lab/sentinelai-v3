import hashlib
import json

class CryptographicAuditChain:
    def __init__(self, db_conn):
        self.db = db_conn

    async def append_record(self, tx_id: str, action: str, payload: dict) -> str:
        """
        Добавляет неизменяемую запись в криптографическую цепь.
        Вызывается строго внутри уже открытой транзакции базы данных.
        """
        # 1. Получаем хэш предыдущего блока
        cursor = await self.db.execute("""
            SELECT current_hash FROM audit_ledger 
            ORDER BY seq_id DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        
        # Если база пустая, используем Genesis-хэш
        prev_hash = row["current_hash"] if row else "0000000000000000000000000000000000000000000000000000000000000000"

        # 2. Детерминированная сериализация payload (чтобы ключи всегда были в одном порядке)
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # 3. Вычисляем новый хэш: SHA256(prev_hash + tx_id + action + payload)
        data_to_hash = f"{prev_hash}|{tx_id}|{action}|{payload_str}"
        current_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()

        # 4. Записываем в книгу аудита
        await self.db.execute("""
            INSERT INTO audit_ledger (tx_id, action, payload, prev_hash, current_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (tx_id, action, payload_str, prev_hash, current_hash))

        return current_hash
