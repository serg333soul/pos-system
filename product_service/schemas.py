from pydantic import BaseModel
from typing import List, Optional 
from datetime import datetime

# --- CATEGORIES ---
class CategoryBase(BaseModel):
    name: str
    slug: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True

# --- UNITS ---
class UnitBase(BaseModel):
    name: str
    symbol: str

class UnitCreate(UnitBase):
    pass

class Unit(UnitBase):
    id: int
    class Config:
        from_attributes = True

# --- INGREDIENTS ---
class IngredientBase(BaseModel):
    name: str
    unit_id: int
    cost_per_unit: float = 0.0
    stock_quantity: float = 0.0

class IngredientCreate(IngredientBase):
    pass

class Ingredient(IngredientBase):
    id: int
    unit: Unit
    class Config:
        from_attributes = True

# --- RECIPE ITEM ---
class RecipeItemBase(BaseModel):
    ingredient_id: int
    quantity: float

class RecipeItemCreate(RecipeItemBase):
    pass

class RecipeItem(RecipeItemBase):
    id: int
    ingredient_name: Optional[str] = None
    class Config:
        from_attributes = True

# --- PRODUCTS (Тут була проблема) ---
class ProductBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    
    # БУЛО: category_id: int
    # СТАЛО (Виправлено):
    category_id: Optional[int] = None 

class ProductCreate(ProductBase):
    recipe: List[RecipeItemCreate] = []

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    recipe: List[RecipeItem] = []

    class Config:
        from_attributes = True

# --- СПИСАННЯ ---
# --- ЗАМОВЛЕННЯ ТА СПИСАННЯ (ОНОВЛЕНО) ---
class SoldItem(BaseModel):
    product_id: int
    quantity: int

# Це те, що приходить від Фронтенду при натисканні "Оплатити"
class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str # "cash" або "card"
    total_price: float

# Це те, як ми будемо віддавати історію замовлень на сторінку Статистики
class OrderItemRead(BaseModel):
    product_name: str
    quantity: int
    price_at_moment: float
    class Config:
        from_attributes = True

class OrderRead(BaseModel):
    id: int
    created_at: datetime
    total_price: float
    payment_method: str
    items: List[OrderItemRead] = []
    class Config:
        from_attributes = True

#class DeductRequest(BaseModel):
#    items: List[SoldItem]
