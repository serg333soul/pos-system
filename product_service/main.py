# FILE: product_service/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database, models

# Імпортуємо наші нові модульні роутери
from routers import (
    products, 
    inventory, 
    categories, 
    recipes, 
    processes, 
    customers, 
    orders
)

app = FastAPI(title="HITS POS Product Service", version="2.0.0")

# Налаштування CORS (дозволяємо фронтенду стукатись сюди)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Створення таблиць в БД при старті (якщо їх немає)
models.Base.metadata.create_all(bind=database.engine)

# --- ПІДКЛЮЧЕННЯ РОУТЕРІВ ---
# Тепер кожен файл відповідає за свій шматок URL
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(inventory.router)   # /ingredients, /consumables, /units
app.include_router(categories.router)
app.include_router(recipes.router)
app.include_router(processes.router)
app.include_router(customers.router)

@app.get("/")
def read_root():
    return {
        "message": "Product Service is running", 
        "architecture": "Clean Architecture (Router-Service-Repository)",
        "status": "Healthy"
    }