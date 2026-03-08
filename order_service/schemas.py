from pydantic import BaseModel
from typing import List, Optional

# 🔥 ДОДАНО: Схема для замін пакування
class ConsumableOverride(BaseModel):
    original_id: int
    new_id: Optional[int] = None

class ModifierItem(BaseModel):
    modifier_id: int

class CartItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[ModifierItem] = []
    quantity: int = 1
    # Ми передаємо ці дані з фронту, щоб кошик не робив запитів до Product Service (швидкодія)
    name: str 
    price: float

    # 🔥 ДОДАНО: Поле для збереження замін пакування в кошику
    consumable_overrides: Optional[List[ConsumableOverride]] = []

class CartItem(CartItemCreate):
    cart_item_id: str # Унікальний ID саме цього рядка в кошику (UUID)