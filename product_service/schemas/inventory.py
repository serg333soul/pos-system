from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- КАТЕГОРІЇ ТА ОДИНИЦІ ---
class Category(BaseModel):
    id: int
    name: str
    slug: str
    color: Optional[str] = '#ffffff'
    parent_id: Optional[int] = None
    class Config(): from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    slug: str
    color: Optional[str] = '#ffffff'
    parent_id: Optional[int] = None

class Unit(BaseModel):
    id: int
    name: str
    symbol: str
    class Config(): from_attributes = True

class UnitCreate(BaseModel):
    name: str
    symbol: str

# --- ІНГРЕДІЄНТИ ТА ВИТРАТНИКИ ---
class IngredientCreate(BaseModel):
    name: str
    costing_method: str = 'wac'
    unit_id: int
    category_id: Optional[int] = None

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: Optional[float] = 0.0
    stock_quantity: Optional[float] = 0.0
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    category_id: Optional[int] = None
    category: Optional[Category] = None
    costing_method: str
    class Config():
        from_attributes = True
        extra = 'ignore'

class ConsumableBase(BaseModel):
    name: str
    cost_per_unit: Optional[float] = 0.0
    stock_quantity: Optional[float] = 0.0
    costing_method: str = 'wac'

class ConsumableCreate(ConsumableBase):
    category_id: Optional[int] = None
    unit_id: Optional[int] = None

class Consumable(ConsumableBase):
    id: int
    category_id: Optional[int] = None
    category: Optional[Category] = None
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    class Config(): from_attributes = True

# --- ПРОЦЕСИ ---
class ProcessOptionCreate(BaseModel):
    name: str

class ProcessOption(ProcessOptionCreate):
    id: int
    group_id: int
    class Config(): from_attributes = True

class ProcessGroupCreate(BaseModel):
    name: str
    options: List[ProcessOptionCreate] = []
    parent_option_id: Optional[int] = None

class ProcessGroup(BaseModel):
    id: int
    name: str
    parent_option_id: Optional[int] = None
    options: List[ProcessOption] = []
    class Config(): from_attributes = True

# --- ТЕХНОЛОГІЧНІ КАРТИ ---
class MasterRecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: float
    is_percentage: bool = False

class MasterRecipeItem(MasterRecipeItemCreate):
    id: int
    ingredient_name: Optional[str] = None
    class Config(): from_attributes = True

class MasterRecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[MasterRecipeItemCreate] = []

class MasterRecipe(MasterRecipeCreate):
    id: int
    items: List[MasterRecipeItem] = []
    class Config(): from_attributes = True

# --- МОДИФІКАТОРИ ---
class ModifierCreate(BaseModel):
    name: str
    price_change: float = 0.0
    ingredient_id: Optional[int] = None
    quantity: float = 0.0

class Modifier(ModifierCreate):
    id: int
    class Config(): from_attributes = True

class ModifierGroupCreate(BaseModel):
    name: str
    is_required: bool = False
    modifiers: List[ModifierCreate] = []

class ModifierGroup(ModifierGroupCreate):
    id: int
    modifiers: List[Modifier] = []
    class Config(): from_attributes = True

# --- ЗВ'ЯЗКИ ТОВАРІВ ---
class ProductIngredientLink(BaseModel):
    ingredient_id: int
    quantity: float
    class Config(): extra = 'ignore'

class ProductIngredientRead(BaseModel):
    ingredient_id: int
    quantity: float
    ingredient_name: Optional[str] = None
    name: Optional[str] = Field(default=None, alias='ingredient_name')
    class Config():
        from_attributes = True
        populate_by_name = True

class ProductConsumableLink(BaseModel):
    consumable_id: int
    quantity: float = 1.0
    class Config(): extra = 'ignore'

class ProductConsumableRead(BaseModel):
    consumable_id: int
    quantity: float
    consumable_name: Optional[str] = None
    name: Optional[str] = Field(default=None, alias='consumable_name')
    class Config():
        from_attributes = True
        populate_by_name = True

class ProductCostCheck(BaseModel):
    master_recipe_id: Optional[int] = None
    output_weight: float = 0.0
    ingredients: List[ProductIngredientLink] = []
    consumables: List[ProductConsumableLink] = []

# --- ТОВАРИ ТА ВАРІАНТИ ---
class VariantCreate(BaseModel):
    name: str
    price: float
    sku: Optional[str] = None
    output_weight: float = 0.0
    master_recipe_id: Optional[int] = None
    stock_quantity: float = 0.0
    consumables: List[ProductConsumableLink] = []
    ingredients: List[ProductIngredientLink] = []
    class Config(): extra = 'ignore'

class Variant(VariantCreate):
    id: int
    consumables: List[ProductConsumableRead] = []
    ingredients: List[ProductIngredientRead] = []
    master_recipe: Optional[MasterRecipe] = None
    cost_price: Optional[float] = 0.0
    margin: Optional[float] = 0.0
    class Config(): from_attributes = True

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, description="Назва товару обов'язкова")
    description: Optional[str] = None
    category_id: Optional[int] = None
    has_variants: bool = False
    price: float = 0.0
    output_weight: float = 0.0
    master_recipe_id: Optional[int] = None
    track_stock: bool = False
    stock_quantity: float = 0.0
    room_id: Optional[int] = None

class ProductCreate(ProductBase):
    variants: List[VariantCreate] = []
    modifier_groups: List[ModifierGroupCreate] = []
    consumables: List[ProductConsumableLink] = []
    ingredients: List[ProductIngredientLink] = []
    process_group_ids: List[int] = []
    class Config(): extra = 'ignore'

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    category_id: Optional[int] = None
    has_variants: Optional[bool] = None
    price: Optional[float] = None
    output_weight: Optional[float] = None
    master_recipe_id: Optional[int] = None
    track_stock: Optional[bool] = None
    stock_quantity: Optional[float] = None
    room_id: Optional[int] = None

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    variants: List[Variant] = []
    modifier_groups: List[ModifierGroup] = []
    master_recipe: Optional[MasterRecipe] = None
    consumables: List[ProductConsumableRead] = []
    ingredients: List[ProductIngredientRead] = []
    cost_price: Optional[float] = 0.0
    margin: Optional[float] = 0.0
    process_groups: List[ProcessGroup] = []
    class Config(): from_attributes = True

class ProductRoomCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProductRoomRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    products: List[Product] = []
    class Config(): from_attributes = True

# --- КАЛЬКУЛЯЦІЯ ТА СКЛАД ---
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
    reason: Optional[str] = None
    created_at: datetime
    class Config(): from_attributes = True

class InventoryAdjustRequest(BaseModel):
    entity_type: str
    entity_id: int
    actual_quantity: float
    reason: str
    batch_id: Optional[int] = None