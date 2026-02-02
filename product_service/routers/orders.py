from fastapi import APIRouter, Depends
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

@router.get("/", response_model=List[schemas.OrderRead])
def get_orders(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()