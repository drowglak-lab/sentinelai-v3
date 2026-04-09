import sqlite3
import hashlib
import json
import sys

DB_PATH = "data/ledger.db"
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def verify_audit_chain():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM audit_ledger ORDER BY seq_id ASC")
        rows = cursor.fetchall()
        
        if not rows:
            print("📭 Аудит-журнал пуст. Нет транзакций для проверки.")
            return

        print(f"🔍 Начинаем криптографическую проверку {len(rows)} записей...\n")
        
        expected_prev_hash = GENESIS_HASH
        is_valid = True

        for row in rows:
            seq_id = row["seq_id"]
            tx_id = row["tx_id"]
            action = row["action"]
            payload = row["payload"]
            prev_hash = row["prev_hash"]
            stored_hash = row["current_hash"]

            # 1. Проверяем неразрывность цепи (Chain Continuity)
            if prev_hash != expected_prev_hash:
                print(f"❌ РАЗРЫВ ЦЕПИ на Seq {seq_id}: Хэш предыдущего блока не совпадает!")
                print(f"   Ожидалось: {expected_prev_hash}")
                print(f"   В базе:    {prev_hash}")
                is_valid = False
                break

            # 2. Проверяем целостность данных (Data Integrity)
            data_to_hash = f"{prev_hash}|{tx_id}|{action}|{payload}"
            calculated_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()

            if calculated_hash != stored_hash:
                print(f"❌ ПОДДЕЛКА ДАННЫХ на Seq {seq_id}: Обнаружено изменение payload!")
                print(f"   Рассчитанный хэш: {calculated_hash}")
                print(f"   Хэш в базе:       {stored_hash}")
                is_valid = False
                break

            print(f"✅ Блок {seq_id:03d} | TX: {tx_id[:8]}... | Action: {action:<15} | Hash OK")
            expected_prev_hash = stored_hash

        print("-" * 60)
        if is_valid:
            print("🛡️ АУДИТ УСПЕШЕН: Криптографическая цепь абсолютно цела.")
            print("Ни одна транзакция не была изменена или удалена.")
        else:
            print("🚨 АУДИТ ПРОВАЛЕН: База данных была скомпрометирована!")
            sys.exit(1)

    except sqlite3.OperationalError:
        print("⚠️ База данных или таблица audit_ledger не найдена.")

if __name__ == "__main__":
    verify_chain()
