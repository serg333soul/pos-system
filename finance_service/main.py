# FILE: finance_service/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime
import models
import schemas
from database import get_db

app = FastAPI(title="POS Finance API")

# Налаштування CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Рахунки (зверніть увагу на слеш наприкінці)
@app.get("/finance/accounts/")
def get_accounts(db: Session = Depends(get_db)):
    return db.query(models.Account).all()

# 2. Категорії транзакцій
@app.get("/finance/categories/")
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.TransactionCategory).all()

# 3. Історія транзакцій
@app.get("/finance/transactions/")
def get_transactions(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).limit(limit).all()

# 4. Перевірка активної зміни
@app.get("/finance/shifts/active")
def get_active_shift(db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    return shift

# 5. Відкриття касової зміни
@app.post("/finance/shifts/open")
def open_shift(payload: dict, db: Session = Depends(get_db)):
    active = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    if active:
        raise HTTPException(status_code=400, detail="Зміна вже відкрита")
    
    new_shift = models.Shift(
        user_id=1, # Поки немає системи логіну, ставимо ID касира за замовчуванням
        opening_balance=payload.get("opening_balance", 0)
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift

# 6. Закриття касової зміни
@app.post("/finance/shifts/{shift_id}/close")
def close_shift(shift_id: int, cash_account_id: int, safe_account_id: int, actual_balance: float, db: Session = Depends(get_db)):
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id, models.Shift.closed_at == None).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Активну зміну не знайдено")
    
    shift.closed_at = datetime.utcnow()
    shift.closing_balance_actual = actual_balance
    
    cash_acc = db.query(models.Account).filter(models.Account.id == cash_account_id).first()
    expected = float(cash_acc.balance) if cash_acc else 0.0
    
    shift.closing_balance_expected = expected
    shift.discrepancy = actual_balance - expected
    db.commit()
    return {"status": "success", "shift": shift}

# 7. Звіт PnL (Доходи та Витрати)
@app.get("/finance/report/pnl")
def get_pnl(db: Session = Depends(get_db)):
    # Базовий розрахунок загальних доходів та витрат
    income = db.query(func.sum(models.Transaction.amount)).join(models.TransactionCategory).filter(models.TransactionCategory.type == 'INCOME').scalar() or 0
    expense = db.query(func.sum(models.Transaction.amount)).join(models.TransactionCategory).filter(models.TransactionCategory.type == 'EXPENSE').scalar() or 0
    
    return {
        "income": float(income),
        "expense": abs(float(expense)),
        "profit": float(income) - abs(float(expense)),
        "categories": [] 
    }

# 8. Сівба (Генерація базових рахунків)
@app.post("/finance/seed")
def seed_database(db: Session = Depends(get_db)):
    if not db.query(models.Account).first():
        db.add_all([
            models.Account(name="Каса (Готівка)", type="cash"),
            models.Account(name="Банк (Еквайринг)", type="bank"),
            models.Account(name="Головний Сейф", type="safe")
        ])
        db.add_all([
            models.TransactionCategory(name="Продаж товарів", type="INCOME"),
            models.TransactionCategory(name="Закупівля товару", type="EXPENSE"),
            models.TransactionCategory(name="Інкасація", type="SERVICE")
        ])
        db.commit()
        return {"status": "Базу успішно наповнено базовими даними!"}
    return {"status": "Дані вже існують."}

# Оновлений роут
@app.post("/finance/accounts/", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # Створюємо модель бази даних на основі отриманих даних
    new_account = models.Account(
        name=account.name,
        type=account.type
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account