# FILE: product_service/services/inventory_client.py

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import models
from services.inventory_logger import InventoryLogger
from services.inventory_service import InventoryService
from services.product_service import ProductService
from services.rabbitmq_client import rabbitmq

class InventoryClient:
    """
    Адаптер (Антикорупційний шар) між модулем Продажів (Orders) та Складом (Inventory).
    У мікросервісній архітектурі цей клас буде робити HTTP-запити до сервісу Inventory.
    """
    @staticmethod
    def process_order_items(db: Session, items: list, transaction_reason: str):
        processed_items = []
        total_order_price = 0.0

        for item in items:
            # 1. ЗАХИЩЕНИЙ СЛОВНИК ЗАМІН
            overrides_map = {}
            if getattr(item, 'consumable_overrides', None):
                for override in item.consumable_overrides:
                    if isinstance(override, dict):
                        orig_id = override.get('original_id')
                        n_id = override.get('new_id')
                    else:
                        orig_id = getattr(override, 'original_id', None)
                        n_id = getattr(override, 'new_id', None)
                        
                    if orig_id is not None:
                        overrides_map[int(orig_id)] = int(n_id) if n_id else None

            # Завантажуємо товар (без with_for_update, бо ми лише читаємо!)
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            price = float(product.price)
            item_name = product.name
            details_list = []

            # --- ЛОГІКА ВАРІАНТІВ ---
            if item.variant_id:
                variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
                if not variant:
                    raise HTTPException(status_code=404, detail=f"Variant {item.variant_id} not found")
                
                item_name = f"{product.name} ({variant.name})"
                price = float(variant.price) 

                # Формуємо пакування (щоб надрукувати в чеку)
                for v_cons in variant.consumables:
                    target_cons_id = v_cons.consumable_id
                    is_replaced = False
                    
                    if target_cons_id in overrides_map:
                        new_id = overrides_map[target_cons_id]
                        if new_id is None or new_id == 0:
                            details_list.append(f"🚫 Без пакування")
                            continue 
                        else:
                            target_cons_id = new_id
                            is_replaced = True

                    cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).first()
                    if cons and is_replaced:
                        details_list.append(f"📦 {cons.name}")

            # --- ЛОГІКА ПРОСТОГО ТОВАРУ ---
            else:
                for p_cons in product.consumables:
                    target_cons_id = p_cons.consumable_id
                    is_replaced = False
                    
                    if target_cons_id in overrides_map:
                        new_id = overrides_map[target_cons_id]
                        if new_id is None or new_id == 0:
                            details_list.append(f"🚫 Відмова від матеріалу") 
                            continue 
                        else:
                            target_cons_id = new_id
                            is_replaced = True

                    cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).first()
                    if cons and is_replaced:
                        details_list.append(f"📦 {cons.name}")

            # --- ДОДАВАННЯ МОДИФІКАТОРІВ ДО ЧЕКА ---
            if getattr(item, 'modifiers', None):
                for modifier in item.modifiers:
                     mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == modifier.modifier_id).first()
                     if mod_ing:
                        details_list.append(f"+ {mod_ing.name}")

            # Формуємо рядок чека
            raw_overrides = getattr(item, 'consumable_overrides', [])
            processed_items.append({
                "product_name": item_name,
                "quantity": item.quantity,
                "price_at_moment": price,
                "details": ", ".join(details_list) if details_list else None,
                "consumable_overrides": [o.model_dump() if hasattr(o, 'model_dump') else o for o in raw_overrides]
            })
            total_order_price += price * item.quantity

        return processed_items, total_order_price
    
    @staticmethod
    def deduct_stock_async(order_id: int, transaction_reason: str, items_data: list):
        """
        Відправляє подію на списання складу в RabbitMQ.
        Викликається ТІЛЬКИ після успішного збереження чека в БД!
        """
        try:
            # Конвертуємо Pydantic-моделі у звичайні словники (бо RabbitMQ приймає лише JSON)
            clean_items = []
            for item in items_data:
                clean_items.append(item.model_dump() if hasattr(item, 'model_dump') else dict(item))

            event_data = {
                "event_type": "deduct_stock",
                "order_id": order_id,
                "transaction_reason": transaction_reason,
                "items": clean_items
            }
            rabbitmq.publish(queue_name="inventory_queue", message=event_data)
        except Exception as e:
            print(f"⚠️ [InventoryClient] Помилка відправки в RabbitMQ (Склад): {e}")
    
    @staticmethod
    def receive_stock(db: Session, entity_type: str, entity_id: int, quantity: float, cost_per_unit: float, reason: str) -> str:
        """
        Метод для оприходування товару на склад (від імені Закупівель).
        Повертає офіційну назву товару (display_name), щоб Закупівлі могли зберегти її в накладній.
        """
        target_obj = None
        
        # 1. Знаходимо сутність
        if entity_type == 'ingredient':
            target_obj = db.query(models.Ingredient).get(entity_id)
        elif entity_type == 'consumable':
            target_obj = db.query(models.Consumable).get(entity_id)
        elif entity_type == 'variant':
            target_obj = db.query(models.ProductVariant)\
                .options(joinedload(models.ProductVariant.product))\
                .filter(models.ProductVariant.id == entity_id).first()
        
        if not target_obj:
            raise HTTPException(status_code=404, detail=f"Сутність {entity_type} ID={entity_id} не знайдена на складі")

        # 2. Формуємо правильну назву
        display_name = getattr(target_obj, 'name', 'Unknown')
        if entity_type == 'variant' and hasattr(target_obj, 'product'):
            display_name = f"{target_obj.product.name} ({target_obj.name})"

        # 3. Перераховуємо собівартість (WAC / FIFO)
        if hasattr(target_obj, 'costing_method') and hasattr(target_obj, 'cost_per_unit'):
            method = getattr(target_obj, 'costing_method', 'wac')
            if method == 'fifo':
                target_obj.cost_per_unit = cost_per_unit
            else:
                current_qty = target_obj.stock_quantity or 0.0
                current_cost = target_obj.cost_per_unit or 0.0
                if current_qty <= 0:
                    target_obj.cost_per_unit = cost_per_unit
                else:
                    old_total = current_qty * current_cost
                    new_total = quantity * cost_per_unit
                    target_obj.cost_per_unit = round((old_total + new_total) / (current_qty + quantity), 2)

        # 4. Оновлюємо фізичний залишок
        old_balance = target_obj.stock_quantity if target_obj.stock_quantity is not None else 0.0
        target_obj.stock_quantity = old_balance + quantity
        db.add(target_obj)
        
        # 5. Пишемо лог складу
        InventoryLogger.log(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=display_name,
            balance_before=old_balance,
            balance_after=target_obj.stock_quantity,
            reason=reason,
            force_change=quantity
        )
        
        return display_name
    
    # ДОДАТИ В КЛАС InventoryClient (у файл inventory_client.py)
    
    @staticmethod
    def get_product_history(db: Session, product_id: int, variant_ids: list):
        from sqlalchemy import or_, and_
        import models
        
        criteria = [
            and_(models.InventoryTransaction.entity_type == "product", models.InventoryTransaction.entity_id == product_id)
        ]
        if variant_ids:
            criteria.append(
                and_(models.InventoryTransaction.entity_type == "product_variant", models.InventoryTransaction.entity_id.in_(variant_ids))
            )
        
        return db.query(models.InventoryTransaction).filter(or_(*criteria)).order_by(models.InventoryTransaction.created_at.desc()).all()
    
    @staticmethod
    def get_costing_method(db: Session, entity_type: str, entity_id: int) -> str:
        """Повертає метод списання (wac/fifo) для сутності, не порушуючи межі доменів"""
        obj = None
        if entity_type == 'ingredient':
            obj = db.query(models.Ingredient).filter(models.Ingredient.id == entity_id).first()
        elif entity_type == 'consumable':
            obj = db.query(models.Consumable).filter(models.Consumable.id == entity_id).first()
        elif entity_type == 'variant':
            obj = db.query(models.ProductVariant).filter(models.ProductVariant.id == entity_id).first()
        
        return getattr(obj, 'costing_method', 'wac') if obj else 'wac'