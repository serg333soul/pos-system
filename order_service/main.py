from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import os
import json
import uuid
from typing import List
from schemas import CartItemCreate, CartItem # Імпортуємо схеми

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

# decode_responses=True економить нам час на декодування байтів
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
CART_KEY = "pos_cart_v2" # Змінимо ключ, щоб не конфліктувати зі старим

@app.get("/")
def read_root():
    return {"message": "Advanced Order Service is running!"}

# --- ОТРИМАТИ КОШИК ---
@app.get("/cart/", response_model=List[CartItem])
def get_cart():
    # Отримуємо всі дані з хешу
    raw_data = r.hgetall(CART_KEY)
    cart_items = []
    
    for key, value in raw_data.items():
        try:
            item = json.loads(value)
            cart_items.append(item)
        except json.JSONDecodeError:
            continue
            
    return cart_items

# --- ДОДАТИ ТОВАР ---
@app.post("/cart/add", response_model=CartItem)
def add_item(item_data: CartItemCreate):
    # Генеруємо унікальний ID для цього запису в кошику
    # Це дозволяє мати два однакових товари з різними модифікаторами
    cart_item_id = str(uuid.uuid4())
    
    new_item = CartItem(
        cart_item_id=cart_item_id,
        **item_data.dict()
    )
    
    # Зберігаємо JSON в Redis: Key=UUID, Value=JSON String
    r.hset(CART_KEY, cart_item_id, json.dumps(new_item.dict()))
    
    return new_item

# --- ЗМІНИТИ КІЛЬКІСТЬ (+/-) ---
@app.post("/cart/{cart_item_id}/update")
def update_quantity(cart_item_id: str, change: int):
    raw_json = r.hget(CART_KEY, cart_item_id)
    if not raw_json:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item = json.loads(raw_json)
    new_qty = item['quantity'] + change
    
    if new_qty <= 0:
        # Якщо кількість <= 0, видаляємо
        r.hdel(CART_KEY, cart_item_id)
        return {"status": "removed", "cart_item_id": cart_item_id}
    else:
        # Оновлюємо кількість
        item['quantity'] = new_qty
        r.hset(CART_KEY, cart_item_id, json.dumps(item))
        return {"status": "updated", "quantity": new_qty}

# --- ВИДАЛИТИ ТОВАР ---
@app.delete("/cart/{cart_item_id}")
def remove_item(cart_item_id: str):
    r.hdel(CART_KEY, cart_item_id)
    return {"status": "removed"}

# --- ОЧИСТИТИ КОШИК ---
@app.delete("/cart/")
def clear_cart():
    r.delete(CART_KEY)
    return {"status": "cleared"}