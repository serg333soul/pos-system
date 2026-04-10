# FILE: inventory_service/main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import time
import pika
import json
import os

import models
from database import engine, get_db

# --- 1. ЗАХИСТ ПРИ СТАРТІ (Очікування БД) ---
print("⏳ [Inventory API] Очікування бази даних...")
while True:
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ [Inventory API] База даних готова та таблиці створено!")
        break
    except OperationalError:
        print("⏳ База ще завантажується... Повтор через 2 секунди.")
        time.sleep(2)

app = FastAPI(title="POS Inventory API (Warehouse)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. СХЕМИ ДАНИХ (Pydantic) ---
class UnitCreate(BaseModel):
    name: str
    symbol: str

class IngredientCreate(BaseModel):
    name: str
    cost_per_unit: float = 0.0
    stock_quantity: float = 0.0
    unit_id: int
    category_id: Optional[int] = None
    costing_method: str = 'wac'

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    cost_per_unit: Optional[float] = None
    unit_id: Optional[int] = None
    category_id: Optional[int] = None
    costing_method: Optional[str] = None

class ConsumableCreate(BaseModel):
    name: str
    cost_per_unit: float = 0.0
    stock_quantity: int = 0
    unit_id: Optional[int] = None
    category_id: Optional[int] = None
    costing_method: str = 'wac'

class ConsumableUpdate(BaseModel):
    name: Optional[str] = None
    cost_per_unit: Optional[float] = None
    unit_id: Optional[int] = None
    category_id: Optional[int] = None
    costing_method: Optional[str] = None

#--- СХЕМИ ДЛЯ ПОСТАЧАННЯ ---
class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class SupplyItemCreate(BaseModel):
    entity_type: str
    entity_id: int
    #entity_name: str
    quantity: float
    cost_per_unit: float

class SupplyCreate(BaseModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[SupplyItemCreate]
    # Поля для фінансів (поки що опціональні для складу)
    payment_account_id: Optional[int] = None 
    paid_amount: Optional[Decimal] = Decimal('0.00')
# --- 3. МАРШРУТИ (Endpoints) ---

# ОДИНИЦІ ВИМІРУ (Units)
@app.post("/units/")
def create_unit(unit: UnitCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Unit).filter(or_(models.Unit.name == unit.name, models.Unit.symbol == unit.symbol)).first()
    if exists: 
        raise HTTPException(status_code=400, detail="Одиниця існує")
    db_unit = models.Unit(name=unit.name, symbol=unit.symbol)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.get("/units/")
def read_units(db: Session = Depends(get_db)):
    return db.query(models.Unit).all()


# СИРОВИНА (Ingredients)
@app.post("/ingredients/")
def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Ingredient).filter(models.Ingredient.name == ingredient.name).first()
    if exists: 
        raise HTTPException(status_code=400, detail="Інгредієнт з такою назвою вже існує")
    
    new_item = models.Ingredient(**ingredient.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/ingredients/")
def read_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).options(
        joinedload(models.Ingredient.unit)
    ).all()

@app.put("/ingredients/{id}")
def update_ingredient(id: int, item: IngredientUpdate, db: Session = Depends(get_db)):
    db_i = db.query(models.Ingredient).filter(models.Ingredient.id == id).first()
    if not db_i: 
        raise HTTPException(status_code=404)
    
    update_data = item.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_i, key, value)
        
    db.commit()
    db.refresh(db_i)
    return db_i

@app.delete("/ingredients/{id}")
def delete_ingredient(id: int, db: Session = Depends(get_db)):
    db_i = db.query(models.Ingredient).filter(models.Ingredient.id == id).first()
    if not db_i: 
        raise HTTPException(status_code=404)
    db.delete(db_i)
    db.commit()
    return {"status": "deleted"}


