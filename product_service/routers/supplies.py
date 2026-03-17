# FILE: product_service/routers/supplies.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload # Для оптимизации загрузки связанных данных
from typing import List
import models
import schemas
import database
from services.supply_service import SupplyService

from services import finance_service # 🔥 Імпорт фінансового сервісу для інтеграції з транзакціями

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
    # 1. Зберігаємо накладну і всі товари через ваш існуючий сервіс
    new_supply = SupplyService.create_supply(db, data)
    
    # ==========================================
    # 🔥 ІНТЕГРАЦІЯ З ФІНАНСАМИ (АВТОМАТИЧНА ВИТРАТА)
    # ==========================================
    # Перевіряємо, чи передали з фронтенду рахунок для оплати та суму
    payment_account_id = getattr(data, 'payment_account_id', None)
    paid_amount = getattr(data, 'paid_amount', 0)
    
    if payment_account_id and paid_amount > 0:
        try:
            # Шукаємо активну зміну
            active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
            shift_id = active_shift.id if active_shift else None
            
            # Шукаємо категорію
            category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Закупівля товару").first()
            
            # Обробляємо user_id: беремо з постачання, або ставимо 1
            user_id = getattr(new_supply, 'user_id', 1)

            tx_data = schemas.TransactionCreate(
                amount=-abs(paid_amount),  # 🔥 ОБОВ'ЯЗКОВО МІНУС (це витрата з рахунку!)
                account_id=payment_account_id,
                category_id=category.id if category else None,
                shift_id=shift_id,
                user_id=user_id,
                reference_type='supply',
                reference_id=new_supply.id,
                description=f"Оплата постачання #{new_supply.id} від постачальника"
            )
            # Створюємо транзакцію списання коштів!
            finance_service.create_transaction(db, tx_data)
        except Exception as e:
            # Логуємо помилку, але постачання все одно зберігається
            print(f"⚠️ Помилка створення витратної транзакції: {e}")

    return new_supply

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