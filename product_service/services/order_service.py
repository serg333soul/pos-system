# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, text
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
                
                # Завантажуємо товар (Base load)
                product = db.query(models.Product).filter(
                    models.Product.id == item.product_id
                ).with_for_update().first()

                if not product:
                    print(f"   ❌ Товар {item.product_id} не знайдено!")
                    continue

                item_name = product.name
                price = product.price 
                details_list = []
                
                target_recipe_id = None
                base_weight = 0.0

                # === А. ВАРІАНТ ===
                if item.variant_id:
                    variant = db.query(models.ProductVariant).options(
                        joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable)
                    ).filter(
                        models.ProductVariant.id == item.variant_id
                    ).with_for_update().first()

                    if not variant:
                        raise HTTPException(status_code=404, detail=f"Варіант {item.variant_id} не знайдено")
                    
                    item_name = f"{product.name} ({variant.name})"
                    price = variant.price
                    details_list.append(f"Варіант: {variant.name}")
                    
                    target_recipe_id = variant.master_recipe_id or product.master_recipe_id
                    base_weight = variant.output_weight

                    # Списання варіанту
                    old_qty = variant.stock_quantity
                    variant.stock_quantity -= item.quantity
                    InventoryLogger.log(db, "product_variant", variant.id, item_name, old_qty, variant.stock_quantity, transaction_reason)

                    # Матеріали варіанту
                    for vc in variant.consumables:
                        if vc.consumable:
                            c_old = vc.consumable.stock_quantity
                            deduction = vc.quantity * item.quantity
                            vc.consumable.stock_quantity -= deduction
                            db.add(vc.consumable)
                            InventoryLogger.log(db, "consumable", vc.consumable.id, vc.consumable.name, c_old, vc.consumable.stock_quantity, transaction_reason)

                    # Інгредієнти варіанту (через relationship, тут зазвичай працює)
                    if hasattr(variant, 'ingredients'):
                        for vi in variant.ingredients:
                            if vi.ingredient:
                                i_old = vi.ingredient.stock_quantity
                                deduction = vi.quantity * item.quantity
                                vi.ingredient.stock_quantity -= deduction
                                db.add(vi.ingredient)
                                InventoryLogger.log(db, "ingredient", vi.ingredient.id, vi.ingredient.name, i_old, vi.ingredient.stock_quantity, transaction_reason)

                # === Б. ПРОСТИЙ ТОВАР ===
                else:
                    target_recipe_id = product.master_recipe_id
                    base_weight = product.output_weight
                    
                    # 1. Списання самого товару
                    if product.track_stock:
                        old_qty = product.stock_quantity
                        product.stock_quantity -= item.quantity
                        InventoryLogger.log(db, "product", product.id, product.name, old_qty, product.stock_quantity, transaction_reason)

                    # 2. 🔥 БЕЗПЕЧНЕ СПИСАННЯ ПРЯМИХ ІНГРЕДІЄНТІВ 🔥
                    # Ми робимо окремий запит, щоб не залежати від lazy loading
                    try:
                        direct_ingredients = db.query(models.ProductIngredient).filter(
                            models.ProductIngredient.product_id == product.id
                        ).all()
                        
                        print(f"      🔍 Знайдено прямих інгредієнтів (SQL): {len(direct_ingredients)}")

                        for link in direct_ingredients:
                            # Завантажуємо сам інгредієнт
                            real_ingredient = db.query(models.Ingredient).filter(
                                models.Ingredient.id == link.ingredient_id
                            ).with_for_update().first()

                            if real_ingredient:
                                i_old = real_ingredient.stock_quantity
                                deduction = link.quantity * item.quantity
                                real_ingredient.stock_quantity -= deduction
                                db.add(real_ingredient)
                                InventoryLogger.log(
                                    db, "ingredient", real_ingredient.id, real_ingredient.name, 
                                    i_old, real_ingredient.stock_quantity, 
                                    f"{transaction_reason}_direct"
                                )
                            else:
                                print(f"      ⚠️ Інгредієнт з ID {link.ingredient_id} не знайдено в таблиці ingredients!")
                    except Exception as e:
                        print(f"      ❌ ПОМИЛКА при списанні інгредієнтів товару {product.id}: {e}")
                        # Ми не зупиняємо продаж, якщо впало списання цукру, але пишемо в лог

                # === В. ЗАГАЛЬНІ МАТЕРІАЛИ ТОВАРУ ===
                # Також робимо безпечно через прямий запит, якщо relationship підводить
                prod_consumables = db.query(models.ProductConsumable).filter(
                     models.ProductConsumable.product_id == product.id
                ).all()
                
                for pc in prod_consumables:
                    real_cons = db.query(models.Consumable).filter(
                        models.Consumable.id == pc.consumable_id
                    ).with_for_update().first()
                    
                    if real_cons:
                        c_old = real_cons.stock_quantity
                        deduction = pc.quantity * item.quantity
                        real_cons.stock_quantity -= deduction
                        db.add(real_cons)
                        InventoryLogger.log(db, "consumable", real_cons.id, real_cons.name, c_old, real_cons.stock_quantity, transaction_reason)

                # === Г. СПИСАННЯ ПО ТЕХКАРТІ ===
                if target_recipe_id:
                    recipe = db.query(models.MasterRecipe).options(
                        joinedload(models.MasterRecipe.items).joinedload(models.MasterRecipeItem.ingredient)
                    ).filter(models.MasterRecipe.id == target_recipe_id).first()
                    
                    if recipe:
                        for r_item in recipe.items:
                            if r_item.ingredient:
                                deduction_per_item = (r_item.quantity / 100.0 * base_weight) if r_item.is_percentage else r_item.quantity
                                total_deduction = deduction_per_item * item.quantity
                                
                                i_old = r_item.ingredient.stock_quantity
                                r_item.ingredient.stock_quantity -= total_deduction
                                db.add(r_item.ingredient)
                                InventoryLogger.log(db, "ingredient", r_item.ingredient.id, r_item.ingredient.name, i_old, r_item.ingredient.stock_quantity, transaction_reason)

                # === Д. МОДИФІКАТОРИ ===
                for mod_ref in item.modifiers:
                    modifier = db.query(models.Modifier).filter(models.Modifier.id == mod_ref.modifier_id).first()
                    if modifier:
                        price += modifier.price_change
                        details_list.append(modifier.name)
                        if modifier.ingredient_id:
                             # Отримуємо інгредієнт
                             mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == modifier.ingredient_id).with_for_update().first()
                             if mod_ing:
                                i_old = mod_ing.stock_quantity
                                deduction = modifier.quantity * item.quantity
                                mod_ing.stock_quantity -= deduction
                                db.add(mod_ing)
                                InventoryLogger.log(db, "ingredient", mod_ing.id, mod_ing.name, i_old, mod_ing.stock_quantity, transaction_reason)

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
            print("✅ [CHECKOUT] Замовлення успішно створено!")
            return new_order

        except Exception as e:
            db.rollback()
            print("❌ ПОМИЛКА ПРИ ОПЛАТІ (CRITICAL):")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення")