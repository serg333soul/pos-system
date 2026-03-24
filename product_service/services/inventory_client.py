# FILE: product_service/services/inventory_client.py

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import models
from services.inventory_logger import InventoryLogger
from services.inventory_service import InventoryService
from services.product_service import ProductService

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
            print(f"   -> [InventoryClient] Перевірка товару ID: {item.product_id} (Варіант: {item.variant_id})")

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

            # Завантажуємо товар (блокуємо для безпеки)
            product = db.query(models.Product).filter(
                models.Product.id == item.product_id
            ).with_for_update().first()
            
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            price = float(product.price)
            item_name = product.name
            details_list = []

            # --- ЛОГІКА ВАРІАНТІВ ---
            if item.variant_id:
                variant = db.query(models.ProductVariant).filter(
                    models.ProductVariant.id == item.variant_id
                ).with_for_update().first()
                
                if not variant:
                    raise HTTPException(status_code=404, detail=f"Variant {item.variant_id} not found")
                
                item_name = f"{product.name} ({variant.name})"
                price = float(variant.price) 

                balance_before = variant.stock_quantity if variant.stock_quantity is not None else 0.0
                should_deduct_physical = (variant.stock_quantity is not None) and (not variant.master_recipe_id)
                
                if should_deduct_physical:
                    if variant.stock_quantity < item.quantity:
                        raise HTTPException(status_code=400, detail=f"Недостатньо залишку: {variant.name}")
                    
                    if getattr(item, 'batch_id', None):
                        InventoryService.deduct_manual(db, item.batch_id, item.quantity)
                    else:
                        InventoryService.deduct_fifo(db, 'variant', variant.id, item.quantity)
                    
                    variant.stock_quantity -= item.quantity

                    InventoryLogger.log(
                        db, entity_type="product_variant", entity_id=variant.id, entity_name=item_name,
                        balance_before=balance_before, balance_after=variant.stock_quantity,
                        reason=transaction_reason, force_change=-item.quantity 
                    )

                if variant.master_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == variant.master_recipe_id).first()
                    if recipe:
                        output_w = variant.output_weight or 1
                        for r_item in recipe.items:
                            ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                            if ing:
                                deduction = (r_item.quantity / 100) * output_w * item.quantity if r_item.is_percentage else r_item.quantity * item.quantity
                                i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                
                                InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                                if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                ing.stock_quantity -= deduction
                                db.add(ing)
                                
                                InventoryLogger.log(
                                    db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                                    balance_before=i_old, balance_after=ing.stock_quantity,
                                    reason=transaction_reason, force_change=-deduction
                                )

                        new_calculated_balance = ProductService.calculate_max_possible_stock(db, variant.id)
                        InventoryLogger.log(
                            db, entity_type="product_variant", entity_id=variant.id, entity_name=item_name,
                            balance_before=balance_before, balance_after=new_calculated_balance,
                            reason=transaction_reason, force_change=-item.quantity
                        )

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

                    cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).with_for_update().first()
                    if cons:
                        c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                        qty_to_deduct = v_cons.quantity * item.quantity
                        
                        InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                        if cons.stock_quantity is None: cons.stock_quantity = 0.0
                        cons.stock_quantity -= qty_to_deduct
                        db.add(cons)
                        
                        log_name = f"{cons.name} (Заміна)" if is_replaced else cons.name
                        InventoryLogger.log(
                            db, entity_type="consumable", entity_id=cons.id, entity_name=log_name,
                            balance_before=c_old, balance_after=cons.stock_quantity,
                            reason=transaction_reason, force_change=-qty_to_deduct
                        )
                        if is_replaced:
                            details_list.append(f"📦 {cons.name}")

            # --- ЛОГІКА ПРОСТОГО ТОВАРУ ---
            else:
                if product.track_stock:
                    current_stock = product.stock_quantity if product.stock_quantity is not None else 0.0
                    if current_stock < item.quantity:
                        raise HTTPException(status_code=400, detail=f"Недостатньо залишку товару: {product.name}")
                    
                    if getattr(item, 'batch_id', None):
                        InventoryService.deduct_manual(db, item.batch_id, item.quantity)
                    else:
                        InventoryService.deduct_fifo(db, 'product', product.id, item.quantity)

                    product.stock_quantity = current_stock - item.quantity
                    db.add(product)

                    InventoryLogger.log(
                        db, entity_type="product", entity_id=product.id, entity_name=product.name,
                        balance_before=current_stock, balance_after=product.stock_quantity,
                        reason=transaction_reason, force_change=-item.quantity
                    )

                if product.master_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == product.master_recipe_id).first()
                    if recipe:
                         output_w = product.output_weight or 1
                         for r_item in recipe.items:
                            ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                            if ing:
                                deduction = (r_item.quantity / 100) * output_w * item.quantity if r_item.is_percentage else r_item.quantity * item.quantity
                                i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                
                                InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                                if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                ing.stock_quantity -= deduction
                                db.add(ing)
                                InventoryLogger.log(
                                    db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                                    balance_before=i_old, balance_after=ing.stock_quantity,
                                    reason=transaction_reason, force_change=-deduction
                                )

            # === ЗАГАЛЬНІ СПИСАННЯ (ProductIngredient, Consumable, Modifiers) ===
            for p_ing in product.ingredients:
                ing = db.query(models.Ingredient).filter(models.Ingredient.id == p_ing.ingredient_id).with_for_update().first()
                if ing:
                    i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                    deduction = p_ing.quantity * item.quantity
                    InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                    if ing.stock_quantity is None: ing.stock_quantity = 0.0
                    ing.stock_quantity -= deduction
                    db.add(ing)
                    InventoryLogger.log(
                        db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                        balance_before=i_old, balance_after=ing.stock_quantity,
                        reason=transaction_reason, force_change=-deduction
                    )

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

                cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).with_for_update().first()
                if cons:
                    c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                    qty_to_deduct = p_cons.quantity * item.quantity
                    
                    InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                    if cons.stock_quantity is None: cons.stock_quantity = 0.0
                    cons.stock_quantity -= qty_to_deduct
                    db.add(cons)
                    
                    log_name = f"{cons.name} (Заміна)" if is_replaced else cons.name
                    InventoryLogger.log(
                        db, entity_type="consumable", entity_id=cons.id, entity_name=log_name,
                        balance_before=c_old, balance_after=cons.stock_quantity,
                        reason=transaction_reason, force_change=-qty_to_deduct
                    )
                    if is_replaced:
                        details_list.append(f"📦 {cons.name}")

            if getattr(item, 'modifiers', None):
                for modifier in item.modifiers:
                     mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == modifier.modifier_id).with_for_update().first()
                     if mod_ing:
                        i_old = mod_ing.stock_quantity if mod_ing.stock_quantity is not None else 0.0
                        deduction = modifier.quantity * item.quantity
                        
                        InventoryService.deduct_fifo(db, 'ingredient', mod_ing.id, deduction)

                        if mod_ing.stock_quantity is None: mod_ing.stock_quantity = 0.0
                        mod_ing.stock_quantity -= deduction
                        db.add(mod_ing)
                        
                        InventoryLogger.log(
                            db, entity_type="ingredient", entity_id=mod_ing.id, entity_name=mod_ing.name,
                            balance_before=i_old, balance_after=mod_ing.stock_quantity,
                            reason=transaction_reason, force_change=-deduction
                        )
                        details_list.append(f"+ {mod_ing.name}")

            # Формуємо JSON-об'єкт для запису в базу (без жорстких зв'язків з БД складу)
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