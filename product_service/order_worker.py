# FILE: product_service/order_worker.py
import pika
import json
import os
import time
from sqlalchemy.orm import Session

# Імпортуємо налаштування вашого існуючого продуктового моноліту
from database import SessionLocal, engine
import models
from services.finance_client import FinanceClient
from services.inventory_client import InventoryClient

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@rabbitmq:5672/')

print("⏳ [Order Worker] Очікування бази даних...")
while True:
    try:
        # Перевірка підключення
        with engine.connect() as conn:
            print("✅ [Order Worker] Підключено до БД Товарів!")
            break
    except Exception:
        print("⏳ База ще завантажується... Повтор через 2 секунди.")
        time.sleep(2)

def process_order(ch, method, properties, body):
    db = SessionLocal()
    try:
        data = json.loads(body)
        event_type = data.get("event_type")

        if event_type == "create_order":
            print("📥 [Order Worker] Отримано нове замовлення з кошика!")

            # 1. Створюємо запис чека в базі
            new_order = models.Order(
                customer_id=data.get("customer_id"),
                payment_method=data.get("payment_method", "cash"),
                bonuses_spent=data.get("bonuses_spent", 0.0),
                total_price=0.0 # Порахуємо нижче
            )
            db.add(new_order)
            db.flush() # Flush генерує new_order.id, але ще не робить кінцевий commit

            total_price = 0.0
            
            # (Опціонально) Список товарів для складу, якщо він вам потрібен у такому форматі
            items_for_inventory = []

            # 2. Додаємо товари в чек
            for item in data.get("items", []):
                price = float(item.get("price", 0))
                qty = int(item.get("quantity", 1))
                total_price += price * qty

                db_item = models.OrderItem(
                    order_id=new_order.id,
                    product_id=item.get("product_id"),
                    variant_id=item.get("variant_id"),
                    product_name=item.get("name", "Unknown"), # Додали назву товару
                    quantity=qty,
                    price_at_moment=price
                )
                db.add(db_item)
                
                # Відправляємо команду списати інгредієнти
                InventoryClient.deduct_stock_async(
                    new_order.id, 
                    f"sale_order_{new_order.id}", 
                    data.get("items", [])  # 🔥 МАГІЯ ТУТ: Відправляємо сирі дані з кошика, де Є всі інгредієнти!
                )

            # Фіксуємо підсумкову суму з урахуванням знижки
            new_order.total_price = max(0, total_price - float(new_order.bonuses_spent))
            
            db.commit()
            db.refresh(new_order)
            print(f"✅ [Order Worker] Чек #{new_order.id} успішно створено! Сума: {new_order.total_price} ₴")

            # 3. Розсилаємо події у Фінанси та Склад (використовуючи ваші існуючі клієнти)
            try:
                # Відправляємо гроші у фінанси та бонуси клієнту
                FinanceClient.register_order_income(
                    db=db,
                    order_id=new_order.id,
                    total_price=float(new_order.total_price), # 🔥 КОНВЕРТАЦІЯ В FLOAT
                    payment_method=new_order.payment_method,
                    user_id=1, # ID касира за замовчуванням
                    customer_id=new_order.customer_id,
                    bonuses_spent=float(new_order.bonuses_spent), # 🔥 КОНВЕРТАЦІЯ В FLOAT
                    use_bonuses=data.get("use_bonuses", False)
                )
                
                # Відправляємо команду списати інгредієнти
                InventoryClient.deduct_stock_async(
                    new_order.id, 
                    f"sale_order_{new_order.id}", 
                    items_for_inventory # 🔥 ПЕРЕДАЄМО ПРАВИЛЬНИЙ СПИСОК (а не об'єкти бази)
                )
                
                print("📤 [Order Worker] Команди на Склад та у Фінанси успішно відправлено.")
            except Exception as client_err:
                print(f"⚠️ [Order Worker] Помилка розсилки подій (але чек збережено): {client_err}")

        # Підтверджуємо успішну обробку
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        db.rollback()
        print(f"❌ [Order Worker] КРИТИЧНА ПОМИЛКА: {e}")
        # Не підтверджуємо, щоб RabbitMQ спробував ще раз
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        db.close()

def start_consuming():
    print("⏳ [Order Worker] З'єднання з RabbitMQ...")
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            break
        except pika.exceptions.AMQPConnectionError:
            print("Втрачено зв'язок. Повторна спроба через 5 сек...")
            time.sleep(5)

    channel.queue_declare(queue="orders_queue", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="orders_queue", on_message_callback=process_order)
    print("🐇 [Order Worker] Готовий! Слухаю чергу 'orders_queue'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()