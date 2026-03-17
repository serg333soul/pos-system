from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

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

class IngredientCreate(BaseModel):
    name: str
    #cost_per_unit: float
    costing_method: str = "wac"
    unit_id: int
    category_id: Optional[int] = None 

class Ingredient(BaseModel):
    id: int
    name: str
    cost_per_unit: float
    
    stock_quantity: float
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    category_id: Optional[int] = None
    category: Optional[Category] = None
    costing_method: str
    class Config: from_attributes = True
    class Config:
        from_attributes = True
        extra = 'ignore' # Ігноруємо зайві поля з фронтенду (наприклад, cost_per_unit при створенні)

# --- CONSUMABLES ---
class ConsumableBase(BaseModel):
    name: str
    cost_per_unit: float
    stock_quantity: float
    costing_method: str = "wac"

class ConsumableCreate(ConsumableBase):
    category_id: Optional[int] = None 
    unit_id: Optional[int] = None

class Consumable(ConsumableBase):
    id: int
    category_id: Optional[int] = None
    category: Optional[Category] = None
    unit_id: Optional[int] = None
    unit: Optional[Unit] = None
    class Config: from_attributes = True

# --- LINKS (Зв'язки) ---

# 🔥 FIX: Додаємо extra='ignore', щоб не падати від зайвих полів з фронтенду (name, id...)
class ProductIngredientLink(BaseModel):
    ingredient_id: int
    quantity: float
    class Config:
        extra = 'ignore' 

class ProductIngredientRead(BaseModel):
    ingredient_id: int
    quantity: float
    ingredient_name: Optional[str] = None
    # 🔥 FIX: Додаємо поле name для сумісності з фронтендом
    name: Optional[str] = Field(default=None, alias="ingredient_name") 
    
    class Config: 
        from_attributes = True
        populate_by_name = True # Дозволяє використовувати alias

class ProductConsumableLink(BaseModel):
    consumable_id: int
    quantity: float = 1.0
    class Config:
        extra = 'ignore'

class ProductConsumableRead(BaseModel):
    consumable_id: int
    quantity: float
    consumable_name: Optional[str] = None
    # 🔥 FIX: Додаємо поле name для сумісності з фронтендом
    name: Optional[str] = Field(default=None, alias="consumable_name")

    class Config: 
        from_attributes = True
        populate_by_name = True

# --- Калькулятор ---
class ProductCostCheck(BaseModel):
    master_recipe_id: Optional[int] = None
    output_weight: float = 0.0
    ingredients: List[ProductIngredientLink] = []
    consumables: List[ProductConsumableLink] = []

# --- PROCESSES ---
class ProcessOptionCreate(BaseModel):
    name: str 
class ProcessOption(ProcessOptionCreate):
    id: int
    group_id: int
    class Config: from_attributes = True

class ProcessGroupCreate(BaseModel):
    name: str 
    options: List[ProcessOptionCreate] = []
    parent_option_id: Optional[int] = None

class ProcessGroup(BaseModel):
    id: int
    name: str
    parent_option_id: Optional[int] = None
    options: List[ProcessOption] = []
    class Config: from_attributes = True

# --- MASTER RECIPES ---
class MasterRecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: float
    is_percentage: bool = False 

class MasterRecipeItem(MasterRecipeItemCreate):
    id: int
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
    output_weight: float = 0.0
    master_recipe_id: Optional[int] = None
    stock_quantity: float = 0.0
    consumables: List[ProductConsumableLink] = []
    ingredients: List[ProductIngredientLink] = []
    # 🔥 FIX: Ігноруємо зайві поля при створенні/оновленні
    class Config: extra = 'ignore'

class Variant(VariantCreate):
    id: int
    # Тут використовуємо Read схеми, які тепер мають поле 'name'
    consumables: List[ProductConsumableRead] = []
    ingredients: List[ProductIngredientRead] = []
    master_recipe: Optional[MasterRecipe] = None
    cost_price: float = 0.0
    margin: float = 0.0
    class Config: from_attributes = True

# --- PRODUCTS ---
class ProductBase(BaseModel):
    # min_length=1 гарантує, що порожній рядок не пройде валідацію
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
    # 🔥 FIX: Ігноруємо cost_price, margin та інші поля з фронтенду
    class Config: extra = 'ignore'

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    variants: List[Variant] = [] 
    modifier_groups: List[ModifierGroup] = []
    master_recipe: Optional[MasterRecipe] = None
    
    consumables: List[ProductConsumableRead] = [] 
    ingredients: List[ProductIngredientRead] = []
    
    cost_price: float = 0.0
    margin: float = 0.0
    process_groups: List[ProcessGroup] = []

    class Config: from_attributes = True

# --- DEDUCTION & INVENTORY ---
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
    reason: str
    created_at: datetime
    class Config: from_attributes = True

# --- ORDERS ---
class SoldItemModifier(BaseModel):
    modifier_id: int
    class Config: extra = 'ignore' # На всяк випадок

