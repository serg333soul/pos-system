# FILE: product_service/services/inventory_client.py

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import models
import requests
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
        Відправляє подію на списання складу в RabbitMQ (Патерн Bill of Materials).
        Моноліт сам розпаковує товари до рівня інгредієнтів і матеріалів!
        """
        from database import SessionLocal
        import models
        from services.rabbitmq_client import rabbitmq
        
        db = SessionLocal() # Відкриваємо коротку сесію для читання рецептів
        try:
            bom_ingredients = {} # {id_інгредієнта: загальна_кількість}
            bom_consumables = {} # {id_матеріалу: загальна_кількість}
            sold_items_for_history = [] # Список для запису в історію транзакцій складу
            product_names = []

            for item in items_data:
                # Підтримуємо і словники, і Pydantic моделі
                item_dict = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
                p_id = item_dict.get("product_id")
                v_id = item_dict.get("variant_id")
                qty = float(item_dict.get("quantity", 1.0))

                product = db.query(models.Product).filter(models.Product.id == p_id).first()
                if not product: continue

                # 🌟 Формуємо назву: "Назва товару (Назва варіанту) xКількість"
                variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == v_id).first() if v_id else None
                item_name = product.name
                if variant and variant.name:
                    item_name += f" ({variant.name})"
                product_names.append(f"{item_name} x{int(qty) if qty.is_integer() else qty}")

                # 🌟 ЗБИРАЄМО ДАНІ ПРО ПРОДАНИЙ ТОВАР/ВАРІАНТ ДЛЯ ІСТОРІЇ
                current_stock = (variant.stock_quantity if variant else product.stock_quantity) or 0.0
                sold_items_for_history.append({
                    "type": "product_variant" if v_id else "product",
                    "id": v_id if v_id else p_id,
                    "name": item_name,
                    "qty": qty,
                    "new_stock": current_stock - qty
                })

                recipe = None
                target_weight = 0.0
                
                # 1. ЯКЩО Є ВАРІАНТ (S, M, L)
                if v_id:
                    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == v_id).first()
                    if variant:
                        target_weight = variant.output_weight or 0.0
                        if variant.master_recipe_id:
                            recipe = variant.master_recipe
                            
                        # 🔥 НОВЕ: Розпаковуємо витратні матеріали ВАРІАНТУ (стаканчики, кришки)
                        for vc in variant.consumables:
                            total_qty = vc.quantity * qty
                            bom_consumables[vc.consumable_id] = bom_consumables.get(vc.consumable_id, 0) + total_qty
                            
                        # 🔥 НОВЕ: Розпаковуємо інгредієнти ВАРІАНТУ (якщо є)
                        for vi in variant.ingredients:
                            total_qty = vi.quantity * qty
                            bom_ingredients[vi.ingredient_id] = bom_ingredients.get(vi.ingredient_id, 0) + total_qty
                
                # 2. ЯКЩО ЦЕ ПРОСТИЙ ТОВАР (БЕЗ ВАРІАНТІВ)
                if not recipe and product.master_recipe_id:
                    recipe = product.master_recipe
                    target_weight = product.output_weight or 0.0

                # 3. Розпаковуємо інгредієнти з РЕЦЕПТУ (з правильними відсотками)
                if recipe:
                    for ri in recipe.items:
                        if getattr(ri, 'is_percentage', False):
                            amount_per_item = (ri.quantity / 100.0) * target_weight
                            total_qty = amount_per_item * qty
                        else:
                            total_qty = ri.quantity * qty
                            
                        bom_ingredients[ri.ingredient_id] = bom_ingredients.get(ri.ingredient_id, 0) + total_qty

                # 4. Розпаковуємо базові інгредієнти ПРОДУКТУ
                for pi in product.ingredients:
                    total_qty = pi.quantity * qty
                    bom_ingredients[pi.ingredient_id] = bom_ingredients.get(pi.ingredient_id, 0) + total_qty

                # 5. Розпаковуємо базові витратні матеріали ПРОДУКТУ
                for pc in product.consumables:
                    total_qty = pc.quantity * qty
                    bom_consumables[pc.consumable_id] = bom_consumables.get(pc.consumable_id, 0) + total_qty

            # 🌟 ФОРМУЄМО ДЕТАЛЬНУ ПРИЧИНУ: "Продаж #123: Лате (L) x1, Еспресо x2"
            detailed_reason = f"Продаж чеку #{order_id}: {', '.join(product_names)}"

            # Формуємо чітку команду для Складу
            payload = {
                "event_type": "deduct_bom",
                "order_id": order_id,
                "reason": transaction_reason,
                "ingredients": [{"id": k, "qty": v} for k, v in bom_ingredients.items()],
                "consumables": [{"id": k, "qty": v} for k, v in bom_consumables.items()],
                "sold_items": sold_items_for_history
            }
            rabbitmq.publish(queue_name="inventory_queue", message=payload)
            print(f"✅ [InventoryClient] BoM для чека #{order_id} успішно відправлено на склад!")
            
        except Exception as e:
            print(f"⚠️ [InventoryClient] Помилка формування BoM: {e}")
        finally:
            db.close()
    
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
    
    # 🔥 НОВИЙ МЕТОД: Швидко стягує всі залишки зі Складу
    @staticmethod
    def get_all_stocks():
        try:
            ings = requests.get("http://inventory_api:8004/ingredients/", timeout=2).json()
            cons = requests.get("http://inventory_api:8004/consumables/", timeout=2).json()
            
            ing_stock = {i["id"]: i.get("stock_quantity", 0) for i in ings if "id" in i}
            con_stock = {c["id"]: c.get("stock_quantity", 0) for c in cons if "id" in c}
            return ing_stock, con_stock
        except Exception as e:
            print(f"⚠️ [InventoryClient] Не вдалося отримати залишки зі складу: {e}")
            return {}, {}
        
    @staticmethod
    def refund_stock_async(order_id: int, items_data: list):
        """Відправляє подію на ПОВЕРНЕННЯ розпакованих інгредієнтів (Reverse BoM)"""
        from database import SessionLocal
        import models
        from services.rabbitmq_client import rabbitmq
        
        db = SessionLocal()
        try:
            bom_ingredients = {}
            bom_consumables = {}

            # Розпаковуємо всі рецепти точно так само, як при продажі
            for item in items_data:
                p_id = getattr(item, 'product_id', None)
                v_id = getattr(item, 'variant_id', None)
                qty = getattr(item, 'quantity', 1.0)

                product = db.query(models.Product).filter(models.Product.id == p_id).first()
                if not product: continue

                variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == v_id).first() if v_id else None
                recipe = variant.master_recipe if (variant and variant.master_recipe_id) else (product.master_recipe if product.master_recipe_id else None)
                target_weight = variant.output_weight if variant else (product.output_weight if product else 0.0)

                if recipe:
                    for ri in recipe.items:
                        amount = (ri.quantity / 100.0) * target_weight if getattr(ri, 'is_percentage', False) else ri.quantity
                        bom_ingredients[ri.ingredient_id] = bom_ingredients.get(ri.ingredient_id, 0) + (amount * qty)

                if variant:
                    for vi in variant.ingredients: bom_ingredients[vi.ingredient_id] = bom_ingredients.get(vi.ingredient_id, 0) + (vi.quantity * qty)
                    for vc in variant.consumables: bom_consumables[vc.consumable_id] = bom_consumables.get(vc.consumable_id, 0) + (vc.quantity * qty)
                
                for pi in product.ingredients: bom_ingredients[pi.ingredient_id] = bom_ingredients.get(pi.ingredient_id, 0) + (pi.quantity * qty)
                for pc in product.consumables: bom_consumables[pc.consumable_id] = bom_consumables.get(pc.consumable_id, 0) + (pc.quantity * qty)

            payload = {
                "event_type": "refund_bom",
                "order_id": order_id,
                "reason": f"Скасування чека #{order_id}",
                "ingredients": [{"id": k, "qty": v} for k, v in bom_ingredients.items()],
                "consumables": [{"id": k, "qty": v} for k, v in bom_consumables.items()]
            }
            rabbitmq.publish(queue_name="inventory_queue", message=payload)
        finally:
            db.close()  