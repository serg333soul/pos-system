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
        event_type = data.get("event_type")
        order_id = data.get("order_id")
        
        # Визначаємо унікальну причину для журналу
        reason = data.get("reason", f"{event_type}_{order_id}")

        # 🔥 БЛОК-ПОСТ ІДЕМПОТЕНТНОСТІ (Спільний для списання і повернення)
        if not order_id:
            print("⚠️ [Inventory] Отримано подію без order_id. Пропуск.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        existing_event = db.query(models.ProcessedEvent).filter(models.ProcessedEvent.event_id == reason).first()
        if existing_event:
            print(f"🛡️ [Inventory] Дубль перехоплено! Подія {reason} вже оброблена раніше. Пропуск.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # ---------------------------------------------------------
        # ЛОГІКА СПИСАННЯ
        # ---------------------------------------------------------
        if event_type == "deduct_bom":
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

            # 3. Реєструємо продаж самих товарів
            for item in data.get("sold_items", []):
                db.add(models.InventoryTransaction(
                    entity_type=item.get("type", "product"),
                    entity_id=item.get("id"),
                    entity_name=item.get("name", "Unknown Product"),
                    change_amount=-item.get("qty", 0),
                    balance_after=item.get("new_stock"), 
                    reason=reason
                ))

            # ЗАПИСУЄМО В ЖУРНАЛ ПАМ'ЯТІ ТА ЗБЕРІГАЄМО
            db.add(models.ProcessedEvent(event_id=reason))
            db.commit()
            print(f"✅ [Inventory Worker] Чек #{order_id} успішно списано з партій (FIFO)!")

        # ---------------------------------------------------------
        # ЛОГІКА ПОВЕРНЕННЯ
        # ---------------------------------------------------------
        elif event_type == "refund_bom":
            print(f"📦 [Inventory Worker] ПОВЕРНЕННЯ товарів для чека #{order_id}...")

            for ing in data.get("ingredients", []):
                db_ing = db.query(models.Ingredient).filter(models.Ingredient.id == ing["id"]).first()
                if db_ing:
                    db_ing.stock_quantity += ing["qty"]
                    batch = db.query(models.SupplyItem).filter(models.SupplyItem.entity_type == "ingredient", models.SupplyItem.entity_id == ing["id"]).order_by(models.SupplyItem.id.desc()).first()
                    if batch: batch.remaining_quantity += ing["qty"]
                    db.add(models.InventoryTransaction(entity_type="ingredient", entity_id=ing["id"], entity_name=db_ing.name, change_amount=ing["qty"], balance_after=db_ing.stock_quantity, reason=reason))

            for cons in data.get("consumables", []):
                db_cons = db.query(models.Consumable).filter(models.Consumable.id == cons["id"]).first()
                if db_cons:
                    db_cons.stock_quantity += cons["qty"]
                    batch = db.query(models.SupplyItem).filter(models.SupplyItem.entity_type == "consumable", models.SupplyItem.entity_id == cons["id"]).order_by(models.SupplyItem.id.desc()).first()
                    if batch: batch.remaining_quantity += cons["qty"]
                    db.add(models.InventoryTransaction(entity_type="consumable", entity_id=cons["id"], entity_name=db_cons.name, change_amount=cons["qty"], balance_after=db_cons.stock_quantity, reason=reason))
            
            # ЗАПИСУЄМО В ЖУРНАЛ ПАМ'ЯТІ ТА ЗБЕРІГАЄМО
            db.add(models.ProcessedEvent(event_id=reason))
            db.commit()
            print(f"✅ [Inventory Worker] ПОВЕРНЕННЯ для чека #{order_id} завершено!")

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