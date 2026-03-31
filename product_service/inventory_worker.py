# FILE: product_service/inventory_worker.py

import pika
import json
import os
import time
from sqlalchemy.orm import Session

import models
from database import SessionLocal
from services.inventory_service import InventoryService
from services.inventory_logger import InventoryLogger
from services.product_service import ProductService

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@localhost:5672/')

def process_deduct_stock(db: Session, data: dict):
    """Обробка події списання зі складу"""
    order_id = data.get("order_id")
    transaction_reason = data.get("transaction_reason", f"sale_order_{order_id}")
    items = data.get("items", [])
    
    print(f"📦 [Inventory Worker] Починаю списання для чека #{order_id}. Позицій: {len(items)}")
    
    try:
        # Проходимось по кожному купленому товару з чека
        for item in items:
            product_id = item.get("product_id")
            variant_id = item.get("variant_id")
            item_qty = float(item.get("quantity", 1.0))
            batch_id = item.get("batch_id")
            
            print(f"   -> Списання товару ID: {product_id} (Варіант: {variant_id}), Кількість: {item_qty}")

            # 1. ЗАХИЩЕНИЙ СЛОВНИК ЗАМІН
            overrides_map = {}
            for override in item.get('consumable_overrides', []):
                orig_id = override.get('original_id')
                n_id = override.get('new_id')
                if orig_id is not None:
                    overrides_map[int(orig_id)] = int(n_id) if n_id else None

            # Завантажуємо товар (з блокуванням with_for_update для уникнення race conditions!)
            product = db.query(models.Product).filter(models.Product.id == product_id).with_for_update().first()
            if not product:
                print(f"⚠️ Товар {product_id} не знайдено!")
                continue

            item_name = product.name

            # --- ЛОГІКА ВАРІАНТІВ ---
            if variant_id:
                variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).with_for_update().first()
                if not variant: continue
                    
                item_name = f"{product.name} ({variant.name})"
                balance_before = variant.stock_quantity if variant.stock_quantity is not None else 0.0
                should_deduct_physical = (variant.stock_quantity is not None) and (not variant.master_recipe_id)
                
                # Фізичне списання варіанту
                if should_deduct_physical:
                    if batch_id:
                        InventoryService.deduct_manual(db, batch_id, item_qty)
                    else:
                        InventoryService.deduct_fifo(db, 'variant', variant.id, item_qty)
                    
                    variant.stock_quantity -= item_qty
                    InventoryLogger.log(
                        db, entity_type="product_variant", entity_id=variant.id, entity_name=item_name,
                        balance_before=balance_before, balance_after=variant.stock_quantity,
                        reason=transaction_reason, force_change=-item_qty 
                    )

                # Списання за рецептом
                if variant.master_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == variant.master_recipe_id).first()
                    if recipe:
                        output_w = variant.output_weight or 1
                        for r_item in recipe.items:
                            ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                            if ing:
                                deduction = (r_item.quantity / 100) * output_w * item_qty if r_item.is_percentage else r_item.quantity * item_qty
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
                            reason=transaction_reason, force_change=-item_qty
                        )

                # Пакування варіанта
                for v_cons in variant.consumables:
                    target_cons_id = v_cons.consumable_id
                    if target_cons_id in overrides_map:
                        new_id = overrides_map[target_cons_id]
                        if new_id is None or new_id == 0:
                            continue 
                        else:
                            target_cons_id = new_id

                    cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).with_for_update().first()
                    if cons:
                        c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                        qty_to_deduct = v_cons.quantity * item_qty
                        InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)
                        if cons.stock_quantity is None: cons.stock_quantity = 0.0
                        cons.stock_quantity -= qty_to_deduct
                        db.add(cons)
                        InventoryLogger.log(
                            db, entity_type="consumable", entity_id=cons.id, entity_name=cons.name,
                            balance_before=c_old, balance_after=cons.stock_quantity,
                            reason=transaction_reason, force_change=-qty_to_deduct
                        )

            # --- ЛОГІКА ПРОСТОГО ТОВАРУ ---
            else:
                if product.track_stock:
                    current_stock = product.stock_quantity if product.stock_quantity is not None else 0.0
                    if batch_id:
                        InventoryService.deduct_manual(db, batch_id, item_qty)
                    else:
                        InventoryService.deduct_fifo(db, 'product', product.id, item_qty)

                    product.stock_quantity = current_stock - item_qty
                    db.add(product)
                    InventoryLogger.log(
                        db, entity_type="product", entity_id=product.id, entity_name=product.name,
                        balance_before=current_stock, balance_after=product.stock_quantity,
                        reason=transaction_reason, force_change=-item_qty
                    )

                if product.master_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == product.master_recipe_id).first()
                    if recipe:
                         output_w = product.output_weight or 1
                         for r_item in recipe.items:
                            ing = db.query(models.Ingredient).filter(models.Ingredient.id == r_item.ingredient_id).with_for_update().first()
                            if ing:
                                deduction = (r_item.quantity / 100) * output_w * item_qty if r_item.is_percentage else r_item.quantity * item_qty
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
                    deduction = p_ing.quantity * item_qty
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
                if target_cons_id in overrides_map:
                    new_id = overrides_map[target_cons_id]
                    if new_id is None or new_id == 0:
                        continue 
                    else:
                        target_cons_id = new_id

                cons = db.query(models.Consumable).filter(models.Consumable.id == target_cons_id).with_for_update().first()
                if cons:
                    c_old = cons.stock_quantity if cons.stock_quantity is not None else 0.0
                    qty_to_deduct = p_cons.quantity * item_qty
                    InventoryService.deduct_fifo(db, 'consumable', cons.id, qty_to_deduct)
                    if cons.stock_quantity is None: cons.stock_quantity = 0.0
                    cons.stock_quantity -= qty_to_deduct
                    db.add(cons)
                    InventoryLogger.log(
                        db, entity_type="consumable", entity_id=cons.id, entity_name=cons.name,
                        balance_before=c_old, balance_after=cons.stock_quantity,
                        reason=transaction_reason, force_change=-qty_to_deduct
                    )

            # Модифікатори
            for modifier in item.get('modifiers', []):
                 mod_id = modifier.get('modifier_id')
                 mod_qty = float(modifier.get('quantity', 1.0))
                 mod_ing = db.query(models.Ingredient).filter(models.Ingredient.id == mod_id).with_for_update().first()
                 if mod_ing:
                    i_old = mod_ing.stock_quantity if mod_ing.stock_quantity is not None else 0.0
                    deduction = mod_qty * item_qty
                    InventoryService.deduct_fifo(db, 'ingredient', mod_ing.id, deduction)
                    if mod_ing.stock_quantity is None: mod_ing.stock_quantity = 0.0
                    mod_ing.stock_quantity -= deduction
                    db.add(mod_ing)
                    InventoryLogger.log(
                        db, entity_type="ingredient", entity_id=mod_ing.id, entity_name=mod_ing.name,
                        balance_before=i_old, balance_after=mod_ing.stock_quantity,
                        reason=transaction_reason, force_change=-deduction
                    )

        # 🔥 НАЙГОЛОВНІШЕ: Зберігаємо транзакцію в базі!
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"❌ [Inventory Worker] ПОМИЛКА під час списання: {e}")
        raise e # Прокидаємо вище, щоб RabbitMQ не видалив повідомлення

def callback(ch, method, properties, body):
    event_data = json.loads(body)
    event_type = event_data.get("event_type")
    
    db = SessionLocal()
    try:
        if event_type == "deduct_stock":
            process_deduct_stock(db, event_data)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"✅ [Inventory Worker] Склад успішно оновлено!\n")
        
    except Exception as e:
        # У разі помилки повертаємо повідомлення в чергу
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        db.close()

def start_consuming():
    print("⏳ [Inventory Worker] З'єднання з RabbitMQ...")
    while True:
        try:
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            break
        except pika.exceptions.AMQPConnectionError:
            print("Втрачено зв'язок. Повторна спроба через 5 сек...")
            time.sleep(5)

    channel.queue_declare(queue="inventory_queue", durable=True)
    channel.basic_qos(prefetch_count=1) 
    channel.basic_consume(queue="inventory_queue", on_message_callback=callback)

    print("🎧 [Inventory Worker] Готовий до роботи! Чекаю на події складу...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()