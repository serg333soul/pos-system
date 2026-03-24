# FILE: product_service/routers/supplies.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import models, schemas, database

from services.supply_service import SupplyService
from services.finance_client import FinanceClient

router = APIRouter(prefix="/supplies", tags=["Supplies"])

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
    new_supply = SupplyService.create_supply(db, data)

    # 🔥 ДЕЛЕГУЄМО ФІНАНСИ КЛІЄНТУ (Ізоляція доменів збережена)
    payment_account_id = getattr(data, 'payment_account_id', None)
    paid_amount = getattr(data, 'paid_amount', 0)
    
    if payment_account_id and paid_amount > 0:
        user_id = getattr(data, 'user_id', 1) 
        FinanceClient.register_supply_expense(
            db=db, 
            supply_id=new_supply.id, 
            total_cost=float(paid_amount), 
            account_id=payment_account_id, 
            user_id=user_id
        )

    return new_supply

@router.get("/", response_model=List[schemas.SupplyResponse])
def get_supplies(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    return db.query(models.Supply)\
        .options(joinedload(models.Supply.items), joinedload(models.Supply.supplier))\
        .order_by(models.Supply.created_at.desc())\
        .offset(skip).limit(limit).all()

# =========================================================================
# 🔥 ВІДНОВЛЕНО ОРИГІНАЛЬНИЙ МАРШРУТ (Саме його чекає ваш Vue.js фронтенд!)
# =========================================================================
@router.get("/batches/")
def get_available_batches(
    entity_type: str = Query(..., description="Тип: ingredient, consumable, variant, product"),
    entity_id: int = Query(..., description="ID конкретного товару/інгредієнта"),
    db: Session = Depends(database.get_db)
):
    """
    Повертає список активних партій з деталями накладної та методом списання.
    """
    # 1. Отримуємо активні партії (залишок > 0)
    batches = db.query(models.SupplyItem)\
        .options(joinedload(models.SupplyItem.supply))\
        .filter(
            models.SupplyItem.entity_type == entity_type,
            models.SupplyItem.entity_id == entity_id,
            models.SupplyItem.remaining_quantity > 0  # 🔥 Відновлено фільтр для АКТИВНИХ партій
        ).order_by(models.SupplyItem.id.asc()).all()

    # 2. Визначаємо метод списання (WAC/FIFO) 
    costing_method = 'wac'
    if entity_type == 'ingredient':
        obj = db.query(models.Ingredient).filter(models.Ingredient.id == entity_id).first()
        costing_method = getattr(obj, 'costing_method', 'wac')
    elif entity_type == 'consumable':
        obj = db.query(models.Consumable).filter(models.Consumable.id == entity_id).first()
        costing_method = getattr(obj, 'costing_method', 'wac')

    # 3. Точно ті самі ключі (supply_date, quantity_initial), які потрібні Vue.js
    return {
        "costing_method": costing_method,
        "batches": [
            {
                "id": b.id,
                "supply_id": b.supply_id,
                "invoice_number": b.supply.invoice_number if b.supply else "б/н",
                "supply_date": b.supply.created_at if b.supply else None,
                "quantity_initial": b.quantity,
                "remaining_quantity": b.remaining_quantity,
                "cost_per_unit": b.cost_per_unit
            } for b in batches
        ]
    }

@router.get("/{supply_id}", response_model=schemas.SupplyResponse)
def get_supply(supply_id: int, db: Session = Depends(database.get_db)):
    supply = db.query(models.Supply).filter(models.Supply.id == supply_id).first()
    if not supply:
        raise HTTPException(status_code=404, detail="Накладну не знайдено")
    return supply