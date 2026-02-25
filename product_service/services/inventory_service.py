from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

class InventoryService:
    
    @staticmethod
    def deduct_fifo(db: Session, entity_type: str, entity_id: int, quantity_needed: float) -> float:
        """
        Списує товар за методом FIFO (найстаріші партії перші) і повертає ТОЧНУ собівартість списаного.
        """
        if quantity_needed <= 0:
            return 0.0

        # Шукаємо партії з залишком, сортуємо за ID (що еквівалентно хронології)
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

        # Якщо товару не вистачило в партіях (наприклад, продали в мінус)
        if qty_left_to_deduct > 0:
             last_price = batches[-1].cost_per_unit if batches else 0.0
             total_cost_of_deducted += qty_left_to_deduct * last_price

        return total_cost_of_deducted

    @staticmethod
    def deduct_manual(db: Session, batch_id: int, quantity_needed: float) -> float:
        """
        Списує товар із конкретно обраної партії.
        """
        batch = db.query(models.SupplyItem).filter(
            models.SupplyItem.id == batch_id
        ).with_for_update().first()
        
        if not batch:
            raise HTTPException(status_code=404, detail="Партію не знайдено")
            
        if batch.remaining_quantity < quantity_needed:
            raise HTTPException(
                status_code=400, 
                detail=f"Недостатньо залишку в обраній партії (є {batch.remaining_quantity}, треба {quantity_needed})"
            )
            
        batch.remaining_quantity -= quantity_needed
        db.add(batch)
        
        return quantity_needed * batch.cost_per_unit