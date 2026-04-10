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
    order_id = data.get("order_id")
    
    # 🔥 БЛОК-ПОСТ ІДЕМПОТЕНТНОСТІ: Перевіряємо, чи ми вже нараховували бонуси за цей чек
    if not order_id:
        print("⚠️ [Loyalty] Чек без ID. Пропуск.")
        return

    existing_tx = db.query(models.BonusTransaction).filter(models.BonusTransaction.order_id == order_id).first()
    if existing_tx:
        print(f"🛡️ [Loyalty] Дубль перехоплено! Бонуси за чек #{order_id} вже оброблені. Пропуск.")
        return

    # Перевірка клієнта
    customer_id = data.get("customer_id")
    if not customer_id:
        print("ℹ️ [Loyalty] Чек без клієнта (гість). Бонуси не нараховуються.")
        return

    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        print(f"⚠️ [Loyalty] Клієнта з ID {customer_id} не знайдено в базі.")
        return

    # 1. СПИСАННЯ БОНУСІВ
    bonuses_spent = Decimal(str(data.get("bonuses_spent", 0.0)))
    if bonuses_spent > 0:
        customer.bonus_balance -= bonuses_spent
        print(f"➖ [Loyalty] Списано {bonuses_spent} бонусів.")

    # 2. НАРАХУВАННЯ БОНУСІВ
    amount = Decimal(str(data.get("amount", 0.0)))
    bonuses_earned = Decimal("0.0")
    
    # Нараховуємо кешбек лише на ту суму, яка була оплачена реальними грошима
    eligible_amount = amount - bonuses_spent
    if eligible_amount > 0:
        bonuses_earned = eligible_amount * Decimal("0.05") # 5% кешбек (можна винести в налаштування)
        customer.bonus_balance += bonuses_earned
        print(f"➕ [Loyalty] Нараховано {bonuses_earned:.2f} бонусів.")

    # 🔥 ЗБЕРІГАЄМО ТРАНЗАКЦІЮ (Щоб наступного разу спрацював блок-пост)
    new_tx = models.BonusTransaction(
        customer_id=customer.id,
        order_id=order_id,
        bonuses_spent=bonuses_spent,
        bonuses_earned=bonuses_earned
    )
    db.add(new_tx)

    db.commit()
    print(f"✅ [Loyalty] Баланс клієнта {customer.name} оновлено. Поточний баланс: {customer.bonus_balance:.2f} ₴\n")

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