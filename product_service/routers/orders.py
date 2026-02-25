from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models
from services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/checkout/")
def checkout(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    # Вся логіка тепер тут 👇
    new_order = OrderService.process_checkout(db, order_data)
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
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return {
        "total": total_orders,
        "items": orders,
        "page": page,
        "pages": (total_orders + limit - 1) // limit # Округлення вгору
    }