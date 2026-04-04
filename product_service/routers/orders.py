# FILE: product_service/routers/orders.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models
from services.order_service import OrderService

# 🔥 Звертаємося ТІЛЬКИ через клієнт-адаптер
from services.finance_client import FinanceClient

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/checkout/")
def checkout(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    # 1. Вся логіка створення замовлення (інкапсульована в сервісі)
    new_order = OrderService.process_checkout(db, order_data)
    
    # 2. ДЕЛЕГУЄМО ФІНАНСИ КЛІЄНТУ
    user_id = getattr(new_order, 'user_id', 1)
    # Клієнт сам знайде зміни, рахунки і створить транзакцію, 
    # а у випадку збою - тихо залогує помилку, не ламаючи чек.
    FinanceClient.register_order_income(
        db=db, 
        order_id=new_order.id, 
        total_price=new_order.total_price, 
        payment_method=getattr(order_data, 'payment_method', 'cash'), 
        user_id=user_id
    )

    # 3. Повертаємо результат на фронтенд
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
    total_orders = db.query(models.Order).count()
    
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
    """
    Скасування чека. 
    Викликає сервіс, який відправляє події в RabbitMQ для повернення фінансів та складу.
    """
    # Делегуємо всю складну логіку в OrderService
    success = OrderService.cancel_order(db, order_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Чек не знайдено або неможливо скасувати")
        
    return {"status": "deleted", "message": f"Чек #{order_id} успішно скасовано, ресурси повертаються."}