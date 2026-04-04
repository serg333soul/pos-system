from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Numeric, Float
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from .base import Base


# 1. class Order(Base):
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_price = Column(Float)
    payment_method = Column(String)

    #customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    # 🔥 НОВИЙ М'ЯКИЙ ЗВ'ЯЗОК (Soft Link)
    # Ми прибираємо ForeignKey, залишаємо просто число (і додаємо індекс для швидкості)
    customer_id = Column(Integer, index=True, nullable=True)

    #customer = relationship("Customer")
    # 🔥 Ми кажемо SQLAlchemy: "Зв'язок є логічно, але фізично в базі його не шукай"
    customer = relationship(
        "Customer", 
        primaryjoin="Order.customer_id == foreign(Customer.id)",
        uselist=False
    )
        

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

# 2. class OrderItem(Base):
class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, nullable=True) 
    variant_id = Column(Integer, nullable=True)
    product_name = Column(String)
    quantity = Column(Integer)
    price_at_moment = Column(Float)
    details = Column(String, nullable=True) 
    consumable_overrides = Column(JSON, nullable=True, default=list)
    order = relationship("Order", back_populates="items")
