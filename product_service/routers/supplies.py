# FILE: product_service/routers/supplies.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload # Для оптимизации загрузки связанных данных
from typing import List
import models
import schemas
import database
from services.supply_service import SupplyService

router = APIRouter(
    prefix="/supplies",
    tags=["Supplies"]
)

@router.get("/suppliers/", response_model=List[schemas.Supplier])
def get_suppliers(db: Session = Depends(database.get_db)):
    return db.query(models.Supplier).order_by(models.Supplier.name).all()

@router.post("/suppliers/", response_model=schemas.Supplier)
def create_supplier(data: schemas.SupplierCreate, db: Session = Depends(database.get_db)):
    db_supplier = models.Supplier(**data.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.post("/", response_model=schemas.SupplyResponse)
def create_supply(data: schemas.SupplyCreate, db: Session = Depends(database.get_db)):
    """
    Створює нове постачання (накладну), формує партії та перераховує собівартість.
    """
    return SupplyService.create_supply(db, data)

@router.get("/", response_model=List[schemas.SupplyResponse])
def get_supplies(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    # 🔥 Використовуємо joinedload для миттєвого завантаження позицій накладної
    return db.query(models.Supply)\
        .options(
            joinedload(models.Supply.items),
            joinedload(models.Supply.supplier) # Також завантажуємо об'єкт постачальника
        )\
        .order_by(models.Supply.created_at.desc())\
        .offset(skip).limit(limit).all()

@router.get("/batches/")
def get_available_batches(
    entity_type: str = Query(..., description="Тип: ingredient, consumable, variant, product"),
    entity_id: int = Query(..., description="ID конкретного товару/інгредієнта"),
    db: Session = Depends(database.get_db)
):
    """
    Повертає список активних партій з деталями накладної та методом списання.
    """
    # 1. Отримуємо активні партії (залишок > 0) з підвантаженням даних про постачання [1, 2]
    batches = db.query(models.SupplyItem)\
        .options(joinedload(models.SupplyItem.supply))\
        .filter(
            models.SupplyItem.entity_type == entity_type,
            models.SupplyItem.entity_id == entity_id,
            models.SupplyItem.remaining_quantity > 0
        ).order_by(models.SupplyItem.id.asc()).all() # FIFO: найстаріші спочатку [3]

    # 2. Визначаємо метод списання (WAC/FIFO) для даної сутності [4, 5]
    costing_method = 'wac'
    if entity_type == 'ingredient':
        obj = db.query(models.Ingredient).filter(models.Ingredient.id == entity_id).first()
        costing_method = getattr(obj, 'costing_method', 'wac')
    elif entity_type == 'consumable':
        obj = db.query(models.Consumable).filter(models.Consumable.id == entity_id).first()
        costing_method = getattr(obj, 'costing_method', 'wac')

    # 3. Формуємо розширену відповідь для фронтенду
    return {
        "costing_method": costing_method,
        "batches": [
            {
                "id": b.id,
                "supply_id": b.supply_id,
                "invoice_number": b.supply.invoice_number if b.supply else "б/н", # Номер накладної [6]
                "supply_date": b.supply.created_at if b.supply else None,
                "quantity_initial": b.quantity,
                "remaining_quantity": b.remaining_quantity,
                "cost_per_unit": b.cost_per_unit
            } for b in batches
        ]
    }