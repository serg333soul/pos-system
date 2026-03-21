from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Table, JSON, Numeric, Text
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from .base import Base

# 1. product_process_groups (Table)
# --- АСОЦІАТИВНА ТАБЛИЦЯ: ТОВАР <-> ГРУПИ ПРОЦЕСІВ ---
product_process_groups = Table(
    'product_process_groups_link', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('process_group_id', Integer, ForeignKey('process_groups.id'))
)
# 2. class Category(Base):
# --- КАТЕГОРІЇ ---
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True)
    color = Column(String, default="#ffffff")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    children = relationship("Category", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
# 3. class Unit(Base):
# --- ОДИНИЦІ ---
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    symbol = Column(String)
# 4. class Ingredient(Base):
# --- СКЛАД (ІНГРЕДІЄНТИ) ---
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float)
    stock_quantity = Column(Float, default=0.0)
    unit_id = Column(Integer, ForeignKey("units.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    costing_method = Column(String, default='wac')
    
    unit = relationship("Unit")
    category = relationship("Category")
# 5. class Consumable(Base):
# --- СКЛАД (ВИТРАТНІ МАТЕРІАЛИ) ---
class Consumable(Base):
    __tablename__ = "consumables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cost_per_unit = Column(Float)
    stock_quantity = Column(Integer, default=0)
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    costing_method = Column(String, default='wac')
    
    category = relationship("Category")
    unit = relationship("Unit")
# 6. class MasterRecipe(Base):
# --- ТЕХНОЛОГІЧНІ КАРТИ (РЕЦЕПТИ) ---
class MasterRecipe(Base):
    __tablename__ = "master_recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    items = relationship("MasterRecipeItem", back_populates="recipe", cascade="all, delete-orphan")
# 7. class MasterRecipeItem(Base):
class MasterRecipeItem(Base):
    __tablename__ = "master_recipe_items"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("master_recipes.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    quantity = Column(Float) # Кількість (г або %)
    is_percentage = Column(Boolean, default=False) # True = % від ваги виходу, False = грами
    
    recipe = relationship("MasterRecipe", back_populates="items")
    ingredient = relationship("Ingredient")
# 8. class ProcessGroup(Base):
# --- ПРОЦЕСИ ---
class ProcessGroup(Base):
    __tablename__ = "process_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) # "Помол", "Молоко"

    # 🔥 НОВЕ: Група може залежати від конкретної опції іншої групи
    parent_option_id = Column(Integer, ForeignKey("process_options.id", ondelete="CASCADE"), nullable=True)

    # Зв'язки
    options = relationship("ProcessOption", foreign_keys="[ProcessOption.group_id]", back_populates="group", cascade="all, delete-orphan")
    parent_option = relationship("ProcessOption", foreign_keys=[parent_option_id], back_populates="child_groups")
# 9. class ProcessOption(Base):
# --- ОПЦІЇ ПРОЦЕСІВ ---
class ProcessOption(Base):
    __tablename__ = "process_options"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("process_groups.id"))
    name = Column(String) # "Дрібний", "Зерно"
    # Зв'язки
    group = relationship("ProcessGroup", foreign_keys=[group_id], back_populates="options")
    # 🔥 Зворотний зв'язок: Групи, які з'являються ТІЛЬКИ якщо обрано цю опцію
    child_groups = relationship("ProcessGroup", foreign_keys="[ProcessGroup.parent_option_id]", back_populates="parent_option")
# 10. class ProductConsumable(Base):
# --- ВИТРАТНІ МАТЕРІАЛИ В ТОВАРАХ ---
# Зв'язок Товар -> Витратний матеріал (Стаканчик)
class ProductConsumable(Base):
    __tablename__ = "product_consumables"
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    consumable_id = Column(Integer, ForeignKey("consumables.id"), primary_key=True)
    quantity = Column(Float, default=1.0)
    
    product = relationship("Product", back_populates="consumables")
    consumable = relationship("Consumable")
# 11. class ProductIngredient(Base):
# 🔥 НОВЕ: Зв'язок Товар -> Інгредієнт (для простих товарів)
class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity = Column(Float) # Скільки грам йде на цей товар
    
    product = relationship("Product", back_populates="ingredients")
    ingredient = relationship("Ingredient")
# 12. class Product(Base):
# --- ТОВАРИ ---
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

    # 🔥 НОВЕ: Зовнішній ключ для зв'язку з кімнатою
    room_id = Column(Integer, ForeignKey("product_rooms.id"), nullable=True)
    room = relationship("ProductRoom", back_populates="products")

    category = relationship("Category")
    master_recipe = relationship("MasterRecipe")
    
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    modifier_groups = relationship("ProductModifierGroup", back_populates="product", cascade="all, delete-orphan")
    
    consumables = relationship("ProductConsumable", back_populates="product", cascade="all, delete-orphan")
    # 🔥 НОВЕ: Зв'язок з інгредієнтами
    ingredients = relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")
    
    process_groups = relationship("ProcessGroup", secondary=product_process_groups)

# 13. class ProductVariant(Base):
# --- ВАРІАНТИ ТОВАРІВ (S/M/L) ---
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

# 14. class ProductRoom(Base):
# --- КІМНАТИ (для групування товарів) ---
class ProductRoom(Base):
    __tablename__ = "product_rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Напр: "Кава Delicate"
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Зв'язок: одна кімната має багато товарів
    products = relationship("Product", back_populates="room")

# 15. class ProductVariantIngredient(Base):
# 🔥 НОВЕ: Зв'язок Варіант товару -> Інгредієнт (для варіантів)
class ProductVariantIngredient(Base):
    __tablename__ = "product_variant_ingredients"
    variant_id = Column(Integer, ForeignKey("product_variants.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity = Column(Float)
    
    variant = relationship("ProductVariant", back_populates="ingredients")
    ingredient = relationship("Ingredient")

# 16. class ProductVariantConsumable(Base):
# 🔥 НОВЕ: Зв'язок Варіант товару -> Витратний матеріал (для варіантів)
class ProductVariantConsumable(Base):
    __tablename__ = "product_variant_consumables"
    variant_id = Column(Integer, ForeignKey("product_variants.id"), primary_key=True)
    consumable_id = Column(Integer, ForeignKey("consumables.id"), primary_key=True)
    quantity = Column(Integer, default=1)
    
    variant = relationship("ProductVariant", back_populates="consumables")
    consumable = relationship("Consumable")

# 17. class ProductModifierGroup(Base):
# --- ГРУПИ МОДИФІКАТОРІВ (наприклад, "Молоко" з опціями "Коров'яче", "Мигдальне") ---
class ProductModifierGroup(Base):
    __tablename__ = "product_modifier_groups"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String) # "Вибір молока", "Сироп"
    is_required = Column(Boolean, default=False)
    
    product = relationship("Product", back_populates="modifier_groups")
    modifiers = relationship("Modifier", back_populates="group", cascade="all, delete-orphan")

# 18. class Modifier(Base):
# --- МОДИФІКАТОРИ (опції в групах модифікаторів) ---
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

# 19. class InventoryTransaction(Base):
# --- ТРАНЗАКЦІЇ СКЛАДУ (для історії змін) ---
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