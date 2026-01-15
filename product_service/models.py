from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from database import Base
from datetime import datetime

# --- КАТЕГОРІЇ (ОНОВЛЕНО) ---
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True)
    
    # НОВІ ПОЛЯ
    color = Column(String, default="#ffffff") # Колір категорії (HEX)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True) # Посилання на саму себе
    
    # Зв'язок для отримання дочірніх категорій
    children = relationship("Category", 
                            backref=backref("parent", remote_side=[id]),
                            cascade="all, delete-orphan")

# --- ОДИНИЦІ ВИМІРУ (Без змін) ---
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    symbol = Column(String, unique=True)

# --- ІНГРЕДІЄНТИ (Без змін) ---
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    unit_id = Column(Integer, ForeignKey("units.id"))
    unit = relationship("Unit")
    cost_per_unit = Column(Float, default=0.0)  # Якщо це зміниться, зміниться собівартість всюди
    stock_quantity = Column(Float, default=0.0)

# --- НОВЕ: МАЙСТЕР-РЕЦЕПТИ (ТЕХНОЛОГІЧНІ КАРТИ) ---
class MasterRecipe(Base):
    __tablename__ = "master_recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Напр. "Основа Еспресо"
    description = Column(String, nullable=True)
    
    # Список інгредієнтів у цьому рецепті
    items = relationship("MasterRecipeItem", back_populates="recipe", cascade="all, delete-orphan")

class MasterRecipeItem(Base):
    __tablename__ = "master_recipe_items"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("master_recipes.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float)

    recipe = relationship("MasterRecipe", back_populates="items")
    ingredient = relationship("Ingredient")

# --- МАЙСТЕР-ТОВАР (PRODUCT) ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category")
    
    # Прапорець: чи має цей товар варіанти?
    has_variants = Column(Boolean, default=False)

    # Якщо товар простий (печиво), у нього є ціна. Якщо складний (кава) - ціна 0 (береться з варіантів)
    price = Column(Float, default=0.0)

    # НОВЕ: Посилання на майстер-рецепт
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    master_recipe = relationship("MasterRecipe")

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    modifier_groups = relationship("ProductModifierGroup", back_populates="product", cascade="all, delete-orphan")
    
    # Старе поле recipe (можна залишити для сумісності або видалити пізніше)
    # Ми будемо використовувати master_recipe_id пріоритетно
    # Простий рецепт (для товарів без варіантів, напр. Круасан)
    recipe = relationship("ProductRecipe", back_populates="product", cascade="all, delete-orphan")
    
    
# --- ВАРІАНТИ (НОВЕ) ---
# Наприклад: "Delicate 250g", "Delicate 1kg"
class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    
    name = Column(String) # "250 г" або "Великий"
    price = Column(Float) # 250.00
    sku = Column(String, nullable=True) # Штрих-код
    
    # НОВЕ: Варіант теж може мати свій окремий рецепт (напр. Велика порція)
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    master_recipe = relationship("MasterRecipe")

    product = relationship("Product", back_populates="variants")
    
    # Рецепт конкретно для цього варіанту (напр. 75г кави + 1 пачка 250г)
    variant_recipe = relationship("VariantRecipe", back_populates="variant", cascade="all, delete-orphan")

# --- РЕЦЕПТИ ---

# 1. Для простого товару
class ProductRecipe(Base):
    __tablename__ = "product_recipes"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float)
    
    product = relationship("Product", back_populates="recipe")
    ingredient = relationship("Ingredient")

# 2. Для варіанту (НОВЕ)
class VariantRecipe(Base):
    __tablename__ = "variant_recipes"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float) # Скільки списувати
    
    variant = relationship("ProductVariant", back_populates="variant_recipe")
    ingredient = relationship("Ingredient")

# --- МОДИФІКАТОРИ (НОВЕ) ---
# Група: "Помол", "Молоко"
class ProductModifierGroup(Base):
    __tablename__ = "product_modifier_groups"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String) # "Оберіть помол"
    is_required = Column(Boolean, default=False) # Чи обов'язково обирати?
    
    product = relationship("Product", back_populates="modifier_groups")
    modifiers = relationship("Modifier", back_populates="group", cascade="all, delete-orphan")

# Опція: "Під Еспресо", "Безлактозне молоко"
class Modifier(Base):
    __tablename__ = "modifiers"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("product_modifier_groups.id"))
    name = Column(String) 
    price_change = Column(Float, default=0.0) # +0 грн або +20 грн
    
    # Якщо вибір модифікатора щось списує (напр. коробку)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)
    quantity = Column(Float, default=0.0)

    group = relationship("ProductModifierGroup", back_populates="modifiers")
    ingredient = relationship("Ingredient")

# --- CRM та ORDERS (Без змін структури, тільки логіка) ---
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    total_price = Column(Float)
    payment_method = Column(String)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    customer = relationship("Customer")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    product_name = Column(String)
    quantity = Column(Integer)
    price_at_moment = Column(Float)
    
    # Зберігаємо обрані варіанти та модифікатори текстом для історії
    # Наприклад: "Вага: 250г, Помол: Еспресо"
    details = Column(String, nullable=True) 

    order = relationship("Order", back_populates="items")