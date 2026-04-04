# FILE: finance_service/finance_worker.py

import pika
import json
import os
import time
from decimal import Decimal
from sqlalchemy.orm import Session

# Імпортуємо локальні файли НОВОГО мікросервісу
import models
from database import SessionLocal, engine

from sqlalchemy.exc import OperationalError

print("⏳ [Finance Microservice] Очікування бази даних...")
while True:
    try:
        # Намагаємося створити таблиці
        models.Base.metadata.create_all(bind=engine)
        print("✅ [Finance Microservice] База даних готова!")
        break
    except OperationalError:
        print("⏳ База ще завантажується... Повтор через 2 секунди.")
        time.sleep(2)

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@localhost:5672/')

def create_transaction_internal(db: Session, amount: float, account_id: int, category_id: int, shift_id: int, user_id: int, ref_type: str, ref_id: int, desc: str):
    """
    Ця функція повністю замінює старий finance_service.create_transaction().
    Вона створює транзакцію і оновлює баланс рахунку.
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account or not account.is_active:
        raise ValueError(f"Рахунок {account_id} не знайдено або він деактивований")

    # 1. Створюємо запис у регістрі (Transactions)
    new_tx = models.Transaction(
        amount=Decimal(str(amount)),
        account_id=account.id,
        category_id=category_id,
        shift_id=shift_id,
        user_id=user_id,
        reference_type=ref_type,
        reference_id=ref_id,
        description=desc
    )
    db.add(new_tx)
    
    # 2. Оновлюємо кешований баланс рахунку
    account.balance += Decimal(str(amount))
    
    # 3. Зберігаємо все атомарно
    db.commit()

def process_order_paid(db: Session, data: dict):
    """Обробка події пробиття чека на касі"""
    active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    shift_id = active_shift.id if active_shift else None

    payment_type = 'bank' if data.get("payment_method") == 'card' else 'cash'
    account = db.query(models.Account).filter(models.Account.type == payment_type, models.Account.is_active == True).first()
    category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Продаж товарів").first()

    if account:
        create_transaction_internal(
            db=db,
            amount=data.get("amount"),
            account_id=account.id,
            category_id=getattr(category, 'id', None),
            shift_id=shift_id,
            user_id=data.get("user_id", 1),
            ref_type='order',
            ref_id=data.get("order_id"),
            desc=f"Оплата замовлення #{data.get('order_id')}"
        )

def process_supply_paid(db: Session, data: dict):
    """Обробка події закупівлі товару"""
    active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    shift_id = active_shift.id if active_shift else None

    account = db.query(models.Account).filter(models.Account.id == data.get("account_id")).first()
    category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Закупівля товару").first()

    if account:
        create_transaction_internal(
            db=db,
            amount=-abs(float(data.get("amount"))), # Витрати завжди з мінусом
            account_id=account.id,
            category_id=getattr(category, 'id', None),
            shift_id=shift_id,
            user_id=data.get("user_id", 1),
            ref_type='supply',
            ref_id=data.get("supply_id"),
            desc=f"Оплата постачання #{data.get('supply_id')}"
        )

def callback(ch, method, properties, body):
    """Слухач подій з RabbitMQ"""
    event_data = json.loads(body)
    event_type = event_data.get("event_type")
    
    print(f"📥 [Finance Microservice] Отримано подію: {event_type} -> {event_data}")
    
    db = SessionLocal()
    try:
        if event_type == "order_paid":
            process_order_paid(db, event_data)
        elif event_type == "supply_paid":
            process_supply_paid(db, event_data)
        # 🔥 ДОДАНО
        elif event_type == "order_refunded":
            active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
            account = db.query(models.Account).filter(models.Account.type == ('bank' if event_data.get("payment_method") == 'card' else 'cash')).first()
            if account:
                create_transaction_internal(
                    db=db,
                    amount=-abs(float(event_data.get("amount"))), # Повернення - це відтік грошей
                    account_id=account.id, category_id=None, shift_id=active_shift.id if active_shift else None,
                    user_id=1, ref_type='refund', ref_id=event_data.get("order_id"), desc=f"Повернення чека #{event_data.get('order_id')}"
                )
        else:
            print(f"⚠️ Невідомий тип події: {event_type}")

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"✅ [Finance Microservice] Транзакцію успішно записано!\n")
        
    except Exception as e:
        print(f"❌ [Finance Microservice] Помилка обробки: {e}")
        db.rollback()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        db.close()

def start_consuming():
    print("⏳ [Finance Microservice] З'єднання з RabbitMQ...")
    while True:
        try:
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            break
        except pika.exceptions.AMQPConnectionError:
            print("Втрачено зв'язок. Повторна спроба через 5 сек...")
            time.sleep(5)

    channel.queue_declare(queue="finance_queue", durable=True)
    channel.basic_qos(prefetch_count=1) 
    channel.basic_consume(queue="finance_queue", on_message_callback=callback)

    print("🎧 [Finance Microservice] Готовий до роботи! Чекаю на фінансові події...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()