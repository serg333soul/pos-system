# FILE: product_service/services/finance_client.py

from sqlalchemy.orm import Session
# 🔥 Імпортуємо наш новий брокер повідомлень
from services.rabbitmq_client import rabbitmq

class FinanceClient:
    """
    Адаптер для зв'язку між модулем Продажів (Orders) та Фінансами (Finance).
    Тепер працює АСИНХРОННО через RabbitMQ (Event-Driven Architecture).
    Це робить збереження чека миттєвим і повністю ізолює бази даних.
    """
    
    @staticmethod
    def register_order_income(db: Session, order_id: int, total_price: float, payment_method: str, user_id: int):
        """Відправляє подію про новий дохід від продажу у чергу"""
        try:
            # 1. Формуємо "тіло" повідомлення (Payload)
            event_data = {
                "event_type": "order_paid",
                "order_id": order_id,
                "amount": total_price,
                "payment_method": payment_method,
                "user_id": user_id
            }
            
            # 2. Публікуємо подію в чергу фінансів
            rabbitmq.publish(queue_name="finance_queue", message=event_data)
            
        except Exception as e:
            # Якщо RabbitMQ впав, каса все одно проб'є чек (надійність!)
            print(f"⚠️ [FinanceClient] Помилка відправки в RabbitMQ (order_income): {e}")

    @staticmethod
    def register_supply_expense(db: Session, supply_id: int, total_cost: float, account_id: int, user_id: int):
        """Відправляє подію про нові витрати на закупівлю у чергу"""
        try:
            # 1. Формуємо "тіло" повідомлення
            event_data = {
                "event_type": "supply_paid",
                "supply_id": supply_id,
                "amount": total_cost,
                "account_id": account_id,
                "user_id": user_id
            }
            
            # 2. Публікуємо подію
            rabbitmq.publish(queue_name="finance_queue", message=event_data)
            
        except Exception as e:
            print(f"⚠️ [FinanceClient] Помилка відправки в RabbitMQ (supply_expense): {e}")

    @staticmethod
    def register_order_refund(order_id: int, amount: float, payment_method: str):
        """Відправляє подію про скасування чека та повернення коштів"""
        try:
            event_data = {
                "event_type": "order_refunded",
                "order_id": order_id,
                "amount": amount,
                "payment_method": payment_method
            }
            rabbitmq.publish(queue_name="finance_queue", message=event_data)
        except Exception as e:
            print(f"⚠️ [FinanceClient] Помилка відправки в RabbitMQ (refund): {e}")