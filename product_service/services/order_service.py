# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models
import schemas
import traceback
from services.inventory_logger import InventoryLogger

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
                    
                    price = float(variant.price)
                    item_name = f"{product.name} ({variant.name})"

                    # 1. Списання залишку ВАРІАНТУ (Та запис в історію!)
                    # 🔥 FIX: Списуємо, якщо у варіанту задано кількість (не None), незалежно від налаштувань батька
                    if variant.stock_quantity is not None and not variant.master_recipe_id:
                        current_stock = variant.stock_quantity
                        
                        if current_stock < item.quantity:
                            raise HTTPException(status_code=400, detail=f"Недостатньо залишку для варіанту: {variant.name}")
                        
                        variant.stock_quantity = current_stock - item.quantity
                        db.add(variant)

                        # Логування списання варіанту
                        InventoryLogger.log(
                            db, 
                            "variant", 
                            variant.id, 
                            item_name, 
                            current_stock, 
                            variant.stock_quantity, 
                            transaction_reason
                        )

                    # 2. Списання ІНГРЕДІЄНТІВ (MasterRecipe)
                    if variant.master_recipe_id:
                        recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == variant.master_recipe_id).first()
                        if recipe:
                            output_w = variant.output_weight or 1
                            for r_item in recipe.items:
                                ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                                if ing:
                                    deduction = 0
                                    if r_item.is_percentage:
                                         deduction = (r_item.quantity / 100) * output_w * item.quantity
                                    else:
                                         deduction = r_item.quantity * item.quantity
                                    
                                    i_old = ing.stock_quantity if ing.stock_quantity is not None else 0.0
                                    if ing.stock_quantity is None: ing.stock_quantity = 0.0
                                    ing.stock_quantity -= deduction
                                    db.add(ing)
                                    
                                    InventoryLogger.log(db, "ingredient", ing.id, ing.name, i_old, ing.stock_quantity, transaction_reason)

                    # 3. Списання МАТЕРІАЛІВ варіанту
                    for v_cons in variant.consumables:
                         cons = db.query(models.Consumable).filter(models.Consumable.id == v_cons.consumable_id).with_for_update().first()
                         if cons:
                            c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                            qty_to_deduct = v_cons.quantity * item.quantity
                            
                            if cons.stock_quantity is None: cons.stock_quantity = 0.0
                            cons.stock_quantity -= qty_to_deduct
                            db.add(cons)
                            InventoryLogger.log(db, "consumable", cons.id, cons.name, c_old, cons.stock_quantity, transaction_reason)

                # --- ЛОГІКА ПРОСТОГО ТОВАРУ ---
                else:
                    # 1. Списання залишку ПРОСТОГО товару (Та запис в історію!)
                    if product.track_stock:
                        current_stock = product.stock_quantity if product.stock_quantity is not None else 0.0
                        if current_stock < item.quantity:
                            raise HTTPException(status_code=400, detail=f"Недостатньо залишку товару: {product.name}")
                        
                        product.stock_quantity = current_stock - item.quantity
                        db.add(product)

                        # Логування списання простого товару
                        InventoryLogger.log(
                            db, 
                            "product", 
                            product.id, 
                            product.name, 
                            current_stock, 
                            product.stock_quantity, 
                            transaction_reason
                        )

                    # 2. Списання ІНГРЕДІЄНТІВ (MasterRecipe)
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