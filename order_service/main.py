from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "pos_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# decode_responses=True повертає строки
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
CART_KEY = "cart"

@app.get("/")
def read_root():
    return {"message": "Order Service is running!"}

# --- ВИПРАВЛЕНА ФУНКЦІЯ ---
@app.get("/cart/")
def get_cart():
    raw_cart = r.hgetall(CART_KEY)
    
    # Ми формуємо Словник (Dictionary), а не список
    # Було: {"item:9": "2"} -> Стане: {"9": 2}
    clean_cart = {}
    
    for key, value in raw_cart.items():
        try:
            # key = "item:9" -> parts = ["item", "9"]
            parts = key.split(":")
            if len(parts) == 2 and parts[0] == "item":
                item_id = parts[1] # Залишаємо як стрічку "9", бо JSON ключі завжди стрічки
                quantity = int(value)
                
                clean_cart[item_id] = quantity
        except ValueError:
            continue

    # Результат: {"9": 2, "14": 1}
    return clean_cart

@app.post("/cart/{item_id}")
def add_item(item_id: int):
    r.hincrby(CART_KEY, f"item:{item_id}", 1)
    return {"status": "added", "id": item_id}

@app.post("/cart/{item_id}/decrease")
def decrease_item(item_id: int):
    key = f"item:{item_id}"
    new_qty = r.hincrby(CART_KEY, key, -1)
    if new_qty <= 0:
        r.hdel(CART_KEY, key)
    return {"status": "decreased", "id": item_id, "qty": new_qty}

@app.delete("/cart/{item_id}")
def remove_item(item_id: int):
    key = f"item:{item_id}"
    r.hdel(CART_KEY, key)
    return {"status": "removed", "id": item_id}

@app.delete("/cart/")
def clear_cart():
    r.delete(CART_KEY)
    return {"status": "cart cleared"}