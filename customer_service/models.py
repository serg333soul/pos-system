# FILE: customer_service/models.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from datetime import datetime
from database import Base # Імпортуємо Base з нашого підключення до БД

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    bonus_balance = Column(Numeric(12, 2), default=0.00)

    created_at = Column(DateTime, default=datetime.utcnow)