# FILE: product_service/services/finance_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from decimal import Decimal
import models, schemas
from datetime import datetime

# 🔥 ДОДАНО: параметр auto_commit
def create_transaction(db: Session, trans_data: schemas.TransactionCreate, auto_commit: bool = True) -> models.Transaction:
    """
    Створення базової транзакції у Ledger.
    Це єдиний правильний спосіб змінити баланс рахунку.
    """
    # 1. Знаходимо рахунок
    account = db.query(models.Account).filter(models.Account.id == trans_data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Рахунок не знайдено")
    
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Цей рахунок деактивовано")

    # 2. Створюємо запис транзакції
    new_transaction = models.Transaction(
        amount=trans_data.amount,
        account_id=account.id,
        category_id=trans_data.category_id,
        shift_id=trans_data.shift_id,
        user_id=trans_data.user_id,
        reference_type=trans_data.reference_type,
        reference_id=trans_data.reference_id,
        description=trans_data.description
    )
    
    db.add(new_transaction)
    
    # 3. Оновлюємо кешований баланс рахунку
    account.balance += trans_data.amount
    
    # 🔥 ВИПРАВЛЕНО: Керуємо комітом для підтримки атомарності
    if auto_commit:
        db.commit()
        db.refresh(new_transaction)
    else:
        db.flush() # Тільки фіксуємо ID (для зв'язків), але НЕ зберігаємо намертво
    
    return new_transaction


def transfer_funds(db: Session, transfer_data: schemas.TransferCreate) -> dict:
    """
    Переміщення коштів (Інкасація).
    Атомарно знімає гроші з одного рахунку і кладе на інший.
    """
    if transfer_data.from_account_id == transfer_data.to_account_id:
        raise HTTPException(status_code=400, detail="Не можна переказати гроші на той самий рахунок")

    if transfer_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Сума переказу має бути більшою за 0")

    transfer_category = db.query(models.TransactionCategory).filter(
        models.TransactionCategory.name == "Переміщення коштів",
        models.TransactionCategory.type == "SERVICE"
    ).first()
    
    if not transfer_category:
        transfer_category = models.TransactionCategory(name="Переміщення коштів", type="SERVICE")
        db.add(transfer_category)
        db.flush() # Використовуємо flush замість commit

    # 🔥 ВИПРАВЛЕНО: Створюємо транзакції БЕЗ КОМІТУ
    expense_data = schemas.TransactionCreate(
        amount=-transfer_data.amount,
        account_id=transfer_data.from_account_id,
        category_id=transfer_category.id,
        user_id=transfer_data.user_id,
        shift_id=transfer_data.shift_id,
        description=f"Переказ на рахунок #{transfer_data.to_account_id}: {transfer_data.description}"
    )
    out_tx = create_transaction(db, expense_data, auto_commit=False)

    income_data = schemas.TransactionCreate(
        amount=transfer_data.amount,
        account_id=transfer_data.to_account_id,
        category_id=transfer_category.id,
        user_id=transfer_data.user_id,
        shift_id=transfer_data.shift_id,
        description=f"Переказ з рахунку #{transfer_data.from_account_id}: {transfer_data.description}"
    )
    in_tx = create_transaction(db, income_data, auto_commit=False)

    # 4. Пов'язуємо їх між собою
    out_tx.linked_transaction_id = in_tx.id
    in_tx.linked_transaction_id = out_tx.id
    
    # 🔥 ВИПРАВЛЕНО: Єдиний коміт для всієї операції! 
    # Тепер, якщо станеться помилка, гроші нікуди не зникнуть.
    db.commit()

    return {
        "status": "success",
        "transferred_amount": transfer_data.amount,
        "from_transaction_id": out_tx.id,
        "to_transaction_id": in_tx.id
    }

def open_shift(db: Session, shift_data: schemas.ShiftCreate) -> models.Shift:
    active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    if active_shift:
        raise HTTPException(status_code=400, detail="Вже є відкрита зміна. Спочатку закрийте її (зробіть Z-звіт).")

    new_shift = models.Shift(
        user_id=shift_data.user_id,
        opening_balance=shift_data.opening_balance,
        opened_at=datetime.utcnow()
    )
    
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    
    return new_shift


def close_shift(
    db: Session, 
    shift_id: int, 
    close_data: schemas.ShiftClose, 
    cash_account_id: int, 
    safe_account_id: int, 
    user_id: int
) -> models.Shift:
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Зміну не знайдено")
    if shift.closed_at:
        raise HTTPException(status_code=400, detail="Ця зміна вже була закрита раніше")

    cash_flow = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.shift_id == shift.id,
        models.Transaction.account_id == cash_account_id
    ).scalar() or Decimal('0.00')

    expected_balance = shift.opening_balance + cash_flow

    shift.closing_balance_expected = expected_balance
    shift.closing_balance_actual = close_data.closing_balance_actual
    shift.discrepancy = close_data.closing_balance_actual - expected_balance 
    shift.closed_at = datetime.utcnow()

    # 🔥 ВИПРАВЛЕНО: Робимо flush замість commit перед інкасацією, 
    # щоб закриття зміни та передача в сейф збереглись як єдина транзакція
    db.flush()

    if close_data.transfer_to_safe_amount > 0:
        if close_data.transfer_to_safe_amount > close_data.closing_balance_actual:
            raise HTTPException(
                status_code=400, 
                detail="Сума інкасації не може перевищувати фактичний наявний залишок в касі"
            )

        transfer_data = schemas.TransferCreate(
            from_account_id=cash_account_id,
            to_account_id=safe_account_id,
            amount=close_data.transfer_to_safe_amount,
            user_id=user_id,
            shift_id=shift.id,
            description="Інкасація при закритті зміни (Z-звіт)"
        )
        # transfer_funds зробить фінальний db.commit() всередині
        transfer_funds(db, transfer_data)
    else:
        # Якщо інкасації немає, комітимо тут
        db.commit()

    db.refresh(shift)
    return shift

# ДОДАТИ В КІНЕЦЬ finance_service.py

def generate_pnl_report(db: Session, start_date=None, end_date=None) -> dict:
    """Генерація звіту Прибутки та Збитки (P&L)"""
    query = db.query(
        models.TransactionCategory.name,
        models.TransactionCategory.type,
        func.sum(models.Transaction.amount).label('total')
    ).join(
        models.Transaction, models.Transaction.category_id == models.TransactionCategory.id
    )

    if start_date:
        query = query.filter(models.Transaction.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Transaction.timestamp <= end_date)

    results = query.group_by(models.TransactionCategory.name, models.TransactionCategory.type).all()

    report = {
        "income": {},          
        "expense": {},         
        "total_income": 0.0,
        "total_expense": 0.0,
        "net_profit": 0.0      
    }

    for name, cat_type, total in results:
        amount = float(total)
        if cat_type == 'INCOME':
            report["income"][name] = amount
            report["total_income"] += amount
        elif cat_type == 'EXPENSE':
            report["expense"][name] = abs(amount)
            report["total_expense"] += abs(amount)

    report["net_profit"] = report["total_income"] - report["total_expense"]
    return report