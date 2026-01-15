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

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    class Config: from_attributes = True
class IngredientCreate(BaseModel):
    name: str
    cost_per_unit: float
    stock_quantity: float
    unit_id: int

# --- НОВЕ: MASTER RECIPES ---
class MasterRecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: float

class MasterRecipeItem(MasterRecipeItemCreate):
    id: int
    # Для зручності на фронті
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
    master_recipe_id: Optional[int] = None # <-- НОВЕ

class Variant(VariantCreate):
    id: int
    class Config: from_attributes = True

# --- PRODUCTS ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    has_variants: bool = False
    price: float = 0.0 
    master_recipe_id: Optional[int] = None # <-- НОВЕ

class ProductCreate(ProductBase):
    variants: List[VariantCreate] = []
    modifier_groups: List[ModifierGroupCreate] = []

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    variants: List[Variant] = []
    modifier_groups: List[ModifierGroup] = []
    
    # Для відображення назви рецепту на фронті
    master_recipe: Optional[MasterRecipe] = None

    class Config: from_attributes = True

# --- ORDERS ---
class SoldItemModifier(BaseModel):
    modifier_id: int
class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[SoldItemModifier] = []
    quantity: int
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