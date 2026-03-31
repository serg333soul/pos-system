from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .base import Base

# 1. class Customer(Base):
# --- КЛІЄНТИ (CRM) ---
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
