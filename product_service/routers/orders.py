from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models
from services.order_service import OrderService

# 🔥 ДОДАНО ІМПОРТ ФІНАНСОВОГО СЕРВІСУ
from services import finance_service

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/checkout/")
def checkout(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    # Вся логіка створення замовлення
    new_order = OrderService.process_checkout(db, order_data)
    
    # ==========================================
    # 🔥 ІНТЕГРАЦІЯ З ФІНАНСАМИ (АВТОМАТИЧНИЙ ДОХІД)
    # ==========================================
    try:
        # 1. Шукаємо активну касову зміну
        active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
        shift_id = active_shift.id if active_shift else None

        # 2. Визначаємо рахунок (готівка чи картка)
        # За замовчуванням ставимо 'cash' (готівка). 
        # Якщо у вашій схемі OrderCreate є payment_method, перевіряємо його:
        payment_type = 'cash'
        if hasattr(order_data, 'payment_method') and order_data.payment_method == 'card':
            payment_type = 'bank'
            
        account = db.query(models.Account).filter(
            models.Account.type == payment_type, 
            models.Account.is_active == True
        ).first()

        # 3. Знаходимо категорію доходу
        category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Продаж товарів").first()

        if account:
            # Обробляємо user_id: беремо з замовлення, або ставимо 1 (якщо поки немає авторизації)
            user_id = getattr(new_order, 'user_id', 1)

            tx_data = schemas.TransactionCreate(
                amount=new_order.total_price,  # Сума чека
                account_id=account.id,
                category_id=category.id if category else None,
                shift_id=shift_id,
                user_id=user_id,
                reference_type='order',
                reference_id=new_order.id,
                description=f"Оплата замовлення #{new_order.id}"
            )
            # Створюємо транзакцію в Регістрі!
            finance_service.create_transaction(db, tx_data)
    except Exception as e:
        # Логуємо помилку, але НЕ скасовуємо створення чека (щоб клієнт не чекав через збій у фінансах)
        print(f"⚠️ Помилка створення фінансової транзакції: {e}")

    # Повертаємо ID та пораховану ціну
    return {
        "status": "ok", 
        "order_id": new_order.id, 
        "total_price": new_order.total_price
    }

@router.get("/", response_model=schemas.OrderPaginationResponse)
def get_orders(
    page: int = Query(1, ge=1), 
    limit: int = Query(20, ge=1, le=100), 
    db: Session = Depends(database.get_db)
):
    skip = (page - 1) * limit
    
    # Отримуємо загальну кількість замовлень для розрахунку сторінок
    total_orders = db.query(models.Order).count()
    
    # Отримуємо замовлення для поточної сторінки
    orders = db.query(models.Order)\
        .order_by(models.Order.created_at.desc())\
        .offset(skip).limit(limit).all()
        
    return {
        "items": orders,
        "total": total_orders,
        "page": page,
        "size": limit,
        "pages": (total_orders + limit - 1) // limit
    }

@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(database.get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        return {"error": "Not found"}
    db.delete(order)
    db.commit()
    return {"status": "deleted"}