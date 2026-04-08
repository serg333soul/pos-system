# FILE: customer_service/customer_worker.py

import pika
import json
import os
import time
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

import models
from database import SessionLocal, engine

# Захист при старті: чекаємо, поки підніметься БД
print("⏳ [Loyalty Microservice] Очікування бази даних...")
while True:
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ [Loyalty Microservice] База даних готова!")
        break
    except OperationalError:
        print("⏳ База ще завантажується... Повтор через 2 секунди.")
        time.sleep(2)

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@rabbitmq:5672/')

def process_loyalty_points(db: Session, data: dict):
    customer_id = data.get("customer_id")
    if not customer_id:
        print("ℹ️ [Loyalty] Чек без клієнта (гість). Бонуси не нараховуються.")
        return

    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        print(f"⚠️ [Loyalty] Клієнта з ID {customer_id} не знайдено в базі.")
        return

    # 1. СПИСАННЯ БОНУСІВ (Якщо вони були використані для оплати)
    bonuses_spent = Decimal(str(data.get("bonuses_spent", 0)))
    if bonuses_spent > 0:
        # Захист: не можемо списати більше, ніж є на балансі
        actual_spent = min(customer.bonus_balance, bonuses_spent)
        customer.bonus_balance -= actual_spent
        print(f"📉 [Loyalty] Списано {actual_spent} бонусів у '{customer.name}'.")

    # 2. НАРАХУВАННЯ БОНУСІВ (Тільки на ту суму, яку клієнт сплатив РЕАЛЬНИМИ грошима)
    amount_paid = Decimal(str(data.get("amount", 0)))
    if amount_paid > 0:
        bonus_to_add = amount_paid * Decimal("0.05") # 5% кешбеку
        customer.bonus_balance += bonus_to_add
        print(f"✨ [Loyalty] Нараховано {bonus_to_add} бонусів за покупку на суму {amount_paid} ₴.")

    db.commit()
    print(f"💰 [Loyalty] Фінальний баланс клієнта '{customer.name}': {customer.bonus_balance} ₴\n")

def callback(ch, method, properties, body):
    data = json.loads(body)
    event_type = data.get("event_type")
    
    if event_type == "order_paid":
        print(f"📥 [Loyalty] Отримано чек на обробку бонусів...")
        db = SessionLocal()
        try:
            process_loyalty_points(db, data)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"❌ [Loyalty Microservice] Помилка: {e}")
            db.rollback()
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            db.close()
    else:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    print("⏳ [Loyalty Microservice] З'єднання з RabbitMQ...")
    while True:
        try:
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            break
        except pika.exceptions.AMQPConnectionError:
            print("⚠️ Втрачено зв'язок з RabbitMQ. Повторна спроба через 5 сек...")
            time.sleep(5)

    queue_name = "loyalty_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1) 
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print(f"🎧 [Loyalty Microservice] Готовий до роботи! Слухаю чергу '{queue_name}'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()