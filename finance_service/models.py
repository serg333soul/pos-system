# FILE: finance_service/models.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base # 🔥 Беремо Base з нашого нового файлу підключення

# 1. class Account(Base):
class Account(Base):
    """
    Таблиця Рахунків. 
    Фізичні або віртуальні місця, де зберігаються гроші.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Назва (напр. "Каса 1", "Головний сейф")
    type = Column(String) # Тип: 'cash' (готівка), 'bank' (еквайринг/банк), 'safe' (сейф)
    currency = Column(String, default="UAH") # Мультивалютність (UAH, USD, EUR)
    
    # Використовуємо Numeric(12, 2) для грошей: 12 цифр всього, 2 після коми.
    # Це кешований баланс для швидкого виведення на фронтенді.
    # Реальний баланс завжди можна перерахувати як суму всіх транзакцій.
    balance = Column(Numeric(12, 2), default=0.00) 
    is_active = Column(Boolean, default=True) # Чи можна використовувати цей рахунок

    # Зв'язок з транзакціями (один рахунок має багато транзакцій)
    transactions = relationship("Transaction", back_populates="account")

# 2. class TransactionCategory(Base):
class TransactionCategory(Base):
    """
    Таблиця Категорій транзакцій (Статті витрат/доходів).
    Необхідна для побудови P&L звітів.
    """
    __tablename__ = "transaction_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) # Напр. "Оренда", "Продаж товарів", "Інкасація"
    type = Column(String) # 'INCOME' (Дохід), 'EXPENSE' (Витрата), 'SERVICE' (Службове)
    
    # Для створення дерева категорій (напр. Витрати -> Зарплата -> ЗП Бариста)
    parent_id = Column(Integer, ForeignKey("transaction_categories.id", ondelete="SET NULL"), nullable=True)
    
    transactions = relationship("Transaction", back_populates="category")

# 3. class Shift(Base):
class Shift(Base):
    """
    Таблиця Касових змін.
    Прив'язує фінансові рухи до конкретного робочого дня та касира.
    """
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True) # ID користувача (касира), який відкрив зміну
    opened_at = Column(DateTime, default=datetime.utcnow) # Час відкриття
    closed_at = Column(DateTime, nullable=True) # Час закриття (якщо null - зміна триває)
    
    # Фінансові показники зміни
    opening_balance = Column(Numeric(12, 2), default=0.00) # Гроші в касі на ранок (розмінка)
    closing_balance_expected = Column(Numeric(12, 2), nullable=True) # Скільки має бути по системі
    closing_balance_actual = Column(Numeric(12, 2), nullable=True) # Скільки касир перерахував руками
    discrepancy = Column(Numeric(12, 2), default=0.00) # Нестача (-) або Лишок (+)

    transactions = relationship("Transaction", back_populates="shift")

# 4. class Transaction(Base):
class Transaction(Base):
    """
    Таблиця Транзакцій (Ledger / Регістр).
    СЕРЦЕ системи. Записи тут є незмінними (immutable).
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Сума транзакції. Може бути позитивною (дохід) або негативною (витрата)
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Зовнішні ключі для зв'язків
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"))
    category_id = Column(Integer, ForeignKey("transaction_categories.id", ondelete="RESTRICT"), nullable=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer) # Хто ініціював транзакцію
    
    # Поліморфний зв'язок (Polymorphic Association)
    # Зберігає ЧОМУ виникла транзакція. Напр: type='order', id=105 (Чек №105)
    reference_type = Column(String, index=True, nullable=True) 
    reference_id = Column(Integer, index=True, nullable=True)
    
    # Мультивалютність: курс валюти на момент здійснення операції (щоб історія не ламалась при зміні курсу)
    exchange_rate = Column(Numeric(10, 4), default=1.0000)
    
    # Зв'язок для переміщень (Transfer). 
    # При інкасації створюються 2 транзакції (-500 з Каси, +500 в Сейф). Вони посилаються одна на одну.
    linked_transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    
    description = Column(Text, nullable=True) # Коментар касира ("Заплатив за молоко")

    # Встановлення зв'язків з об'єктами
    account = relationship("Account", back_populates="transactions")
    category = relationship("TransactionCategory", back_populates="transactions")
    shift = relationship("Shift", back_populates="transactions")