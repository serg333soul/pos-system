from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

# 1. class Supplier(Base):
# --- ПОСТАЧАННЯ ТА ПАРТІЇ ---
class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True) # Твій "коментар"
    created_at = Column(DateTime, default=datetime.utcnow)

# 2. class Supply(Base):
class Supply(Base):
    __tablename__ = "supplies"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True) # Нове поле
    supplier_name = Column(String, nullable=True) # Залишаємо для історії (snapshot)
    
    items = relationship("SupplyItem", back_populates="supply", cascade="all, delete-orphan")
    supplier = relationship("Supplier")

# 3. class SupplyItem(Base):
class SupplyItem(Base):
    __tablename__ = "supply_items"
    id = Column(Integer, primary_key=True, index=True)
    
    supply_id = Column(Integer, ForeignKey("supplies.id"))
    
    entity_type = Column(String)  # 'ingredient', 'consumable', 'simple_product'
    entity_id = Column(Integer)
    entity_name = Column(String) 
    
    quantity = Column(Float)      # Скільки приїхало початково
    remaining_quantity = Column(Float, default=0.0) # Залишок для FIFO та Manual Batch
    
    cost_per_unit = Column(Float) # Ціна закупівлі одиниці в ЦІЙ партії
    total_cost = Column(Float)    # Загальна вартість рядка
    
    supply = relationship("Supply", back_populates="items")