# 🔥 НОВА СХЕМА: Інструкція від касира про заміну матеріалу
class ConsumableOverride(BaseModel):
    original_id: int           # ID матеріалу, який мав би списатися за замовчуванням
    new_id: Optional[int] = None # ID нового матеріалу (Якщо None/null - значить касир натиснув "Видалити / Своя чашка")
class SoldItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    modifiers: List[SoldItemModifier] = []
    quantity: int
    # 🔥 НОВЕ: Масив усіх замін пакування, які зробив касир у вікні товару
    consumable_overrides: Optional[List[ConsumableOverride]] = []
class OrderCreate(BaseModel):
    items: List[SoldItem]
    payment_method: str
    customer_id: Optional[int] = None
    
    class Config: extra = 'ignore'
    
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
    consumable_overrides: Optional[List[ConsumableOverride]] = []
    class Config: from_attributes = True

class OrderRead(BaseModel):
    id: int
    created_at: datetime
    total_price: float
    payment_method: str
    items: List[OrderItemRead]
    customer: Optional[Customer] = None
    class Config: from_attributes = True

class ProductRoomRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    # Список товарів у кімнаті з усіма вкладеними даними (процеси, матеріали)
    products: List[Product] 

    class Config:
        from_attributes = True

class ProductRoomCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class Supplier(SupplierCreate):
    id: int
    class Config: from_attributes = True

class SupplyItemCreate(BaseModel):
    entity_type: str
    entity_id: int
    quantity: float
    cost_per_unit: float

# 🔥 НОВА СХЕМА ДЛЯ ВІДПОВІДІ (Response)
class SupplyItemResponse(SupplyItemCreate):
    id: int
    entity_name: Optional[str] = None # Це те, чого не вистачало

    class Config:
        from_attributes = True

class SupplyCreate(BaseModel):
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[SupplyItemCreate]

    payment_account_id: Optional[int] = None # ID рахунку, з якого платимо (напр. Каса 1 або ФОП)
    paid_amount: Optional[Decimal] = Decimal('0.00') # Скільки саме заплатили (може бути часткова оплата)

class SupplyResponse(BaseModel):
    id: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    total_cost: float
    created_at: datetime
    # 🔥 ВИКОРИСТОВУЄМО НОВУ СХЕМУ ТУТ
    items: List[SupplyItemResponse] 
    supplier: Optional[Supplier] = None
    
    class Config:
        from_attributes = True

class OrderPaginationResponse(BaseModel):
    total: int
    items: List[OrderRead]
    page: int
    pages: int

    class Config:
        from_attributes = True

class InventoryAdjustRequest(BaseModel):
    entity_type: str  # 'ingredient', 'consumable', 'product', 'product_variant'
    entity_id: int
    actual_quantity: float  # Фактичний залишок, який ввів менеджер
    reason: str             # Причина коригування
    batch_id: Optional[int] = None  # ID партії (опціонально, якщо це FIFO)

# --- РАХУНКИ (ACCOUNTS) ---
class AccountBase(BaseModel):
    name: str
    type: str # 'cash', 'bank', 'safe'
    currency: Optional[str] = "UAH"
    is_active: Optional[bool] = True

class AccountCreate(AccountBase):
    initial_balance: Optional[Decimal] = Decimal('0.00') # Можливість задати стартовий баланс

class AccountResponse(AccountBase):
    id: int
    balance: Decimal
    
    class Config:
        from_attributes = True

# --- КАТЕГОРІЇ ТРАНЗАКЦІЙ ---
class TransactionCategoryCreate(BaseModel):
    name: str
    type: str # 'INCOME', 'EXPENSE', 'SERVICE'
    parent_id: Optional[int] = None

class TransactionCategoryResponse(TransactionCategoryCreate):
    id: int
    class Config:
        from_attributes = True

# --- ЗМІНИ (SHIFTS) ---
class ShiftCreate(BaseModel):
    user_id: int
    opening_balance: Decimal

class ShiftClose(BaseModel):
    closing_balance_actual: Decimal # Скільки реально нарахував касир
    transfer_to_safe_amount: Optional[Decimal] = Decimal('0.00') # Скільки він забирає в сейф на ніч

class ShiftResponse(BaseModel):
    id: int
    user_id: int
    opened_at: datetime
    closed_at: Optional[datetime]
    opening_balance: Decimal
    closing_balance_expected: Optional[Decimal]
    closing_balance_actual: Optional[Decimal]
    discrepancy: Decimal
    
    class Config:
        from_attributes = True

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
    """Спеціальна схема для операції переміщення (Інкасації)"""
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0, description="Сума переказу має бути більшою за 0")
    user_id: int
    shift_id: Optional[int] = None
    description: Optional[str] = "Переміщення коштів"

class TransactionResponse(BaseModel):
    id: int
    timestamp: datetime
    amount: Decimal
    account_id: int
    category_id: Optional[int]
    reference_type: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True