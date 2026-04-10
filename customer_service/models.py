# FILE: customer_service/models.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
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

# 🔥 НОВА ТАБЛИЦЯ: Історія бонусів та ІДЕМПОТЕНТНІСТЬ
class BonusTransaction(Base):
    __tablename__ = "bonus_transactions"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"))
    
    # Головний захист від дублікатів: один order_id може бути в цій таблиці лише один раз
    order_id = Column(Integer, unique=True, index=True) 
    
    bonuses_spent = Column(Numeric(12, 2), default=0.00)
    bonuses_earned = Column(Numeric(12, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)