# ВИТРАТНІ МАТЕРІАЛИ (Consumables)
@app.post("/consumables/")
def create_consumable(consumable: ConsumableCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Consumable).filter(models.Consumable.name == consumable.name).first()
    if exists: 
        raise HTTPException(status_code=400, detail="Матеріал з такою назвою вже існує")
        
    new_item = models.Consumable(**consumable.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/consumables/")
def read_consumables(db: Session = Depends(get_db)):
    return db.query(models.Consumable).options(
        joinedload(models.Consumable.unit)
    ).all()

@app.put("/consumables/{id}")
def update_consumable(id: int, item: ConsumableUpdate, db: Session = Depends(get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: 
        raise HTTPException(status_code=404)
    
    update_data = item.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_c, key, value)
        
    db.commit()
    db.refresh(db_c)
    return db_c

@app.delete("/consumables/{id}")
def delete_consumable(id: int, db: Session = Depends(get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: 
        raise HTTPException(status_code=404)
    db.delete(db_c)
    db.commit()
    return {"status": "deleted"}


# ІСТОРІЯ РУХУ (Transactions)
@app.get("/history/")
def get_inventory_history(
    entity_type: Optional[str] = None, 
    entity_id: Optional[int] = None, 
    entity_ids: Optional[List[int]] = Query(None), # Для запиту списком (продукт + варіанти)
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    query = db.query(models.InventoryTransaction)
    
    if entity_type:
        query = query.filter(models.InventoryTransaction.entity_type == entity_type)
        
    if entity_ids:
        query = query.filter(models.InventoryTransaction.entity_id.in_(entity_ids))
    elif entity_id:
        query = query.filter(models.InventoryTransaction.entity_id == entity_id)
        
    return query.order_by(desc(models.InventoryTransaction.created_at)).limit(limit).all()

def publish_finance_event(event_type: str, data: dict):
    """Відправляє фінансову подію у RabbitMQ (Асинхронно)"""
    try:
        url = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@rabbitmq:5672/')
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.queue_declare(queue='finance_queue', durable=True)
        
        payload = {"event_type": event_type, **data}
        
        channel.basic_publish(
            exchange='',
            routing_key='finance_queue',
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2) # Persistent
        )
        connection.close()
        print(f"💸 [RabbitMQ] Фінансову подію '{event_type}' успішно відправлено!")
    except Exception as e:
        print(f"⚠️ [RabbitMQ] Помилка відправки фінансів: {e}")

# --- МАРШРУТИ ДЛЯ ПОСТАЧАЛЬНИКІВ ---
@app.post("/suppliers/")
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@app.get("/suppliers/")
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()

# --- МАРШРУТИ ПОСТАЧАННЯ (Supplies) ---
# --- ПОСТАЧАННЯ (Supplies) ---
@app.post("/supplies/")
def create_supply(supply: SupplyCreate, db: Session = Depends(get_db)):
    # 1. Створюємо накладну
    db_supply = models.Supply(
        invoice_number=supply.invoice_number,
        notes=supply.notes,
        supplier_id=supply.supplier_id,
        supplier_name=supply.supplier_name,
        total_cost=0
    )
    db.add(db_supply)
    db.flush()

    total_supply_cost = 0.0

    for item in supply.items:
        item_total = item.quantity * item.cost_per_unit
        total_supply_cost += item_total

        # 🚀 ЛОГІКА ОДЕРЖАННЯ ІМЕНІ (Оскільки фронтенд його не шле)
        current_entity_name = "Невідомо"
        db_ent = None

        if item.entity_type == "ingredient":
            db_ent = db.query(models.Ingredient).filter(models.Ingredient.id == item.entity_id).first()
        elif item.entity_type == "consumable":
            db_ent = db.query(models.Consumable).filter(models.Consumable.id == item.entity_id).first()

        if db_ent:
            current_entity_name = db_ent.name
            # Оновлюємо залишки та середню ціну (WAC)
            old_total = db_ent.stock_quantity * db_ent.cost_per_unit
            new_total = item.quantity * item.cost_per_unit
            new_qty = db_ent.stock_quantity + item.quantity
            if new_qty > 0:
                db_ent.cost_per_unit = (old_total + new_total) / new_qty
            db_ent.stock_quantity = new_qty

        # 2. Додаємо позицію в накладну
        db_item = models.SupplyItem(
            supply_id=db_supply.id,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            entity_name=current_entity_name, # Використовуємо знайдене ім'я
            quantity=item.quantity,
            remaining_quantity=item.quantity,
            cost_per_unit=item.cost_per_unit,
            total_cost=item_total
        )
        db.add(db_item)

        # 3. Записуємо в історію
        transaction = models.InventoryTransaction(
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            entity_name=current_entity_name,
            change_amount=item.quantity,
            balance_after=db_ent.stock_quantity if db_ent else 0,
            reason=f"supply_in_{db_supply.id}"
        )
        db.add(transaction)

    db_supply.total_cost = total_supply_cost
    db.commit()
    db.refresh(db_supply)

    # 🔥 НОВЕ: Відправляємо наказ списати гроші, якщо вказано рахунок оплати
    if supply.payment_account_id and supply.paid_amount and supply.paid_amount > 0:
        publish_finance_event("supply_paid", {
            "supply_id": db_supply.id,
            "account_id": supply.payment_account_id,
            "amount": float(supply.paid_amount),
            "user_id": 1 # Тимчасово, поки не додамо авторизацію
        })

    return db_supply

@app.get("/supplies/")
def get_supplies(db: Session = Depends(get_db)):
    # Підтягуємо і items, і supplier для фронтенду
    return db.query(models.Supply).options(
        joinedload(models.Supply.items), 
        joinedload(models.Supply.supplier)
    ).order_by(desc(models.Supply.created_at)).all()

# ДОДАТИ В КІНЕЦЬ ФАЙЛУ inventory_service/main.py

# --- АЛІАСИ ДЛЯ ФРОНТЕНДУ (Вирішення проблеми 404 для вкладених маршрутів) ---
@app.post("/supplies/suppliers/")
def create_supplier_nested(supplier: SupplierCreate, db: Session = Depends(get_db)):
    return create_supplier(supplier, db)

@app.get("/supplies/suppliers/")
def get_suppliers_nested(db: Session = Depends(get_db)):
    return get_suppliers(db)

@app.get("/supplies/batches/")
def get_available_batches(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    # 1. Знаходимо партії
    batches = db.query(models.SupplyItem).join(models.Supply).filter(
        models.SupplyItem.entity_type == entity_type,
        models.SupplyItem.entity_id == entity_id,
        models.SupplyItem.remaining_quantity > 0
    ).order_by(models.SupplyItem.id.asc()).all()

    # 2. Визначаємо метод списання (WAC/FIFO) 
    costing_method = 'wac'
    if entity_type == 'ingredient':
        obj = db.query(models.Ingredient).filter(models.Ingredient.id == entity_id).first()
        if obj:
            costing_method = getattr(obj, 'costing_method', 'wac')
    elif entity_type == 'consumable':
        obj = db.query(models.Consumable).filter(models.Consumable.id == entity_id).first()
        if obj:
            costing_method = getattr(obj, 'costing_method', 'wac')

    # 3. Точно ті самі ключі (supply_date, quantity_initial), які потрібні Vue.js
    return {
        "costing_method": costing_method,
        "batches": [
            {
                "id": b.id,
                "supply_id": b.supply_id,
                "invoice_number": b.supply.invoice_number if b.supply else "б/н",
                "supply_date": b.supply.created_at if b.supply else None, # 🔥 Правильний ключ
                "quantity_initial": b.quantity, # 🔥 Правильний ключ
                "remaining_quantity": b.remaining_quantity,
                "cost_per_unit": b.cost_per_unit
            } for b in batches
        ]
    }