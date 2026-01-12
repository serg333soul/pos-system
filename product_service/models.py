from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# --- КАТЕГОРІЇ ---
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True)

# --- ОДИНИЦІ ВИМІРУ (Нове) ---
class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)   # "Кілограм"
    symbol = Column(String, unique=True) # "кг"

# --- ІНГРЕДІЄНТИ (Нове) ---
class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True) # "Молоко", "Кава"
    
    # Зв'язок: Інгредієнт посилається на Одиницю виміру
    unit_id = Column(Integer, ForeignKey("units.id"))
    unit = relationship("Unit")

    # Складський облік
    cost_per_unit = Column(Float, default=0.0)  # Собівартість
    stock_quantity = Column(Float, default=0.0) # Залишок

# --- ТОВАРИ ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float) # Ціна продажу
    description = Column(String, nullable=True)
    
    # Зв'язок з категорією
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category")

    # Зв'язок з рецептом (список інгредієнтів)
    recipe = relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")

# --- РЕЦЕПТ (Зв'язок Товар <-> Інгредієнт) ---
class ProductIngredient(Base):
    __tablename__ = "product_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    
    product_id = Column(Integer, ForeignKey("products.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float) # Скільки цього інгредієнта йде на 1 порцію
    
    # Зв'язки
    product = relationship("Product", back_populates="recipe")
    ingredient = relationship("Ingredient")    

# --- ІСТОРІЯ ЗАМОВЛЕНЬ (НОВЕ) ---
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now) # Дата та час покупки
    total_price = Column(Float) # Загальна сума чеку
    payment_method = Column(String) # "cash" або "card"
    
    # Зв'язок: В одному замовленні багато товарів
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    # Ми зберігаємо назву товару текстом, бо якщо ти видалиш товар "Кава", 
    # в історії він має залишитися як "Кава".
    product_name = Column(String) 
    quantity = Column(Integer)
    price_at_moment = Column(Float) # Ціна на момент покупки (раптом завтра подорожчає)

    order = relationship("Order", back_populates="items")
