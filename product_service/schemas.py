from pydantic import BaseModel, Field
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
    category_id: Optional[int] = None 

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    category_id: Optional[int] = None
    category: Optional[Category] = None
    class Config: from_attributes = True

# --- CONSUMABLES ---
class ConsumableBase(BaseModel):
    name: str
    cost_per_unit: float
    stock_quantity: int

class ConsumableCreate(ConsumableBase):
    category_id: Optional[int] = None 
    unit_id: Optional[int] = None

class Consumable(ConsumableBase):
    id: int
    category_id: Optional[int] = None
    category: Optional[Category] = None
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    class Config: from_attributes = True

# --- LINKS (Зв'язки) ---

# 🔥 FIX: Додаємо extra='ignore', щоб не падати від зайвих полів з фронтенду (name, id...)
class ProductIngredientLink(BaseModel):
    ingredient_id: int
    quantity: float
    class Config:
        extra = 'ignore' 

class ProductIngredientRead(BaseModel):
    ingredient_id: int
    quantity: float
    ingredient_name: Optional[str] = None
    # 🔥 FIX: Додаємо поле name для сумісності з фронтендом
    name: Optional[str] = Field(default=None, alias="ingredient_name") 
    
    class Config: 
        from_attributes = True
        populate_by_name = True # Дозволяє використовувати alias

class ProductConsumableLink(BaseModel):
    consumable_id: int
    quantity: float = 1.0
    class Config:
        extra = 'ignore'

class ProductConsumableRead(BaseModel):
    consumable_id: int
    quantity: float
    consumable_name: Optional[str] = None
    # 🔥 FIX: Додаємо поле name для сумісності з фронтендом
    name: Optional[str] = Field(default=None, alias="consumable_name")

    class Config: 
        from_attributes = True
        populate_by_name = True

# --- Калькулятор ---
class ProductCostCheck(BaseModel):
    master_recipe_id: Optional[int] = None
    output_weight: float = 0.0
    ingredients: List[ProductIngredientLink] = []
    consumables: List[ProductConsumableLink] = []

# --- PROCESSES ---
class ProcessOptionCreate(BaseModel):
    name: str 
class ProcessOption(ProcessOptionCreate):
    id: int
    group_id: int
    class Config: from_attributes = True

class ProcessGroupCreate(BaseModel):
    name: str 
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
    consumables: List[ProductConsumableLink] = []
    ingredients: List[ProductIngredientLink] = []
    # 🔥 FIX: Ігноруємо зайві поля при створенні/оновленні
    class Config: extra = 'ignore'

class Variant(VariantCreate):
    id: int
    # Тут використовуємо Read схеми, які тепер мають поле 'name'
    consumables: List[ProductConsumableRead] = []
    ingredients: List[ProductIngredientRead] = []
    cost_price: float = 0.0
    margin: float = 0.0
    class Config: from_attributes = True

# --- PRODUCTS ---
class ProductBase(BaseModel):
    # min_length=1 гарантує, що порожній рядок не пройде валідацію
    name: str = Field(..., min_length=1, description="Назва товару обов'язкова")
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
    ingredients: List[ProductIngredientLink] = []
    process_group_ids: List[int] = [] 
    # 🔥 FIX: Ігноруємо cost_price, margin та інші поля з фронтенду
    class Config: extra = 'ignore'

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    variants: List[Variant] = [] 
    modifier_groups: List[ModifierGroup] = []
    master_recipe: Optional[MasterRecipe] = None
    
    consumables: List[ProductConsumableRead] = [] 
    ingredients: List[ProductIngredientRead] = []
    
    cost_price: float = 0.0
    margin: float = 0.0
    process_groups: List[ProcessGroup] = []

    class Config: from_attributes = True

# --- DEDUCTION & INVENTORY ---
class StockDeductionItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: float
    order_id: int

class InventoryTransactionRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: str
    change_amount: float
    balance_after: float
    reason: str
    created_at: datetime
    class Config: from_attributes = True

# --- ORDERS ---
class SoldItemModifier(BaseModel):
    modifier_id: int
    class Config: extra = 'ignore' # На всяк випадок

class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[SoldItemModifier] = []
    quantity: int

class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str
    customer_id: Optional[int] = None
    class Config: extra = 'ignore'

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