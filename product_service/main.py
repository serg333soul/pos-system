# FILE: product_service/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session  # 🔥 ДОДАНО: імпорт Session
import database, models
from database import get_db           # 🔥 ДОДАНО: імпорт get_db

# Імпортуємо наші нові модульні роутери
from routers import (
    products, 
    inventory, 
    categories, 
    recipes, 
    processes, 
    orders,
    product_rooms,
    supplies,
    adjustments
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
app.include_router(product_rooms.router)
app.include_router(supplies.router)
app.include_router(adjustments.router) # /finance/accounts, /finance/categories, /finance/transactions, /finance/transfers

@app.get("/")
def read_root():
    return {
        "message": "Product Service is running", 
        "architecture": "Clean Architecture (Router-Service-Repository)",
        "status": "Healthy"
    }

# 🔥 СЛУЖБОВИЙ ЕНДПОІНТ ДЛЯ МІКРОСЕРВІСІВ (Inter-Service API)
@app.get("/orders/history/{customer_id}")
def get_customer_order_history(customer_id: int, db: Session = Depends(get_db)):
    """
    Цей маршрут викликається не фронтендом, а сусіднім мікросервісом customer_service,
    щоб отримати історію чеків конкретного клієнта.
    """
    orders = db.query(models.Order).filter(
        models.Order.customer_id == customer_id
    ).order_by(models.Order.created_at.desc()).all()
    
    return orders