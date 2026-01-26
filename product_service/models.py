from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship, backref
from database import Base
from datetime import datetime

# --- АСОЦІАТИВНА ТАБЛИЦЯ: ТОВАР <-> ГРУПИ ПРОЦЕСІВ ---
# Це дозволяє прив'язати "Помол" до "Ефіопії", "Колумбії" і "Бразилії" одночасно
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
    symbol = Column(String, unique=True)

# --- ІНГРЕДІЄНТИ ---
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    unit_id = Column(Integer, ForeignKey("units.id"))
    unit = relationship("Unit")
    cost_per_unit = Column(Float, default=0.0)
    stock_quantity = Column(Float, default=0.0)

# --- ВИТРАТНІ МАТЕРІАЛИ ---
class Consumable(Base):
    __tablename__ = "consumables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    unit = relationship("Unit")
    cost_per_unit = Column(Float, default=0.0)
    stock_quantity = Column(Float, default=0.0)

# --- МАЙСТЕР-РЕЦЕПТИ ---
class MasterRecipe(Base):
    __tablename__ = "master_recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    items = relationship("MasterRecipeItem", back_populates="recipe", cascade="all, delete-orphan")

class MasterRecipeItem(Base):
    __tablename__ = "master_recipe_items"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("master_recipes.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float)
    is_percentage = Column(Boolean, default=False) 
    recipe = relationship("MasterRecipe", back_populates="items")
    ingredient = relationship("Ingredient")

# --- ПРОЦЕСИ (НОВЕ) ---
class ProcessGroup(Base):
    __tablename__ = "process_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Напр: "Помол", "Просмаження"
    
    # Зв'язок один-до-багатьох з опціями
    options = relationship("ProcessOption", back_populates="group", cascade="all, delete-orphan")
    
    # Зв'язок багато-до-багатьох з товарами (зворотній бік)
    products = relationship("Product", secondary=product_process_groups, back_populates="process_groups")

class ProcessOption(Base):
    __tablename__ = "process_options"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("process_groups.id"))
    name = Column(String) # Напр: "Під турку", "Під фільтр"
    
    group = relationship("ProcessGroup", back_populates="options")

# --- ТОВАРИ ---
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category")
    has_variants = Column(Boolean, default=False)
    price = Column(Float, default=0.0)
    output_weight = Column(Float, default=0.0) 
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    master_recipe = relationship("MasterRecipe")

    # --- НОВІ ПОЛЯ ---
    track_stock = Column(Boolean, default=False) # Чи вести складський облік цього товару
    stock_quantity = Column(Float, default=0.0)  # Залишок (для простих товарів)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    modifier_groups = relationship("ProductModifierGroup", back_populates="product", cascade="all, delete-orphan")
    consumables = relationship("ProductConsumable", back_populates="product", cascade="all, delete-orphan")
    # НОВЕ: Зв'язок з групами процесів
    process_groups = relationship("ProcessGroup", secondary=product_process_groups, back_populates="products")

# --- Зв'язок Товар -> Витратні матеріали ---
class ProductConsumable(Base):
    __tablename__ = "product_consumables"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    consumable_id = Column(Integer, ForeignKey("consumables.id"))
    quantity = Column(Float, default=1.0)
    
    product = relationship("Product", back_populates="consumables")
    consumable = relationship("Consumable")

# --- ВАРІАНТИ ---
class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    price = Column(Float)
    sku = Column(String, nullable=True)
    output_weight = Column(Float, default=0.0) 
    master_recipe_id = Column(Integer, ForeignKey("master_recipes.id"), nullable=True)
    master_recipe = relationship("MasterRecipe")

    # --- НОВЕ ПОЛЕ ---
    stock_quantity = Column(Float, default=0.0) # Залишок конкретного варіанту

    product = relationship("Product", back_populates="variants")
    consumables = relationship("ProductVariantConsumable", back_populates="variant", cascade="all, delete-orphan")
    # !!! НОВЕ: Зв'язок з інгредієнтами !!!
    ingredients = relationship("ProductVariantIngredient", back_populates="variant", cascade="all, delete-orphan")

class ProductVariantConsumable(Base):
    __tablename__ = "product_variant_consumables"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    consumable_id = Column(Integer, ForeignKey("consumables.id"))
    quantity = Column(Float, default=1.0)
    
    variant = relationship("ProductVariant", back_populates="consumables")
    consumable = relationship("Consumable")

# !!! НОВИЙ КЛАС: Інгредієнти варіанту !!!
class ProductVariantIngredient(Base):
    __tablename__ = "product_variant_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float, default=0.0) # Скільки грам/мл
    
    variant = relationship("ProductVariant", back_populates="ingredients")
    ingredient = relationship("Ingredient")

# --- МОДИФІКАТОРИ ---
class ProductModifierGroup(Base):
    __tablename__ = "product_modifier_groups"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    is_required = Column(Boolean, default=False)
    product = relationship("Product", back_populates="modifier_groups")
    modifiers = relationship("Modifier", back_populates="group", cascade="all, delete-orphan")

class Modifier(Base):
    __tablename__ = "modifiers"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("product_modifier_groups.id"))
    name = Column(String) 
    price_change = Column(Float, default=0.0)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)
    quantity = Column(Float, default=0.0)
    group = relationship("ProductModifierGroup", back_populates="modifiers")
    ingredient = relationship("Ingredient")

# --- CRM/ORDERS ---
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True)
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
    details = Column(String, nullable=True) 
    order = relationship("Order", back_populates="items")

# --- ІСТОРІЯ РУХУ ТОВАРІВ (TRANSACTIONS) ---
class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Тип сутності: 'ingredient', 'consumable', 'product'
    entity_type = Column(String, index=True) 
    
    # ID сутності (ingredient_id, consumable_id або product_id)
    entity_id = Column(Integer, index=True)
    
    # Назва на момент транзакції (щоб якщо видалили товар, історія лишилась)
    entity_name = Column(String)
    
    # Зміна кількості: +5.0 (прихід), -0.5 (списання)
    change_amount = Column(Float)
    
    # Залишок ПІСЛЯ транзакції (для контролю)
    balance_after = Column(Float)
    
    # Причина: 'manual_update', 'sale_order_#105', 'waste', 'restock'
    reason = Column(String)
    
    created_at = Column(DateTime, default=datetime.now)