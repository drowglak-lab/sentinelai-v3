import asyncio
from core.database import get_db_connection


async def outbox_relay_worker():
    print("🚀 [Outbox Relay] Started listening for events...")
    db = await get_db_connection()

    while True:
        try:
            # Ищем необработанные события
            cursor = await db.execute(
                "SELECT id, aggregate_id, event_type FROM outbox_events WHERE status = 'PENDING' LIMIT 10")
            events = await cursor.fetchall()

            for event in events:
                # ЗДЕСЬ ДОЛЖНА БЫТЬ ОТПРАВКА В KAFKA
                print(
                    f"📨 [Kafka Emulator] Publishing event: {event['event_type']} for Payment: {event['aggregate_id']}")

                # Отмечаем как опубликованное
                await db.execute("UPDATE outbox_events SET status = 'PUBLISHED' WHERE id = ?", (event['id'],))

            if events:
                await db.commit()

        except Exception as e:
            print(f"⚠️ [Outbox Relay] Error: {e}")

        await asyncio.sleep(2)  # Пауза перед следующей проверкой