import sys
import os
import traceback

# Шлях для імпортів
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models, schemas
from services.inventory_logger import InventoryLogger

class OrderService:
    """
    Гібридний OrderService:
    1. ZERO TRUST: Сам рахує ціну.
    2. LOCKING: Блокує товари при покупці.
    3. DEEP INVENTORY: Списує по рецептах (як у старій версії).
    """
    @staticmethod
    def process_checkout(db: Session, order_data: schemas.OrderCreate):
        try:
            total_order_price = 0.0
            
            # 1. Створюємо замовлення (ціна поки 0)
            new_order = models.Order(
                created_at=datetime.utcnow(),
                payment_method=order_data.payment_method,
                total_price=0, 
                customer_id=order_data.customer_id
            )
            db.add(new_order)
            db.flush() # Отримуємо ID
            
            transaction_reason = f"sale_order_{new_order.id}"

            # 2. Обробляємо товари
            for item in order_data.items:
                # --- БЛОКУВАННЯ (Locking) ---
                product = db.query(models.Product).filter(
                    models.Product.id == item.product_id
                ).with_for_update().first()

                if not product:
                    continue

                item_name = product.name
                # Ціну беремо з БАЗИ, а не з запиту
                price = product.price 
                details_list = []
                
                target_recipe_id = None
                base_weight = 0.0

                # === А. ВАРІАНТ (якщо є) ===
                if item.variant_id:
                    variant = db.query(models.ProductVariant).filter(
                        models.ProductVariant.id == item.variant_id
                    ).with_for_update().first()

                    if not variant:
                        raise HTTPException(status_code=404, detail=f"Варіант {item.variant_id} не знайдено")
                    
                    item_name = f"{product.name} ({variant.name})"
                    price = variant.price # Ціна варіанту
                    details_list.append(f"Варіант: {variant.name}")
                    
                    # Визначаємо, яку техкарту списувати
                    target_recipe_id = variant.master_recipe_id or product.master_recipe_id
                    base_weight = variant.output_weight

                    # 1. Списання залишку самого варіанту (якщо ведеться облік штук)
                    if variant.stock_quantity > 0 or product.track_stock: # Логіка перевірки залишку
                         old_qty = variant.stock_quantity
                         variant.stock_quantity -= item.quantity
                         InventoryLogger.log(db, "variant", variant.id, item_name, old_qty, variant.stock_quantity, transaction_reason)

                    # 2. Списання матеріалів варіанту (стаканчики і т.д.)
                    for vc in variant.consumables:
                        if vc.consumable:
                            c_old = vc.consumable.stock_quantity
                            deduction = vc.quantity * item.quantity
                            vc.consumable.stock_quantity -= deduction
                            db.add(vc.consumable)
                            InventoryLogger.log(db, "consumable", vc.consumable.id, vc.consumable.name, c_old, vc.consumable.stock_quantity, transaction_reason)

                    # 3. Списання унікальних інгредієнтів варіанту
                    # (Цей блок був у старій версії, повертаємо його)
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
                    
                    if product.track_stock:
                        old_qty = product.stock_quantity
                        product.stock_quantity -= item.quantity
                        InventoryLogger.log(db, "product", product.id, product.name, old_qty, product.stock_quantity, transaction_reason)

                # === В. ЗАГАЛЬНІ МАТЕРІАЛИ ТОВАРУ ===
                for pc in product.consumables:
                    if pc.consumable:
                        c_old = pc.consumable.stock_quantity
                        deduction = pc.quantity * item.quantity
                        pc.consumable.stock_quantity -= deduction
                        db.add(pc.consumable)
                        InventoryLogger.log(db, "consumable", pc.consumable.id, pc.consumable.name, c_old, pc.consumable.stock_quantity, transaction_reason)

                # === Г. СПИСАННЯ ПО ТЕХКАРТІ (MASTER RECIPE) ===
                # Це те, чого не вистачало в "безпечній" версії!
                if target_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == target_recipe_id).first()
                    if recipe:
                        for r_item in recipe.items:
                            if r_item.ingredient:
                                # Логіка: Якщо відсоток - беремо від ваги, якщо ні - фіксована кількість
                                deduction_per_item = (r_item.quantity / 100.0 * base_weight) if r_item.is_percentage else r_item.quantity
                                total_deduction = deduction_per_item * item.quantity
                                
                                i_old = r_item.ingredient.stock_quantity
                                r_item.ingredient.stock_quantity -= total_deduction
                                db.add(r_item.ingredient)
                                
                                InventoryLogger.log(db, "ingredient", r_item.ingredient.id, r_item.ingredient.name, i_old, r_item.ingredient.stock_quantity, transaction_reason)

                # === Д. МОДИФІКАТОРИ (Сиропи, молоко) ===
                for mod_ref in item.modifiers:
                    # Безпечно шукаємо модифікатор
                    modifier = db.query(models.Modifier).filter(models.Modifier.id == mod_ref.modifier_id).first()
                    
                    if modifier:
                        # 1. Додаємо до ціни
                        price += modifier.price_change
                        details_list.append(modifier.name)
                        
                        # 2. Списуємо інгредієнт модифікатора
                        if modifier.ingredient:
                            i_old = modifier.ingredient.stock_quantity
                            deduction = modifier.quantity * item.quantity
                            modifier.ingredient.stock_quantity -= deduction
                            db.add(modifier.ingredient)
                            InventoryLogger.log(db, "ingredient", modifier.ingredient.id, modifier.ingredient.name, i_old, modifier.ingredient.stock_quantity, transaction_reason)

                # === ЗАПИС У ЧЕК ===
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_name=item_name,
                    quantity=item.quantity,
                    price_at_moment=price, # Серверна ціна
                    details=", ".join(details_list) if details_list else None
                ))
                
                total_order_price += price * item.quantity

            # 3. Фіксуємо загальну суму і зберігаємо
            new_order.total_price = round(total_order_price, 2)
            db.commit()
            db.refresh(new_order)
            return new_order

        except Exception as e:
            db.rollback()
            print("❌ ПОМИЛКА ПРИ ОПЛАТІ:")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення")