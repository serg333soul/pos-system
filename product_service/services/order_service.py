# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models
import schemas
import traceback
from services.inventory_logger import InventoryLogger
from services.inventory_service import InventoryService # 🔥 НОВЕ: Імпортуємо наш сервіс партій
from services.product_service import ProductService

class OrderService:
    @staticmethod
    def process_checkout(db: Session, order_data: schemas.OrderCreate):
        try:
            print(f"🛒 [CHECKOUT] Початок обробки замовлення. Позицій: {len(order_data.items)}")
            total_order_price = 0.0
            
            # 1. Створюємо замовлення
            new_order = models.Order(
                created_at=datetime.utcnow(),
                payment_method=order_data.payment_method,
                total_price=0, 
                customer_id=order_data.customer_id
            )
            db.add(new_order)
            db.flush()
            
            transaction_reason = f"sale_order_{new_order.id}"

            # 2. Обробляємо товари
            for item in order_data.items:
                print(f"   -> Обробка товару ID: {item.product_id} (Варіант: {item.variant_id})")

                # 🔥 ДОДАЙТЕ ЦЕЙ РЯДОК ДЛЯ ДІАГНОСТИКИ:
                print(f"   -> ДАНІ ПАКУВАННЯ: {getattr(item, 'consumable_overrides', 'НЕМАЄ ДАНИХ')}")
                
                # 🔥 1. ЗАХИЩЕНИЙ СЛОВНИК ЗАМІН (працює і з dict, і з об'єктами Pydantic)
                overrides_map = {}
                if getattr(item, 'consumable_overrides', None):
                    for override in item.consumable_overrides:
                        # Перевіряємо тип: словник чи об'єкт
                        if isinstance(override, dict):
                            orig_id = override.get('original_id')
                            n_id = override.get('new_id')
                        else:
                            orig_id = getattr(override, 'original_id', None)
                            n_id = getattr(override, 'new_id', None)
                            
                        # Якщо знайшли original_id, записуємо в словник (обов'язково як числа int)
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

                    # 1. Фіксуємо баланс "ДО" (для історії)
                    balance_before = variant.stock_quantity if variant.stock_quantity is not None else 0.0
                    
                    # Визначаємо, чи треба фізично віднімати цифру залишку самого варіанту
                    should_deduct_physical = (variant.stock_quantity is not None) and (not variant.master_recipe_id)
                    
                    if should_deduct_physical:
                        if variant.stock_quantity < item.quantity:
                            raise HTTPException(status_code=400, detail=f"Недостатньо залишку: {variant.name}")
                        
                        # Гібридний облік для варіанту (Manual або FIFO)
                        if getattr(item, 'batch_id', None):
                            InventoryService.deduct_manual(db, item.batch_id, item.quantity)
                        elif getattr(variant, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'variant', variant.id, item.quantity)
                        
                        variant.stock_quantity -= item.quantity

                        # 🔥 ВИПРАВЛЕНО: Безпечний виклик логера для ФІЗИЧНОГО списання
                        InventoryLogger.log(
                            db, entity_type="product_variant", entity_id=variant.id, entity_name=item_name,
                            balance_before=balance_before, balance_after=variant.stock_quantity,
                            reason=transaction_reason, force_change=-item.quantity 
                        )

                    # 2. Списання ІНГРЕДІЄНТІВ (MasterRecipe)
                    if variant.master_recipe_id:
                        recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == variant.master_recipe_id).first()
                        if recipe:
                            output_w = variant.output_weight or 1
                            for r_item in recipe.items:
                                ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                                if ing:
                                    # Розрахунок кількості списання
                                    if r_item.is_percentage:
                                        deduction = (r_item.quantity / 100) * output_w * item.quantity
                                    else:
                                        deduction = r_item.quantity * item.quantity
                                    
                                    i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                    
                                    # Облік за методом FIFO або WAC
                                    if getattr(ing, 'costing_method', 'wac') == 'fifo':
                                        InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                                    # Оновлюємо фізичний залишок інгредієнта
                                    if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                    ing.stock_quantity -= deduction
                                    db.add(ing)
                                    
                                    # 🔥 ВИПРАВЛЕНО: Логуємо зміну ІНГРЕДІЄНТА
                                    InventoryLogger.log(
                                        db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                                        balance_before=i_old, balance_after=ing.stock_quantity,
                                        reason=transaction_reason, force_change=-deduction
                                    )

                            # Після того як всі інгредієнти списані, розраховуємо НОВИЙ "Поточний залишок" 
                            new_calculated_balance = ProductService.calculate_max_possible_stock(db, variant.id)
                            
                            # 🔥 ВИПРАВЛЕНО: Записуємо транзакцію для РОЗРАХУНКОВОГО ВАРІАНТУ
                            InventoryLogger.log(
                                db, entity_type="product_variant", entity_id=variant.id, entity_name=item_name,
                                balance_before=balance_before, balance_after=new_calculated_balance,
                                reason=transaction_reason, force_change=-item.quantity
                            )

                    # 3. Списання МАТЕРІАЛІВ варіанту (з урахуванням замін)
                    for v_cons in variant.consumables:
                        target_cons_id = v_cons.consumable_id
                        is_replaced = False
                        
                        # Перевіряємо, чи є інструкція змінити/видалити цей матеріал
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
                            
                            if getattr(cons, 'costing_method', 'wac') == 'fifo':
                                InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                            if cons.stock_quantity is None: cons.stock_quantity = 0.0
                            cons.stock_quantity -= qty_to_deduct
                            db.add(cons)
                            
                            log_name = f"{cons.name} (Заміна)" if is_replaced else cons.name
                            # 🔥 ВИПРАВЛЕНО: Логуємо матеріали
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
                        elif getattr(product, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'product', product.id, item.quantity)

                        product.stock_quantity = current_stock - item.quantity
                        db.add(product)

                        # 🔥 ВИПРАВЛЕНО: Логування простого товару
                        InventoryLogger.log(
                            db, entity_type="product", entity_id=product.id, entity_name=product.name,
                            balance_before=current_stock, balance_after=product.stock_quantity,
                            reason=transaction_reason, force_change=-item.quantity
                        )

                    # 2. Списання ІНГРЕДІЄНТІВ (MasterRecipe)
                    if product.master_recipe_id:
                        recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == product.master_recipe_id).first()
                        if recipe:
                             output_w = product.output_weight or 1
                             for r_item in recipe.items:
                                ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                                if ing:
                                    if r_item.is_percentage:
                                         deduction = (r_item.quantity / 100) * output_w * item.quantity
                                    else:
                                         deduction = r_item.quantity * item.quantity
                                    
                                    i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                    
                                    if getattr(ing, 'costing_method', 'wac') == 'fifo':
                                        InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                                    if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                    ing.stock_quantity -= deduction
                                    db.add(ing)
                                    # 🔥 ВИПРАВЛЕНО: Логування інгредієнта для простого товару
                                    InventoryLogger.log(
                                        db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                                        balance_before=i_old, balance_after=ing.stock_quantity,
                                        reason=transaction_reason, force_change=-deduction
                                    )

                # === ЗАГАЛЬНІ СПИСАННЯ ===
                
                # A. ProductIngredient
                for p_ing in product.ingredients:
                    ing = db.query(models.Ingredient).filter(models.Ingredient.id == p_ing.ingredient_id).with_for_update().first()
                    if ing:
                        i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                        deduction = p_ing.quantity * item.quantity
                        
                        if getattr(ing, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                        if ing.stock_quantity is None: ing.stock_quantity = 0.0
                        ing.stock_quantity -= deduction
                        db.add(ing)
                        # 🔥 ВИПРАВЛЕНО
                        InventoryLogger.log(
                            db, entity_type="ingredient", entity_id=ing.id, entity_name=ing.name,
                            balance_before=i_old, balance_after=ing.stock_quantity,
                            reason=transaction_reason, force_change=-deduction
                        )

                # B. ProductConsumable
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
                        
                        if getattr(cons, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                        if cons.stock_quantity is None: cons.stock_quantity = 0.0
                        cons.stock_quantity -= qty_to_deduct
                        db.add(cons)
                        
                        log_name = f"{cons.name} (Заміна)" if is_replaced else cons.name
                        # 🔥 ВИПРАВЛЕНО
                        InventoryLogger.log(
                            db, entity_type="consumable", entity_id=cons.id, entity_name=log_name,
                            balance_before=c_old, balance_after=cons.stock_quantity,
                            reason=transaction_reason, force_change=-qty_to_deduct
                        )
                        if is_replaced:
                            details_list.append(f"📦 {cons.name}")

                # C. Modifiers
                if getattr(item, 'modifiers', None):
                    for modifier in item.modifiers:
                         mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == modifier.modifier_id).with_for_update().first()
                         if mod_ing:
                            i_old = mod_ing.stock_quantity if mod_ing.stock_quantity is not None else 0.0
                            deduction = modifier.quantity * item.quantity
                            
                            if getattr(mod_ing, 'costing_method', 'wac') == 'fifo':
                                InventoryService.deduct_fifo(db, 'ingredient', mod_ing.id, deduction)

                            if mod_ing.stock_quantity is None: mod_ing.stock_quantity = 0.0
                            mod_ing.stock_quantity -= deduction
                            db.add(mod_ing)
                            
                            # 🔥 ВИПРАВЛЕНО
                            InventoryLogger.log(
                                db, entity_type="ingredient", entity_id=mod_ing.id, entity_name=mod_ing.name,
                                balance_before=i_old, balance_after=mod_ing.stock_quantity,
                                reason=transaction_reason, force_change=-deduction
                            )
                            details_list.append(f"+ {mod_ing.name}")

                # === ЗАПИС У ЧЕК ===
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_name=item_name,
                    quantity=item.quantity,
                    price_at_moment=price, 
                    details=", ".join(details_list) if details_list else None,
                    # 🔥 КРИТИЧНЕ ВИПРАВЛЕННЯ: Додано збереження JSON-даних про пакування!
                    consumable_overrides=[o.model_dump() for o in item.consumable_overrides] if getattr(item, 'consumable_overrides', None) else []
                ))
                
                total_order_price += price * item.quantity

            new_order.total_price = round(total_order_price, 2)
            db.commit()
            db.refresh(new_order)
            print(f"✅ [CHECKOUT] Замовлення {new_order.id} успішно створено! Сума: {new_order.total_price}")
            return new_order

        except HTTPException as http_ex:
            db.rollback()
            print(f"⚠️ HTTP помилка при оплаті: {http_ex.detail}")
            raise http_ex
        except Exception as e:
            db.rollback()
            print("❌ КРИТИЧНА ПОМИЛКА ПРИ ОПЛАТІ:")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення. Деталі в логах сервера.")