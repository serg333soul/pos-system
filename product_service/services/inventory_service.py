# FILE: product_service/services/inventory_service.py

from services.inventory_logger import InventoryLogger
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas

# 🔥 Єдиний місток до партій та накладних
from services.supply_client import SupplyClient

class InventoryService:
    
    @staticmethod
    def deduct_fifo(db: Session, entity_type: str, entity_id: int, quantity_needed: float) -> float:
        # Делегуємо роботу з партіями Клієнту Закупівель
        return SupplyClient.deduct_fifo(db, entity_type, entity_id, quantity_needed)

    @staticmethod
    def deduct_manual(db: Session, batch_id: int, quantity_needed: float) -> float:
        return SupplyClient.deduct_manual(db, batch_id, quantity_needed)
    
    @staticmethod
    def adjust_inventory(db: Session, request: schemas.InventoryAdjustRequest):
        # 1. Знаходимо сутність
        target_obj = None
        if request.entity_type == 'ingredient':
            target_obj = db.query(models.Ingredient).get(request.entity_id)
        elif request.entity_type == 'consumable':
            target_obj = db.query(models.Consumable).get(request.entity_id)
        elif request.entity_type == 'product_variant':
            target_obj = db.query(models.ProductVariant).get(request.entity_id)
        elif request.entity_type == 'product':
            target_obj = db.query(models.Product).get(request.entity_id)
            
        if not target_obj:
            raise HTTPException(status_code=404, detail="Сутність не знайдена")
            
        # Рахуємо різницю
        current_qty = target_obj.stock_quantity if target_obj.stock_quantity is not None else 0.0
        difference = request.actual_quantity - current_qty
        
        if difference == 0:
            return {"status": "ok", "message": "Немає змін для збереження"}
            
        transaction_reason = f"Коригування: {request.reason}"
        
        # 2. ДЕЛЕГУЄМО РОБОТУ З ПАРТІЯМИ КЛІЄНТУ
        if request.batch_id:
            SupplyClient.adjust_batch(db, request.batch_id, difference)
        else:
            if difference < 0:
                deduct_amount = abs(difference)
                SupplyClient.deduct_fifo(db, request.entity_type, request.entity_id, deduct_amount)
            else:
                entity_name = getattr(target_obj, 'name', 'Unknown')
                fallback_cost = getattr(target_obj, 'cost_per_unit', 0.0)
                SupplyClient.create_system_adjustment(
                    db, request.entity_type, request.entity_id, entity_name, difference, fallback_cost
                )

        # 3. Оновлюємо загальний залишок сутності на складі
        target_obj.stock_quantity = request.actual_quantity
        db.add(target_obj)
        
        # 4. Логування в Історію Складу
        InventoryLogger.log(
            db=db,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_name=getattr(target_obj, 'name', 'Unknown'),
            balance_before=current_qty,
            balance_after=request.actual_quantity,
            reason=transaction_reason,
            force_change=difference
        )
        
        db.commit()
        return {
            "status": "success", 
            "difference": difference, 
            "new_quantity": request.actual_quantity
        }