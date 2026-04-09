import redis
import sys

# Подключаемся к Redis (используем localhost, так как запускаем извне Docker)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def set_mode(mode, rate=1.0):
    if mode not in ["NORMAL", "FROZEN", "READ_ONLY", "RAMP_UP"]:
        print("❌ Неверный режим!")
        return

    # Устанавливаем флаги в Redis
    r.set("sentinel:mode", mode)
    r.set("sentinel:rate_limit", str(rate))
    
    # Публикуем сообщение для мгновенной реакции L1
    r.publish("sentinel:alerts", f"MODE_CHANGE:{mode}")
    
    print(f"✅ Система переведена в режим: {mode} (Пропуск: {rate*100}%)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python admin_panel.py [NORMAL|FROZEN|READ_ONLY|RAMP_UP] [rate]")
    else:
        mode = sys.argv[1].upper()
        rate = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        set_mode(mode, rate)
