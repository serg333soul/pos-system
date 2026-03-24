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
    return db.query(models.Account).offset(skip).limit(limit).all()

# ==========================================
# 2. КАТЕГОРІЇ ТРАНЗАКЦІЙ (CATEGORIES)
# ==========================================

@router.post("/categories/", response_model=schemas.TransactionCategoryResponse)
def create_category(cat_data: schemas.TransactionCategoryCreate, db: Session = Depends(database.get_db)):
    new_cat = models.TransactionCategory(
        name=cat_data.name,
        type=cat_data.type,
        description=cat_data.description
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/categories/", response_model=List[schemas.TransactionCategoryResponse])
def get_categories(type: Optional[str] = None, db: Session = Depends(database.get_db)):
    query = db.query(models.TransactionCategory)
    if type:
        query = query.filter(models.TransactionCategory.type == type)
    return query.all()

# ==========================================
# 3. КАСОВІ ЗМІНИ (SHIFTS)
# ==========================================

@router.post("/shifts/open", response_model=schemas.ShiftResponse)
def open_shift(shift_data: schemas.ShiftCreate, db: Session = Depends(database.get_db)):
    return finance_service.open_shift(db, shift_data)

@router.get("/shifts/active", response_model=schemas.ShiftResponse)
def get_active_shift(db: Session = Depends(database.get_db)):
    shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Немає активної зміни")
    return shift

@router.post("/shifts/{shift_id}/close", response_model=schemas.ShiftResponse)
def close_shift(shift_id: int, close_data: schemas.ShiftClose, db: Session = Depends(database.get_db)):
    # 🔥 ВИПРАВЛЕНО: Шукаємо безпечно за ТИПОМ рахунку, а не за назвою, яку можуть змінити
    cash_account = db.query(models.Account).filter(models.Account.type == "CASH").first()
    safe_account = db.query(models.Account).filter(models.Account.type == "SAFE").first()

    if not cash_account or not safe_account:
        raise HTTPException(status_code=500, detail="Системна помилка: Не знайдено рахунок 'Каса' (CASH) або 'Сейф' (SAFE) у базі.")

    # Користувача беремо з токена (поки хардкод 1)
    current_user_id = 1 

    closed_shift = finance_service.close_shift(
        db=db,
        shift_id=shift_id,
        close_data=close_data,
        cash_account_id=cash_account.id,
        safe_account_id=safe_account.id,
        user_id=current_user_id
    )
    return closed_shift

# ==========================================
# 4. ТРАНЗАКЦІЇ ТА ПЕРЕКАЗИ
# ==========================================

@router.post("/transactions/", response_model=schemas.TransactionResponse)
def add_transaction(trans_data: schemas.TransactionCreate, db: Session = Depends(database.get_db)):
    return finance_service.create_transaction(db, trans_data)

@router.get("/transactions/", response_model=List[schemas.TransactionResponse])
def get_transactions(
    account_id: Optional[int] = None,
    shift_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Transaction)
    if account_id:
        query = query.filter(models.Transaction.account_id == account_id)
    if shift_id:
        query = query.filter(models.Transaction.shift_id == shift_id)
        
    return query.order_by(models.Transaction.timestamp.desc()).offset(skip).limit(limit).all()

@router.get("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(database.get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Транзакцію не знайдено")
    return tx

@router.post("/transfers/")
def transfer_money(transfer_data: schemas.TransferCreate, db: Session = Depends(database.get_db)):
    return finance_service.transfer_funds(db, transfer_data)

# ==========================================
# 5. ЗВІТИ (REPORTS)
# ==========================================

@router.get("/reports/pnl")
def get_profit_and_loss_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(database.get_db)
):
    """
    Звіт P&L (Прибутки та Збитки).
    """
    # 🔥 ВИПРАВЛЕНО: Роутер тепер чистий і лише викликає сервіс
    return finance_service.generate_pnl_report(db, start_date, end_date)