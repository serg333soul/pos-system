from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

# --- РАХУНКИ (ACCOUNTS) ---
class AccountBase(BaseModel):
    name: str
    type: str
    currency: str = "UAH"
    is_active: bool = True

class AccountCreate(AccountBase):
    initial_balance: Decimal = Decimal('0.00')

class AccountResponse(AccountBase):
    id: int
    balance: Decimal
    class Config: from_attributes = True


# --- КАТЕГОРІЇ ТРАНЗАКЦІЙ ---
class TransactionCategoryCreate(BaseModel):
    name: str
    type: str
    parent_id: Optional[int] = None

class TransactionCategoryResponse(BaseModel):
    id: int
    name: str
    type: str
    parent_id: Optional[int] = None  # 🔥 Додано = None
    class Config: from_attributes = True


# --- КАСОВІ ЗМІНИ (SHIFTS) ---
class ShiftCreate(BaseModel):
    user_id: int
    opening_balance: Decimal = Decimal('0.00')

class ShiftClose(BaseModel):
    closing_balance_actual: Decimal
    transfer_to_safe_amount: Optional[Decimal] = Decimal('0.00')

class ShiftResponse(BaseModel):
    id: int
    user_id: int
    opened_at: datetime
    closed_at: Optional[datetime] = None               # 🔥 Додано = None
    opening_balance: Decimal
    closing_balance_expected: Optional[Decimal] = None # 🔥 Додано = None
    closing_balance_actual: Optional[Decimal] = None   # 🔥 Додано = None
    discrepancy: Decimal
    class Config: from_attributes = True


# --- ТРАНЗАКЦІЇ (TRANSACTIONS) ---
class TransactionCreate(BaseModel):
    amount: Decimal = Field(..., description="Позитивна або негативна сума")
    account_id: int
    category_id: Optional[int] = None
    shift_id: Optional[int] = None
    user_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    description: Optional[str] = None

class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0, description="Сума переказу має бути більшою за 0")
    user_id: int
    shift_id: Optional[int] = None
    description: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    timestamp: datetime
    amount: Decimal
    account_id: int
    category_id: Optional[int] = None           # 🔥 Додано = None
    shift_id: Optional[int] = None              # 🔥 Додано = None
    user_id: int
    reference_type: Optional[str] = None        # 🔥 Додано = None
    reference_id: Optional[int] = None          # 🔥 Додано = None
    description: Optional[str] = None           # 🔥 Додано = None
    linked_transaction_id: Optional[int] = None # 🔥 Додано = None
    class Config: from_attributes = True