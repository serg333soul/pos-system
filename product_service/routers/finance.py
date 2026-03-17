# FILE: product_service/routers/finance.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

import database, schemas, models
from services import finance_service

router = APIRouter(prefix="/finance", tags=["Finance"])

# ==========================================
# 1. РАХУНКИ (ACCOUNTS)
# ==========================================

@router.post("/accounts/", response_model=schemas.AccountResponse)
def create_account(account_data: schemas.AccountCreate, db: Session = Depends(database.get_db)):
    """Створення нового фінансового рахунку (каса, сейф, банк)."""
    new_account = models.Account(
        name=account_data.name,
        type=account_data.type,
        currency=account_data.currency,
        balance=account_data.initial_balance,
        is_active=account_data.is_active
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@router.get("/accounts/", response_model=List[schemas.AccountResponse])
def get_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """Отримання списку всіх рахунків."""
    return db.query(models.Account).offset(skip).limit(limit).all()

# ==========================================
# 2. КАТЕГОРІЇ ТРАНЗАКЦІЙ (CATEGORIES)
# ==========================================

@router.post("/categories/", response_model=schemas.TransactionCategoryResponse)
def create_category(category_data: schemas.TransactionCategoryCreate, db: Session = Depends(database.get_db)):
    """Створення нової категорії доходів/витрат."""
    new_category = models.TransactionCategory(
        name=category_data.name,
        type=category_data.type,
        parent_id=category_data.parent_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.get("/categories/", response_model=List[schemas.TransactionCategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(database.get_db)):
    """Отримання списку категорій (опціонально з фільтром по типу)."""
    query = db.query(models.TransactionCategory)
    if type:
        query = query.filter(models.TransactionCategory.type == type)
    return query.all()

# ==========================================
# 3. КАСОВІ ЗМІНИ (SHIFTS)
# ==========================================

@router.post("/shifts/open", response_model=schemas.ShiftResponse)
def open_shift(shift_data: schemas.ShiftCreate, db: Session = Depends(database.get_db)):
    """Відкриття нової касової зміни."""
    return finance_service.open_shift(db=db, shift_data=shift_data)

@router.post("/shifts/{shift_id}/close", response_model=schemas.ShiftResponse)
def close_shift(
    shift_id: int, 
    close_data: schemas.ShiftClose,
    cash_account_id: int = Query(..., description="ID рахунку Готівкової Каси"),
    safe_account_id: int = Query(..., description="ID рахунку Головного Сейфу"),
    user_id: int = Query(..., description="ID касира, який закриває зміну"),
    db: Session = Depends(database.get_db)
):
    """Закриття касової зміни (Z-звіт) з інкасацією."""
    return finance_service.close_shift(
        db=db,
        shift_id=shift_id,
        close_data=close_data,
        cash_account_id=cash_account_id,
        safe_account_id=safe_account_id,
        user_id=user_id
    )

@router.get("/shifts/active", response_model=Optional[schemas.ShiftResponse])
def get_active_shift(db: Session = Depends(database.get_db)):
    """Отримання поточної відкритої зміни (якщо є)."""
    return db.query(models.Shift).filter(models.Shift.closed_at == None).first()

# ==========================================
# 4. ТРАНЗАКЦІЇ ТА ПЕРЕКАЗИ (TRANSACTIONS)
# ==========================================

@router.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(trans_data: schemas.TransactionCreate, db: Session = Depends(database.get_db)):
    """
    Створення ручної транзакції.
    (Наприклад: внесення розмінної монети, оплата кур'єру з каси).
    """
    return finance_service.create_transaction(db=db, trans_data=trans_data)

@router.post("/transactions/transfer")
def transfer_funds(transfer_data: schemas.TransferCreate, db: Session = Depends(database.get_db)):
    """
    Переміщення коштів між рахунками (Інкасація або поповнення).
    """
    return finance_service.transfer_funds(db=db, transfer_data=transfer_data)

@router.get("/transactions/", response_model=List[schemas.TransactionResponse])
def get_transactions(
    account_id: Optional[int] = None,
    shift_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    """Отримання історії транзакцій (Ledger) з можливістю фільтрації."""
    query = db.query(models.Transaction)
    if account_id:
        query = query.filter(models.Transaction.account_id == account_id)
    if shift_id:
        query = query.filter(models.Transaction.shift_id == shift_id)
    
    return query.order_by(models.Transaction.timestamp.desc()).offset(skip).limit(limit).all()

# ==========================================
# 5. ЗВІТИ (REPORTS)
# ==========================================

@router.get("/report/pnl")
def get_pnl_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(database.get_db)
):
    """
    Генерує звіт P&L (Прибутки та збитки) згрупований по категоріях.
    """
    # Будуємо запит: об'єднуємо транзакції з категоріями і рахуємо суму
    query = db.query(
        models.TransactionCategory.name,
        models.TransactionCategory.type,
        func.sum(models.Transaction.amount).label('total')
    ).join(
        models.Transaction, models.Transaction.category_id == models.TransactionCategory.id
    )

    # Фільтри по даті (для майбутнього масштабування, щоб дивитись звіт за місяць)
    if start_date:
        query = query.filter(models.Transaction.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Transaction.timestamp <= end_date)

    # Групуємо за категорією
    results = query.group_by(models.TransactionCategory.name, models.TransactionCategory.type).all()

    # Формуємо структуру звіту
    report = {
        "income": {},          # Деталізація доходів
        "expense": {},         # Деталізація витрат
        "total_income": 0.0,
        "total_expense": 0.0,
        "net_profit": 0.0      # Чистий прибуток
    }

    for name, cat_type, total in results:
        amount = float(total)
        if cat_type == 'INCOME':
            report["income"][name] = amount
            report["total_income"] += amount
        elif cat_type == 'EXPENSE':
            # Транзакції витрат у нас з мінусом, тому беремо модулі (abs) для красивого відображення
            report["expense"][name] = abs(amount)
            report["total_expense"] += abs(amount)

    # Рахуємо чистий прибуток
    report["net_profit"] = report["total_income"] - report["total_expense"]

    return report