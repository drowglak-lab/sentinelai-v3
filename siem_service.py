import uvicorn
import sqlite3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

app = FastAPI(title="SentinelAI: Persistent SIEM Witness")

class RootHashPayload(BaseModel):
    root_hash: str
    prev_hash: str
    timestamp: str
    signature: str

DB_PATH = "audit_siem.db"

def init_db():
    """Создаем таблицу, если её нет. Это наш фундамент."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_chain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_hash TEXT UNIQUE,
            prev_hash TEXT,
            timestamp TEXT,
            signature TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Инициализируем БД при запуске модуля
init_db()

# Загружаем публичный ключ шлюза
with open("core/public.pem", "rb") as key_file:
    PUBLIC_KEY = serialization.load_pem_public_key(key_file.read())

@app.get("/latest")
async def get_latest_root():
    """Позволяет шлюзу узнать текущую голову цепи"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT root_hash FROM audit_chain ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return {"latest_root": row[0] if row else "0" * 64}

@app.post("/ingest")
async def ingest_root(data: RootHashPayload):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Защита от Replay-атак (проверяем уникальность через БД)
    cursor.execute('SELECT 1 FROM audit_chain WHERE root_hash = ?', (data.root_hash,))
    if cursor.fetchone():
        conn.close()
        return {"status": "ignored", "reason": "already_processed"}

    # 2. Криптографическая проверка подписи
    try:
        PUBLIC_KEY.verify(
            bytes.fromhex(data.signature),
            data.root_hash.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
    except InvalidSignature:
        conn.close()
        raise HTTPException(status_code=403, detail="Invalid Root Signature")

    # 3. Валидация Hash Chain (сверяемся с последним записанным корнем)
    cursor.execute('SELECT root_hash FROM audit_chain ORDER BY id DESC LIMIT 1')
    last_row = cursor.fetchone()
    last_root = last_row[0] if last_row else "0" * 64

    # Если база не пуста и пришел неверный prev_hash
    if last_root != "0" * 64 and data.prev_hash != last_root:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Chain broken. Expected: {last_root[:12]}")

    # 4. Сохранение «улики» в вечное хранилище
    try:
        cursor.execute('''
            INSERT INTO audit_chain (root_hash, prev_hash, timestamp, signature)
            VALUES (?, ?, ?, ?)
        ''', (data.root_hash, data.prev_hash, data.timestamp, data.signature))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")
    
    conn.close()
    print(f"[+] Persistent Root Accepted: {data.root_hash[:12]}")
    return {"status": "accepted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
