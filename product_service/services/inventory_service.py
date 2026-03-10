from services.inventory_logger import InventoryLogger
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas

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
        
        # 2. Обробка за КОНКРЕТНОЮ ПАРТІЄЮ (Ручний вибір для FIFO)
        if request.batch_id:
            batch = db.query(models.SupplyItem).filter(models.SupplyItem.id == request.batch_id).with_for_update().first()
            if not batch:
                raise HTTPException(status_code=404, detail="Партія не знайдена")
                
            if difference < 0:
                # Нестача: списуємо з вибраної партії
                deduct_amount = abs(difference)
                if batch.remaining_quantity < deduct_amount:
                    raise HTTPException(status_code=400, detail="У вибраній партії недостатньо залишку для такого списання")
                batch.remaining_quantity -= deduct_amount
            else:
                # Лишок: додаємо знайдений товар у вибрану партію
                batch.remaining_quantity += difference
                batch.quantity += difference # Оновлюємо початкову кількість партії
            db.add(batch)
            
        # 3. Обробка БЕЗ партії (Автоматичне розподілення)
        else:
            if difference < 0:
                deduct_amount = abs(difference)
                # 🔥 ВИПРАВЛЕННЯ: Списуємо з найстаріших партій ЗАВЖДИ (і для FIFO, і для WAC), 
                # щоб сума в партіях дорівнювала stock_quantity
                InventoryService.deduct_fifo(db, request.entity_type, request.entity_id, deduct_amount)
            else:
                # 🔥 ВИПРАВЛЕННЯ: Якщо це Лишок - створюємо НОВУ системну партію ЗАВЖДИ 
                # (і для FIFO, і для WAC), щоб ця кількість з'явилась у випадаючих списках
                
                # Шукаємо останню ціну закупівлі цього товару для адекватної оцінки лишку
                last_batch = db.query(models.SupplyItem).filter(
                    models.SupplyItem.entity_type == request.entity_type,
                    models.SupplyItem.entity_id == request.entity_id
                ).order_by(models.SupplyItem.id.desc()).first()
                
                cost_unit = last_batch.cost_per_unit if last_batch else getattr(target_obj, 'cost_per_unit', 0.0)
                
                # Створюємо системну поставку-документ
                system_supply = models.Supply(
                    notes=f"Системна накладна (Коригування: {request.reason})",
                    total_cost=difference * cost_unit
                )
                db.add(system_supply)
                db.flush() # робимо flush, щоб отримати system_supply.id
                
                # Створюємо сам рядок партії
                system_supply_item = models.SupplyItem(
                    supply_id=system_supply.id,
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    entity_name=getattr(target_obj, 'name', 'Unknown'),
                    quantity=difference,
                    remaining_quantity=difference,
                    cost_per_unit=cost_unit,
                    total_cost=difference * cost_unit
                )
                db.add(system_supply_item)

        # 4. Оновлюємо загальний залишок сутності
        target_obj.stock_quantity = request.actual_quantity
        db.add(target_obj)
        
        # 5. Логування в Історію
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