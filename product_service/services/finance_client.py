# FILE: product_service/services/finance_client.py

from sqlalchemy.orm import Session
import models, schemas
from services import finance_service

class FinanceClient:
    """
    Адаптер для зв'язку між модулем Продажів (Orders) та Фінансами (Finance).
    Ізолює роутери від прямого доступу до чужих таблиць (Shift, Account, Category).
    """
    @staticmethod
    def register_order_income(db: Session, order_id: int, total_price: float, payment_method: str, user_id: int):
        try:
            # 1. Шукаємо активну касову зміну
            active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
            shift_id = active_shift.id if active_shift else None

            # 2. Визначаємо рахунок (готівка чи картка)
            payment_type = 'bank' if payment_method == 'card' else 'cash'
                
            account = db.query(models.Account).filter(
                models.Account.type == payment_type, 
                models.Account.is_active == True
            ).first()

            # 3. Знаходимо категорію доходу
            category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Продаж товарів").first()

            if account:
                tx_data = schemas.TransactionCreate(
                    amount=total_price,
                    account_id=account.id,
                    category_id=category.id if category else None,
                    shift_id=shift_id,
                    user_id=user_id,
                    reference_type='order',
                    reference_id=order_id,
                    description=f"Оплата замовлення #{order_id}"
                )
                # Створюємо транзакцію в Регістрі!
                finance_service.create_transaction(db, tx_data)
        except Exception as e:
            # У мікросервісах тут буде логіка Message Broker (RabbitMQ / Kafka)
            # яка буде повторювати спроби відправити подію. Поки що просто логуємо.
            print(f"⚠️ [FinanceClient] Помилка створення фінансової транзакції: {e}")

    @staticmethod
    def register_supply_expense(db: Session, supply_id: int, total_cost: float, account_id: int, user_id: int):
        """Реєструє витрати на постачання через сервіс фінансів (Асинхронно/Ізольовано)"""
        try:
            active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
            shift_id = active_shift.id if active_shift else None

            account = db.query(models.Account).filter(models.Account.id == account_id).first()
            category = db.query(models.TransactionCategory).filter(models.TransactionCategory.name == "Закупівля товарів").first()

            if account:
                tx_data = schemas.TransactionCreate(
                    amount=-total_cost, # Витрата йде з мінусом!
                    account_id=account.id,
                    category_id=category.id if category else None,
                    shift_id=shift_id,
                    user_id=user_id,
                    reference_type='supply',
                    reference_id=supply_id,
                    description=f"Оплата накладної #{supply_id}"
                )
                from services import finance_service
                finance_service.create_transaction(db, tx_data)
        except Exception as e:
            print(f"⚠️ [FinanceClient] Помилка створення транзакції закупівлі: {e}")