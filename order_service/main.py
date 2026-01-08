from fastapi import FastAPI
import redis
import os

app = FastAPI()

# --- ПІДКЛЮЧЕННЯ ДО REDIS ---
# REDIS_HOST - це ім'я контейнера з базою (ми назвемо його 'redis_db' у docker-compose)
# Якщо змінної немає, пробуємо 'localhost' (для локальних тестів без докера)
redis_host = os.getenv("REDIS_HOST", "localhost")

# Створюємо клієнта. db=0 - це стандартна база даних Redis.
r = redis.Redis(host=redis_host, port=6379, db=0)

# --- API ---

# Додати товар у кошик
@app.post("/cart/{item_id}")
def add_to_cart(item_id: int):
    # Redis зберігає дані як "Ключ": "Значення".
    # Ключ буде виглядати як "item:1", "item:5" тощо.
    # Функція incr() збільшує число на 1. Якщо ключа не було - створює його.
    new_count = r.incr(f"item:{item_id}")
    return {"item_id": item_id, "count": new_count, "status": "added"}

# Подивитися весь кошик
@app.get("/cart/")
def get_cart():
    # Шукаємо всі ключі, які починаються на "item:"
    keys = r.keys("item:*")
    cart = {}

    for key in keys:
        # Redis повертає дані у байтах (b'item:1'), тому їх треба декодувати (перетворити в текст)
        key_str = key.decode("utf-8")
        value = r.get(key)
        value_int = int(value)
        cart[key_str] = value_int

    return cart

# Очистити кошик
@app.delete("/cart/")
def clear_cart():
    r.flushdb()
    return {"status": "Cart cleared"}
