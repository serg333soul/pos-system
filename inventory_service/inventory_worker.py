# FILE: inventory_service/inventory_worker.py
import pika
import json
import os
import time
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@rabbitmq:5672/')

print("⏳ [Inventory Worker] Очікування бази даних...")
while True:
    try:
        with engine.connect() as conn:
            print("✅ [Inventory Worker] Підключено до БД Складу!")
            break
    except Exception:
        time.sleep(2)

def apply_fifo(db: Session, entity_type: str, entity_id: int, deduct_qty: float):
    """Шукає найстаріші партії (FIFO) і списує з них залишки"""
    batches = db.query(models.SupplyItem).join(models.Supply).filter(
        models.SupplyItem.entity_type == entity_type,
        models.SupplyItem.entity_id == entity_id,
        models.SupplyItem.remaining_quantity > 0
    ).order_by(models.SupplyItem.id.asc()).with_for_update().all()

    rem_qty = deduct_qty
    for batch in batches:
        if rem_qty <= 0: break
        if batch.remaining_quantity >= rem_qty:
            batch.remaining_quantity -= rem_qty
            rem_qty = 0
        else:
            rem_qty -= batch.remaining_quantity
            batch.remaining_quantity = 0

def process_message(ch, method, properties, body):
    db = SessionLocal()
    try:
        data = json.loads(body)
        
        if data.get("event_type") == "deduct_bom":
            order_id = data.get("order_id")
            reason = data.get("reason", f"sale_order_{order_id}")
            print(f"📦 [Inventory Worker] Списання для чека #{order_id}...")

            # 1. Списуємо інгредієнти
            for ing in data.get("ingredients", []):
                db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ing["id"]).first()
                if db_ing:
                    db_ing.stock_quantity -= ing["qty"]
                    apply_fifo(db, "ingredient", ing["id"], ing["qty"]) # FIFO
                    
                    db.add(models.InventoryTransaction(
                        entity_type="ingredient", entity_id=ing["id"], entity_name=db_ing.name,
                        change_amount=-ing["qty"], balance_after=db_ing.stock_quantity, reason=reason
                    ))

            # 2. Списуємо матеріали
            for cons in data.get("consumables", []):
                db_cons = db.query(models.Consumable).filter(models.Consumable.id == cons["id"]).first()
                if db_cons:
                    db_cons.stock_quantity -= cons["qty"]
                    apply_fifo(db, "consumable", cons["id"], cons["qty"]) # FIFO
                    
                    db.add(models.InventoryTransaction(
                        entity_type="consumable", entity_id=cons["id"], entity_name=db_cons.name,
                        change_amount=-cons["qty"], balance_after=db_cons.stock_quantity, reason=reason
                    ))

            # 3. Реєструємо продаж самих товарів або варіантів для історії
            # (Навіть якщо їх фізичний залишок у іншій БД, транзакція має бути тут для звітності)
            for item in data.get("sold_items", []):
                # Очікуємо в повідомленні: {"type": "variant", "id": 10, "name": "Latte", "qty": 1, "new_stock": 5}
                db.add(models.InventoryTransaction(
                    entity_type=item.get("type", "product"),
                    entity_id=item.get("id"),
                    entity_name=item.get("name", "Unknown Product"),
                    change_amount=-item.get("qty", 0),
                    # balance_after беремо з повідомлення, бо воркер не має прямого доступу до БД товарів
                    balance_after=item.get("new_stock"), 
                    reason=reason
                ))

            db.commit()
            print(f"✅ [Inventory Worker] Чек #{order_id} успішно списано з партій (FIFO)!")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        db.rollback()
        print(f"❌ [Inventory Worker] Помилка обробки чека: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    finally:
        db.close()

def start_worker():
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue='inventory_queue', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='inventory_queue', on_message_callback=process_message)
            print("🐇 [Inventory Worker] Готовий! Очікування чеків...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            time.sleep(5)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    start_worker()