from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- BASIC ---
class Category(BaseModel):
    id: int
    name: str
    slug: str
    color: Optional[str] = "#ffffff"
    parent_id: Optional[int] = None
    class Config: from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    slug: str
    color: Optional[str] = "#ffffff"
    parent_id: Optional[int] = None

class Unit(BaseModel):
    id: int
    name: str
    symbol: str
    class Config: from_attributes = True
class UnitCreate(BaseModel):
    name: str
    symbol: str

class IngredientCreate(BaseModel):
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit_id: int
    # Без нього API не прийме категорію при створенні
    category_id: Optional[int] = None 

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    
    # 👇 ЦІ РЯДКИ ТРЕБА ДЛЯ ЧИТАННЯ (Вже є у тебе, але перевір тип category)
    category_id: Optional[int] = None
    category: Optional[Category] = None # Щоб фронтенд міг показати назву категорії
    
    class Config:
        from_attributes = True   

# --- CONSUMABLES ---
class ConsumableBase(BaseModel):
    name: str
    cost_per_unit: float
    stock_quantity: int
    # category_id тут не додаємо, щоб не ламати логіку Base

class ConsumableCreate(ConsumableBase):
    # 👇 ДОДАНО: Дозволяємо приймати ID категорії при створенні
    category_id: Optional[int] = None 
    unit_id: Optional[int] = None

class Consumable(ConsumableBase):
    id: int
    
    # 👇 ДОДАНО: Щоб фронтенд бачив категорію
    category_id: Optional[int] = None
    category: Optional[Category] = None

    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    
    class Config:
        from_attributes = True

# Схема для запису (Link)
class ProductIngredientLink(BaseModel):
    ingredient_id: int
    quantity: float

# Схема для читання (Read)
class ProductIngredientRead(BaseModel):
    ingredient_id: int
    quantity: float
    ingredient_name: Optional[str] = None
    class Config: from_attributes = True

# Схема для прив'язки витратних матеріалів до товару (для запису)
class ProductConsumableLink(BaseModel):
    consumable_id: int
    quantity: float = 1.0

# --- ВАЖЛИВО: Переміщено СЮДИ (перед Variants), щоб Pydantic його бачив ---
class ProductConsumableRead(BaseModel):
    consumable_id: int
    quantity: float
    consumable_name: Optional[str] = None
    class Config: from_attributes = True

# --- PROCESSES (НОВЕ) ---
class ProcessOptionCreate(BaseModel):
    name: str # "Дрібний", "Зерно"
class ProcessOption(ProcessOptionCreate):
    id: int
    group_id: int
    class Config: from_attributes = True

class ProcessGroupCreate(BaseModel):
    name: str # "Помол"
    options: List[ProcessOptionCreate] = []

class ProcessGroup(BaseModel):
    id: int
    name: str
    options: List[ProcessOption] = []
    class Config: from_attributes = True

# --- MASTER RECIPES ---
class MasterRecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: float
    is_percentage: bool = False 

class MasterRecipeItem(MasterRecipeItemCreate):
    id: int
    ingredient_name: Optional[str] = None 
    class Config: from_attributes = True

class MasterRecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[MasterRecipeItemCreate] = []

class MasterRecipe(MasterRecipeCreate):
    id: int
    items: List[MasterRecipeItem] = []
    class Config: from_attributes = True

# --- MODIFIERS ---
class ModifierCreate(BaseModel):
    name: str
    price_change: float = 0.0
    ingredient_id: Optional[int] = None
    quantity: float = 0.0
class Modifier(ModifierCreate):
    id: int
    class Config: from_attributes = True
class ModifierGroupCreate(BaseModel):
    name: str
    is_required: bool = False
    modifiers: List[ModifierCreate] = []
class ModifierGroup(ModifierGroupCreate):
    id: int
    modifiers: List[Modifier] = []
    class Config: from_attributes = True

# --- VARIANTS ---
class VariantCreate(BaseModel):
    name: str
    price: float
    sku: Optional[str] = None
    output_weight: float = 0.0
    master_recipe_id: Optional[int] = None
    stock_quantity: float = 0.0
    # При створенні використовуємо Link (тільки ID та кількість)
    consumables: List[ProductConsumableLink] = []

    ingredients: List[ProductIngredientLink] = []

class Variant(VariantCreate):
    id: int
    # При читанні використовуємо Read (з назвою), тепер це працюватиме коректно
    consumables: List[ProductConsumableRead] = []
    ingredients: List[ProductIngredientRead] = []

    cost_price: float = 0.0
    margin: float = 0.0

    class Config: from_attributes = True

# --- PRODUCTS ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    has_variants: bool = False
    price: float = 0.0 
    output_weight: float = 0.0 
    master_recipe_id: Optional[int] = None

    track_stock: bool = False
    stock_quantity: float = 0.0

class ProductCreate(ProductBase):
    variants: List[VariantCreate] = []
    modifier_groups: List[ModifierGroupCreate] = []
    consumables: List[ProductConsumableLink] = []
    
    # НОВЕ: Список ID груп процесів, які треба прив'язати
    process_group_ids: List[int] = [] 

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    variants: List[Variant] = [] 
    modifier_groups: List[ModifierGroup] = []
    master_recipe: Optional[MasterRecipe] = None
    consumables: List[ProductConsumableRead] = [] 
    
    cost_price: float = 0.0
    margin: float = 0.0

    # НОВЕ: Повертаємо повні об'єкти груп процесів
    process_groups: List[ProcessGroup] = []

    class Config: from_attributes = True

class StockDeductionItem(BaseModel):
    id: int
    type: str  # 'product' або 'product_variant'
    quantity: float
    order_id: int

# --- INVENTORY TRANSACTIONS ---
class InventoryTransactionRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: str
    change_amount: float
    balance_after: float
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- ORDERS ---
class SoldItemModifier(BaseModel):
    modifier_id: int
class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[SoldItemModifier] = []
    quantity: int
    # Тут ми не додаємо окреме поле для процесів, 
    # бо вони приходять вже як частина назви або details, сформовані на фронті
    # або ми додамо їх в майбутньому, якщо треба буде.
class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str
    total_price: float
    customer_id: Optional[int] = None

class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None
class Customer(CustomerCreate):
    id: int
    class Config: from_attributes = True

class OrderItemRead(BaseModel):
    product_name: str
    quantity: int
    price_at_moment: float
    details: Optional[str] = None
    class Config: from_attributes = True
class OrderRead(BaseModel):
    id: int
    created_at: datetime
    total_price: float
    payment_method: str
    items: List[OrderItemRead]
    customer: Optional[Customer] = None
    class Config: from_attributes = True