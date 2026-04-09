import aiosqlite
import json

DB_PATH = "data/ledger.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица платежей (Payment Intent)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_intents (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица Outbox (наша очередь сообщений)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS outbox_events (
                id TEXT PRIMARY KEY,
                aggregate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 💥 НОВАЯ ТАБЛИЦА: Доверенные получатели (White-list)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS approved_beneficiaries (
                id TEXT PRIMARY KEY, 
                owner_user_id TEXT NOT NULL, 
                account_iban TEXT NOT NULL,
                is_active INTEGER DEFAULT 1, 
                aml_risk_score INTEGER DEFAULT 0, 
                country_code TEXT DEFAULT 'ES'
            )
        """)
        
        # Закидываем тестового получателя (UUID: 1111-2222-3333-4444)
        await db.execute("""
            INSERT OR IGNORE INTO approved_beneficiaries (id, owner_user_id, account_iban, aml_risk_score)
            VALUES ('1111-2222-3333-4444', 'ADMIN', 'ES12345678901234567890', 10)
        """)
        await db.commit()
    print("🗄️ [Database] Ledger and Compliance tables initialized")

async def get_db_connection():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row # Чтобы получать результаты как словари
    return db
