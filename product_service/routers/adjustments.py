# FILE: product_service/routers/adjustments.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import database
import schemas
from services.inventory_service import InventoryService

router = APIRouter(prefix="/adjustments", tags=["Adjustments"])

@router.post("/")
def adjust_stock(request: schemas.InventoryAdjustRequest, db: Session = Depends(database.get_db)):
    """
    Ендпоінт для ручного коригування залишків (Інвентаризація/Швидка корекція).
    Приймає фактичний залишок та автоматично вираховує і проводить різницю.
    """
    try:
        result = InventoryService.adjust_inventory(db, request)
        return result
    except HTTPException as http_ex:
        db.rollback()
        raise http_ex
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))