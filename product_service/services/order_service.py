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
                        
                        # 🔥 НОВЕ: Гібридний облік для варіанту (Manual або FIFO)
                        # Якщо з фронтенду прийшов конкретний batch_id - списуємо з нього
                        if getattr(item, 'batch_id', None):
                            InventoryService.deduct_manual(db, item.batch_id, item.quantity)
                        # Інакше перевіряємо, чи ввімкнено FIFO для цього варіанту
                        elif getattr(variant, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'variant', variant.id, item.quantity)
                        
                        # Завжди зменшуємо загальний залишок
                        variant.stock_quantity -= item.quantity

                    # 3. ЛОГУВАННЯ ВАРІАНТУ (ЗАВЖДИ!)
                    balance_after = variant.stock_quantity if variant.stock_quantity is not None else 0.0
                    InventoryLogger.log(
                        db,
                        entity_type="product_variant",
                        entity_id=variant.id,
                        entity_name=item_name,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        reason=transaction_reason,
                        force_change=-item.quantity 
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
                                    deduction = 0
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
                                    
                                    # Логуємо зміну саме ІНГРЕДІЄНТА
                                    InventoryLogger.log(db, "ingredient", ing.id, ing.name, i_old, ing.stock_quantity, transaction_reason)

                            # 🔥 КЛЮЧОВЕ ВИПРАВЛЕННЯ ДЛЯ ВАРІАНТУ:
                            # Після того як всі інгредієнти списані, ми розраховуємо НОВИЙ "Поточний залишок" 
                            # (calculated stock), який тепер доступний для цього варіанту.
                            
                            new_calculated_balance = ProductService.calculate_max_possible_stock(db, variant.id)
                            
                            # Записуємо транзакцію для ВАРІАНТУ з актуальним залишком
                            InventoryLogger.log(
                                db,
                                entity_type="product_variant",
                                entity_id=variant.id,
                                entity_name=item_name,
                                balance_before=balance_before, # Це значення ми взяли на початку циклу
                                balance_after=new_calculated_balance, # 🔥 Тепер тут НЕ 0, а реальний розрахунок!
                                reason=transaction_reason,
                                force_change=-item.quantity
                            )

                    # 3. Списання МАТЕРІАЛІВ варіанту
                    for v_cons in variant.consumables:
                         cons = db.query(models.Consumable).filter(models.Consumable.id == v_cons.consumable_id).with_for_update().first()
                         if cons:
                            c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                            qty_to_deduct = v_cons.quantity * item.quantity
                            
                            # 🔥 НОВЕ: Перевірка FIFO для Матеріалу
                            if getattr(cons, 'costing_method', 'wac') == 'fifo':
                                InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                            if cons.stock_quantity is None: cons.stock_quantity = 0.0
                            cons.stock_quantity -= qty_to_deduct
                            db.add(cons)
                            InventoryLogger.log(db, "consumable", cons.id, cons.name, c_old, cons.stock_quantity, transaction_reason)

                # --- ЛОГІКА ПРОСТОГО ТОВАРУ ---
                else:
                    if product.track_stock:
                        current_stock = product.stock_quantity if product.stock_quantity is not None else 0.0
                        if current_stock < item.quantity:
                            raise HTTPException(status_code=400, detail=f"Недостатньо залишку товару: {product.name}")
                        
                        # 🔥 НОВЕ: Гібридний облік для простого товару
                        if getattr(item, 'batch_id', None):
                            InventoryService.deduct_manual(db, item.batch_id, item.quantity)
                        elif getattr(product, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'product', product.id, item.quantity)

                        product.stock_quantity = current_stock - item.quantity
                        db.add(product)

                        # Логування списання простого товару
                        InventoryLogger.log(
                            db, "product", product.id, product.name, 
                            current_stock, product.stock_quantity, transaction_reason
                        )

                    # 2. Списання ІНГРЕДІЄНТІВ (MasterRecipe) - Аналогічно додаємо FIFO
                    if product.master_recipe_id:
                        recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == product.master_recipe_id).first()
                        if recipe:
                             output_w = product.output_weight or 1
                             for r_item in recipe.items:
                                ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                                if ing:
                                    deduction = 0
                                    if r_item.is_percentage:
                                         deduction = (r_item.quantity / 100) * output_w * item.quantity
                                    else:
                                         deduction = r_item.quantity * item.quantity
                                    
                                    i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                    
                                    # 🔥 НОВЕ: FIFO
                                    if getattr(ing, 'costing_method', 'wac') == 'fifo':
                                        InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                                    if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                    ing.stock_quantity -= deduction
                                    db.add(ing)
                                    InventoryLogger.log(db, "ingredient", ing.id, ing.name, i_old, ing.stock_quantity, transaction_reason)

                # === ЗАГАЛЬНІ СПИСАННЯ ===
                
                # A. ProductIngredient (Додаткові інгредієнти поза рецептом)
                for p_ing in product.ingredients:
                    ing = db.query(models.Ingredient).filter(models.Ingredient.id == p_ing.ingredient_id).with_for_update().first()
                    if ing:
                        i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                        deduction = p_ing.quantity * item.quantity
                        
                        # 🔥 НОВЕ: FIFO
                        if getattr(ing, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'ingredient', ing.id, deduction)

                        if ing.stock_quantity is None: ing.stock_quantity = 0.0
                        ing.stock_quantity -= deduction
                        db.add(ing)
                        InventoryLogger.log(db, "ingredient", ing.id, ing.name, i_old, ing.stock_quantity, transaction_reason)

                # B. ProductConsumable (Загальні матеріали)
                for p_cons in product.consumables:
                    cons = db.query(models.Consumable).filter(models.Consumable.id == p_cons.consumable_id).with_for_update().first()
                    if cons:
                        c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                        qty_to_deduct = p_cons.quantity * item.quantity
                        
                        # 🔥 НОВЕ: FIFO
                        if getattr(cons, 'costing_method', 'wac') == 'fifo':
                            InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)

                        if cons.stock_quantity is None: cons.stock_quantity = 0.0
                        cons.stock_quantity -= qty_to_deduct
                        db.add(cons)
                        InventoryLogger.log(db, "consumable", cons.id, cons.name, c_old, cons.stock_quantity, transaction_reason)

                # C. Modifiers (Модифікатори з фронтенду)
                if item.modifiers:
                    for modifier in item.modifiers:
                         mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == modifier.modifier_id).with_for_update().first()
                         if mod_ing:
                            i_old = mod_ing.stock_quantity if mod_ing.stock_quantity is not None else 0.0
                            deduction = modifier.quantity * item.quantity
                            
                            # 🔥 НОВЕ: FIFO
                            if getattr(mod_ing, 'costing_method', 'wac') == 'fifo':
                                InventoryService.deduct_fifo(db, 'ingredient', mod_ing.id, deduction)

                            if mod_ing.stock_quantity is None: mod_ing.stock_quantity = 0.0
                            mod_ing.stock_quantity -= deduction
                            db.add(mod_ing)
                            
                            InventoryLogger.log(db, "ingredient", mod_ing.id, mod_ing.name, i_old, mod_ing.stock_quantity, transaction_reason)
                            details_list.append(f"+ {mod_ing.name}")

                # === ЗАПИС У ЧЕК ===
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_name=item_name,
                    quantity=item.quantity,
                    price_at_moment=price, 
                    details=", ".join(details_list) if details_list else None
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