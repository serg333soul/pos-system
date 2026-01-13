from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- BASIC (Categories, Units, Ingredients) ---
class Category(BaseModel):
    id: int
    name: str
    slug: str
    class Config: from_attributes = True

class Unit(BaseModel):
    id: int
    name: str
    symbol: str
    class Config: from_attributes = True

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit: Optional[Unit] = None
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

# --- RECIPES ---
class RecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: float

class RecipeItem(RecipeItemCreate):
    ingredient_name: Optional[str] = None
    class Config: from_attributes = True

# --- VARIANTS ---
class VariantCreate(BaseModel):
    name: str
    price: float
    sku: Optional[str] = None
    recipe: List[RecipeItemCreate] = []

class Variant(VariantCreate):
    id: int
    recipe: List[RecipeItem] = [] # (Це заповниться з variant_recipe в main.py)
    class Config: from_attributes = True

# --- PRODUCTS ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    has_variants: bool = False
    price: float = 0.0 # Базова ціна (для простих товарів)

class ProductCreate(ProductBase):
    # Або простий рецепт
    recipe: List[RecipeItemCreate] = []
    # Або варіанти
    variants: List[VariantCreate] = []
    # Модифікатори
    modifier_groups: List[ModifierGroupCreate] = []

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    
    # Поля для читання
    recipe: List[RecipeItem] = []
    variants: List[Variant] = []
    modifier_groups: List[ModifierGroup] = []

    class Config:
        from_attributes = True

# --- ORDERS ---
class SoldItemModifier(BaseModel):
    modifier_id: int

class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None # Якщо товар з варіантами
    modifiers: List[SoldItemModifier] = [] # Обрані модифікатори
    quantity: int

class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str
    total_price: float
    customer_id: Optional[int] = None

class Customer(BaseModel):
    id: int
    name: str
    phone: str
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