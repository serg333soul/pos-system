from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None

class Customer(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config: 
        from_attributes = True