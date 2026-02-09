from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship, backref
from database import Base
from datetime import datetime

# --- АСОЦІАТИВНА ТАБЛИЦЯ: ТОВАР <-> ГРУПИ ПРОЦЕСІВ ---
product_process_groups = Table(
    'product_process_groups_link', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('process_group_id', Integer, ForeignKey('process_groups.id'))
)

# --- КАТЕГОРІЇ ---
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True)
    color = Column(String, default="#ffffff")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    children = relationship("Category", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")

# --- ОДИНИЦІ ---
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    symbol = Column(String)

# --- СКЛАД (ІНГРЕДІЄНТИ) ---
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float)
    stock_quantity = Column(Float, default=0.0)
    unit_id = Column(Integer, ForeignKey("units.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    unit = relationship("Unit")
    category = relationship("Category")
    
# --- СКЛАД (ВИТРАТНІ МАТЕРІАЛИ) ---
class Consumable(Base):
    __tablename__ = "consumables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float)
    stock_quantity = Column(Integer, default=0)
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    
    category = relationship("Category")
    unit = relationship("Unit")

# --- ТЕХНОЛОГІЧНІ КАРТИ (РЕЦЕПТИ) ---
class MasterRecipe(Base):
    __tablename__ = "master_recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    items = relationship("MasterRecipeItem", back_populates="recipe", cascade="all, delete-orphan")

class MasterRecipeItem(Base):
    __tablename__ = "master_recipe_items"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("master_recipes.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float) # Кількість (г або %)
    is_percentage = Column(Boolean, default=False) # True = % від ваги виходу, False = грами
    
    recipe = relationship("MasterRecipe", back_populates="items")
    ingredient = relationship("Ingredient")

# --- ПРОЦЕСИ ---
class ProcessGroup(Base):
    __tablename__ = "process_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) # "Помол", "Молоко"
    options = relationship("ProcessOption", back_populates="group", cascade="all, delete-orphan")

class ProcessOption(Base):
    __tablename__ = "process_options"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("process_groups.id"))
    name = Column(String) # "Дрібний", "Зерно"
    group = relationship("ProcessGroup", back_populates="options")

# --- ПРОДУКТИ ТА ВАРІАНТИ ---

# Зв'язок Товар -> Витратний матеріал (Стаканчик)
class ProductConsumable(Base):
    __tablename__ = "product_consumables"
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    consumable_id = Column(Integer, ForeignKey("consumables.id"), primary_key=True)
    quantity = Column(Float, default=1.0)
    
    product = relationship("Product", back_populates="consumables")
    consumable = relationship("Consumable")

# 🔥 НОВЕ: Зв'язок Товар -> Інгредієнт (для простих товарів)
class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity = Column(Float) # Скільки грам йде на цей товар
    
    product = relationship("Product", back_populates="ingredients")
    ingredient = relationship("Ingredient")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Прапорець: чи є варіанти (S/M/L) чи це простий товар
    has_variants = Column(Boolean, default=False)
    
    # Для простих товарів:
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    output_weight = Column(Float, default=0.0) # Вага готового виробу (для розрахунку %)
    
    # Складський облік готового виробу (наприклад, десерти в холодильнику)
    track_stock = Column(Boolean, default=False)
    stock_quantity = Column(Float, default=0.0)

    category = relationship("Category")
    master_recipe = relationship("MasterRecipe")
    
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    modifier_groups = relationship("ProductModifierGroup", back_populates="product", cascade="all, delete-orphan")
    
    consumables = relationship("ProductConsumable", back_populates="product", cascade="all, delete-orphan")
    # 🔥 НОВЕ: Зв'язок з інгредієнтами
    ingredients = relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")
    
    process_groups = relationship("ProcessGroup", secondary=product_process_groups)

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String) # "S", "M", "L" або "На мигдальному"
    price = Column(Float)
    sku = Column(String, nullable=True)
    
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    output_weight = Column(Float, default=0.0)
    
    stock_quantity = Column(Float, default=0.0) # Якщо ведемо облік по варіантах

    master_recipe = relationship("MasterRecipe")
    product = relationship("Product", back_populates="variants")
    
    ingredients = relationship("ProductVariantIngredient", back_populates="variant", cascade="all, delete-orphan")
    consumables = relationship("ProductVariantConsumable", back_populates="variant", cascade="all, delete-orphan")

class ProductVariantIngredient(Base):
    __tablename__ = "product_variant_ingredients"
    variant_id = Column(Integer, ForeignKey("product_variants.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity = Column(Float)
    
    variant = relationship("ProductVariant", back_populates="ingredients")
    ingredient = relationship("Ingredient")

class ProductVariantConsumable(Base):
    __tablename__ = "product_variant_consumables"
    variant_id = Column(Integer, ForeignKey("product_variants.id"), primary_key=True)
    consumable_id = Column(Integer, ForeignKey("consumables.id"), primary_key=True)
    quantity = Column(Integer, default=1)
    
    variant = relationship("ProductVariant", back_populates="consumables")
    consumable = relationship("Consumable")

# --- МОДИФІКАТОРИ (СИРОПИ, МОЛОКО) ---
class ProductModifierGroup(Base):
    __tablename__ = "product_modifier_groups"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String) # "Вибір молока", "Сироп"
    is_required = Column(Boolean, default=False)
    
    product = relationship("Product", back_populates="modifier_groups")
    modifiers = relationship("Modifier", back_populates="group", cascade="all, delete-orphan")

class Modifier(Base):
    __tablename__ = "modifiers"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("product_modifier_groups.id"))
    name = Column(String) # "Кокосове", "Карамельний"
    price_change = Column(Float, default=0.0)
    
    # Що списувати при виборі цього модифікатора
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)
    quantity = Column(Float, default=0.0) # Скільки списувати
    
    group = relationship("ProductModifierGroup", back_populates="modifiers")
    ingredient = relationship("Ingredient")

# --- ЗАМОВЛЕННЯ ---
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
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
    details = Column(String, nullable=True) 
    order = relationship("Order", back_populates="items")

# --- ІСТОРІЯ РУХУ ТОВАРІВ (TRANSACTIONS) ---
class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True) 
    entity_id = Column(Integer, index=True)
    entity_name = Column(String)
    change_amount = Column(Float)
    balance_after = Column(Float)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- КЛІЄНТИ (CRM) ---
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)