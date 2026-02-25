from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas
from services.inventory_logger import InventoryLogger

class SupplyService:
    @staticmethod
    def create_supply(db: Session, data: schemas.SupplyCreate):
        # 1. Знаходимо ім'я постачальника, якщо передано тільки ID
        name_to_save = data.supplier_name
        if data.supplier_id and not name_to_save:
            supplier = db.query(models.Supplier).filter(models.Supplier.id == data.supplier_id).first()
            if supplier:
                name_to_save = supplier.name

        # 2. Створюємо шапку накладної
        supply = models.Supply(
            supplier_id=data.supplier_id,
            supplier_name=name_to_save, # 🔥 Тепер ім'я точно буде
            invoice_number=data.invoice_number,
            notes=data.notes,
            total_cost=0
        )
        db.add(supply)
        db.flush() # Отримуємо supply.id

        total_supply_cost = 0.0

        for item in data.items:
            line_total = item.quantity * item.cost_per_unit
            total_supply_cost += line_total
            
            # 2. Знаходимо сутність (куди додаємо залишок)
            target_obj = None
            if item.entity_type == 'ingredient':
                target_obj = db.query(models.Ingredient).get(item.entity_id)
            elif item.entity_type == 'consumable':
                target_obj = db.query(models.Consumable).get(item.entity_id)
            elif item.entity_type == 'variant':
                # 🔥 Senior Tip: Використовуємо joinedload, щоб відразу отримати назву батьківського товару
                target_obj = db.query(models.ProductVariant)\
                    .options(joinedload(models.ProductVariant.product))\
                    .filter(models.ProductVariant.id == item.entity_id).first()
            
            if not target_obj:
                raise HTTPException(status_code=404, detail=f"Сутність {item.entity_type} ID={item.entity_id} не знайдена")

            # --- 🔥 ПОКРАЩЕННЯ: Формуємо інформативну назву для історії ---
            display_name = getattr(target_obj, 'name', 'Unknown')
            
            if item.entity_type == 'variant' and hasattr(target_obj, 'product'):
                # Замість просто "XL" запишемо "Кава Лате (XL)"
                display_name = f"{target_obj.product.name} ({target_obj.name})"

            # 3. Створюємо ПАРТІЮ (SupplyItem)
            db_item = models.SupplyItem(
                supply_id=supply.id,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                entity_name=display_name, # Тепер тут буде коректна назва [1]
                quantity=item.quantity,
                remaining_quantity=item.quantity, # Для FIFO/Manual Batch [2]
                cost_per_unit=item.cost_per_unit,
                total_cost=line_total
            )
            db.add(db_item)

            # 4. Перераховуємо середньозважену ціну (WAC) або оновлюємо ціну за останньою закупівлею (FIFO)
            if hasattr(target_obj, 'costing_method') and hasattr(target_obj, 'cost_per_unit'):
                method = getattr(target_obj, 'costing_method', 'wac')
    
                if method == 'fifo':
                    # Для FIFO в основній картці відображаємо ціну ОСТАННЬОЇ закупівлі
                    # (Це дає розуміння актуальної ринкової ціни)
                    target_obj.cost_per_unit = item.cost_per_unit
                else:
                    # Для WAC використовуємо формулу середньозваженої ціни
                    current_qty = target_obj.stock_quantity or 0.0
                    current_cost = target_obj.cost_per_unit or 0.0
        
                    if current_qty <= 0:
                        target_obj.cost_per_unit = item.cost_per_unit
                    else:
                        old_total = current_qty * current_cost
                        new_total = item.quantity * item.cost_per_unit
                        target_obj.cost_per_unit = round((old_total + new_total) / (current_qty + item.quantity), 2)
            
            # 5. Оновлюємо фізичний залишок на картці товару
            old_balance = target_obj.stock_quantity if target_obj.stock_quantity is not None else 0.0
            target_obj.stock_quantity = old_balance + item.quantity
            
            # 6. Записуємо в історію
            InventoryLogger.log(
                db=db,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                entity_name=db_item.entity_name,
                balance_before=old_balance,      # Передаємо старий залишок
                balance_after=target_obj.stock_quantity, # Новий залишок
                reason=f"Постачання #{supply.id}",
                force_change=item.quantity       # Вказуємо зміну (плюсове значення) [1, 3]
            )

        supply.total_cost = total_supply_cost
        db.commit()
        db.refresh(supply)
        return supply