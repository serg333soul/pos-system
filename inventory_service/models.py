# FILE: inventory_service/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base # Беремо з нашого нового універсального database.py

# --- ОДИНИЦІ ВИМІРУ (мл, грами, шт) ---
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    symbol = Column(String)

# --- ІНГРЕДІЄНТИ (Кава, Молоко, Сиропи) ---
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float, default=0.0)
    stock_quantity = Column(Float, default=0.0)
    category_id = Column(Integer, nullable=True)
    
    # Жорсткий зв'язок, бо Unit живе в цій же базі!
    unit_id = Column(Integer, ForeignKey("units.id"))
    costing_method = Column(String, default='wac')
    
    unit = relationship("Unit")

# --- ВИТРАТНІ МАТЕРІАЛИ (Стаканчики, Кришки) ---
class Consumable(Base):
    __tablename__ = "consumables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float, default=0.0)
    stock_quantity = Column(Integer, default=0)
    
    # Жорсткий зв'язок
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    costing_method = Column(String, default='wac')
    category_id = Column(Integer, nullable=True)
    
    unit = relationship("Unit")

# --- ІСТОРІЯ ТРАНЗАКЦІЙ СКЛАДУ ---
class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True) # 'ingredient' або 'consumable'
    entity_id = Column(Integer, index=True)
    entity_name = Column(String)
    change_amount = Column(Float)
    balance_after = Column(Float)
    reason = Column(String) # Наприклад: "sale_order_15" або "manual_adjustment"
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

class Supply(Base):
    __tablename__ = "supplies"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True) 
    supplier_name = Column(String, nullable=True) 
    
    items = relationship("SupplyItem", back_populates="supply", cascade="all, delete-orphan")
    supplier = relationship("Supplier")

class SupplyItem(Base):
    __tablename__ = "supply_items"
    id = Column(Integer, primary_key=True, index=True)
    supply_id = Column(Integer, ForeignKey("supplies.id"))
    entity_type = Column(String)  # 'ingredient', 'consumable'
    entity_id = Column(Integer)
    entity_name = Column(String) 
    quantity = Column(Float)      
    remaining_quantity = Column(Float, default=0.0) 
    cost_per_unit = Column(Float)
    total_cost = Column(Float)
    
    supply = relationship("Supply", back_populates="items")

# Журнал ідемпотентності (захист від дублікатів RabbitMQ)
class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    id = Column(Integer, primary_key=True, index=True)
    # Зберігатимемо унікальний ідентифікатор події, наприклад "sale_order_105"
    event_id = Column(String, unique=True, index=True) 
    processed_at = Column(DateTime, default=datetime.utcnow)