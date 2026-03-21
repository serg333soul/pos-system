from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# --- ПОСТАЧАЛЬНИКИ ---
class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class Supplier(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config: 
        from_attributes = True

# --- ТОВАРИ В НАКЛАДНІЙ ---
class SupplyItemCreate(BaseModel):
    entity_type: str
    entity_id: int
    quantity: float
    cost_per_unit: float

class SupplyItemResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    quantity: float
    cost_per_unit: float
    entity_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- САМА НАКЛАДНА (ПОСТАЧАННЯ) ---
class SupplyCreate(BaseModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[SupplyItemCreate]
    payment_account_id: Optional[int] = None 
    paid_amount: Optional[Decimal] = Decimal('0.00')

class SupplyResponse(BaseModel):
    id: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    total_cost: float
    created_at: datetime
    items: List[SupplyItemResponse] = []
    supplier: Optional[Supplier] = None
    
    class Config:
        from_attributes = True