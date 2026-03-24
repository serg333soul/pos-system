# FILE: product_service/services/supply_client.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

class SupplyClient:
    """
    Адаптер для зв'язку між Складом (Inventory) та Закупівлями (Supply).
    Допомагає складу працювати з партіями (SupplyItem) без прямого доступу до чужої БД.
    """

    @staticmethod
    def deduct_fifo(db: Session, entity_type: str, entity_id: int, quantity_needed: float) -> float:
        if quantity_needed <= 0:
            return 0.0

        batches = db.query(models.SupplyItem).filter(
            models.SupplyItem.entity_type == entity_type,
            models.SupplyItem.entity_id == entity_id,
            models.SupplyItem.remaining_quantity > 0
        ).order_by(models.SupplyItem.id.asc()).with_for_update().all()

        total_cost_of_deducted = 0.0
        qty_left_to_deduct = quantity_needed

        for batch in batches:
            if qty_left_to_deduct <= 0:
                break
            take_from_batch = min(batch.remaining_quantity, qty_left_to_deduct)
            total_cost_of_deducted += take_from_batch * batch.cost_per_unit
            
            batch.remaining_quantity -= take_from_batch
            qty_left_to_deduct -= take_from_batch
            db.add(batch)

        if qty_left_to_deduct > 0:
             last_price = batches[-1].cost_per_unit if batches else 0.0
             total_cost_of_deducted += qty_left_to_deduct * last_price

        return total_cost_of_deducted

    @staticmethod
    def deduct_manual(db: Session, batch_id: int, quantity_needed: float) -> float:
        batch = db.query(models.SupplyItem).filter(models.SupplyItem.id == batch_id).with_for_update().first()
        if not batch:
            raise HTTPException(status_code=404, detail="Партію не знайдено")
        if batch.remaining_quantity < quantity_needed:
            raise HTTPException(status_code=400, detail=f"Недостатньо залишку в обраній партії (є {batch.remaining_quantity}, треба {quantity_needed})")
            
        batch.remaining_quantity -= quantity_needed
        db.add(batch)
        return quantity_needed * batch.cost_per_unit

    @staticmethod
    def adjust_batch(db: Session, batch_id: int, difference: float):
        batch = db.query(models.SupplyItem).filter(models.SupplyItem.id == batch_id).with_for_update().first()
        if not batch:
            raise HTTPException(status_code=404, detail="Партія не знайдена")
            
        if difference < 0:
            deduct_amount = abs(difference)
            if batch.remaining_quantity < deduct_amount:
                raise HTTPException(status_code=400, detail="У вибраній партії недостатньо залишку для такого списання")
            batch.remaining_quantity -= deduct_amount
        else:
            batch.remaining_quantity += difference
            batch.quantity += difference 
        db.add(batch)

    @staticmethod
    def create_system_adjustment(db: Session, entity_type: str, entity_id: int, entity_name: str, difference: float, fallback_cost: float):
        last_batch = db.query(models.SupplyItem).filter(
            models.SupplyItem.entity_type == entity_type,
            models.SupplyItem.entity_id == entity_id
        ).order_by(models.SupplyItem.id.desc()).first()
        
        cost_unit = last_batch.cost_per_unit if last_batch else fallback_cost
        
        system_supply = models.Supply(
            notes=f"Системна накладна (Коригування залишків)",
            total_cost=difference * cost_unit
        )
        db.add(system_supply)
        db.flush() 
        
        system_supply_item = models.SupplyItem(
            supply_id=system_supply.id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            quantity=difference,
            remaining_quantity=difference,
            cost_per_unit=cost_unit,
            total_cost=difference * cost_unit
        )
        db.add(system_supply_item)