from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 🔥 Імпортуємо тільки Customer (залежності від inventory більше немає!)
from .crm import Customer

# --- МОДИФІКАТОРИ ТА ПАКУВАННЯ ---
class SoldItemModifier(BaseModel):
    modifier_id: int
    
    class Config: 
        extra = 'ignore'

class ConsumableOverride(BaseModel):
    original_id: int           
    new_id: Optional[int] = None 

# --- СТВОРЕННЯ ЧЕКА (ВІД КАСИРА) ---
class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[SoldItemModifier] = []
    quantity: int
    consumable_overrides: Optional[List[ConsumableOverride]] = []

class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str
    customer_id: Optional[int] = None
    use_bonuses: bool = False
    
    class Config: 
        extra = 'ignore'

# --- ВІДОБРАЖЕННЯ ЧЕКА (ДЛЯ ІСТОРІЇ/ЗВІТІВ) ---
class OrderItemRead(BaseModel):
    product_name: str
    quantity: int
    price_at_moment: float
    details: Optional[str] = None
    consumable_overrides: Optional[List[ConsumableOverride]] = []
    
    class Config: 
        from_attributes = True

class OrderRead(BaseModel):
    id: int
    created_at: datetime
    total_price: float
    payment_method: str
    customer_id: Optional[int] = None
    bonuses_spent: Optional[float] = 0.0
    items: List[OrderItemRead] = []
    customer: Optional[Customer] = None
    
    class Config: 
        from_attributes = True

# --- ПАГІНАЦІЯ ДЛЯ СПИСКУ ЧЕКІВ ---
class OrderPaginationResponse(BaseModel):
    total: int
    items: List[OrderRead] = []
    page: int
    pages: int

    class Config:
        from_attributes = True