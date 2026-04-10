from pydantic import BaseModel
from typing import Optional

# Схема для створення (те, що ми отримуємо від фронтенду)
class AccountCreate(BaseModel):
    name: str
    type: str  # 'cash', 'bank' або 'safe'

# Схема для відповіді (те, що ми повертаємо фронтенду)
class Account(BaseModel):
    id: int
    name: str
    type: str
    balance: float
    is_active: bool

    class Config:
        from_attributes = True # Дозволяє Pydantic читати дані прямо з SQLAlchemy моделей