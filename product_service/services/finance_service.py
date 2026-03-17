# FILE: product_service/services/finance_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from decimal import Decimal
import models, schemas
from datetime import datetime

def create_transaction(db: Session, trans_data: schemas.TransactionCreate) -> models.Transaction:
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
    
    # 3. Оновлюємо кешований баланс рахунку (+= працює і для мінусових сум)
    # Наприклад, якщо amount = -50, то balance += -50 зменшить його.
    account.balance += trans_data.amount
    
    db.commit()
    db.refresh(new_transaction)
    
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

    # 1. Знаходимо категорію "Службове переміщення" (або створюємо її, якщо немає)
    transfer_category = db.query(models.TransactionCategory).filter(
        models.TransactionCategory.name == "Переміщення коштів",
        models.TransactionCategory.type == "SERVICE"
    ).first()
    
    if not transfer_category:
        transfer_category = models.TransactionCategory(name="Переміщення коштів", type="SERVICE")
        db.add(transfer_category)
        db.commit()
        db.refresh(transfer_category)

    # 2. Створюємо транзакцію СПИСАННЯ (Мінус)
    expense_data = schemas.TransactionCreate(
        amount=-transfer_data.amount, # Від'ємна сума
        account_id=transfer_data.from_account_id,
        category_id=transfer_category.id,
        user_id=transfer_data.user_id,
        shift_id=transfer_data.shift_id,
        description=f"Переказ на рахунок #{transfer_data.to_account_id}: {transfer_data.description}"
    )
    out_tx = create_transaction(db, expense_data)

    # 3. Створюємо транзакцію ЗАРАХУВАННЯ (Плюс)
    income_data = schemas.TransactionCreate(
        amount=transfer_data.amount, # Позитивна сума
        account_id=transfer_data.to_account_id,
        category_id=transfer_category.id,
        user_id=transfer_data.user_id,
        shift_id=transfer_data.shift_id,
        description=f"Переказ з рахунку #{transfer_data.from_account_id}: {transfer_data.description}"
    )
    in_tx = create_transaction(db, income_data)

    # 4. Пов'язуємо їх між собою (щоб знати, що це одна операція)
    out_tx.linked_transaction_id = in_tx.id
    in_tx.linked_transaction_id = out_tx.id
    db.commit()

    return {
        "status": "success",
        "transferred_amount": transfer_data.amount,
        "from_transaction_id": out_tx.id,
        "to_transaction_id": in_tx.id
    }

def open_shift(db: Session, shift_data: schemas.ShiftCreate) -> models.Shift:
    """
    Відкриття касової зміни (X-Звіт на початок дня).
    """
    # 1. Перевірка: чи немає вже відкритої зміни? (Захист від дублів)
    active_shift = db.query(models.Shift).filter(models.Shift.closed_at == None).first()
    if active_shift:
        raise HTTPException(status_code=400, detail="Вже є відкрита зміна. Спочатку закрийте її (зробіть Z-звіт).")

    # 2. Створюємо зміну з початковим залишком (розмінка в шухляді)
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
    """
    Закриття касової зміни (Z-Звіт).
    Рахує очікувані гроші, фіксує різницю та робить інкасацію в сейф.
    """
    # 1. Знаходимо зміну і перевіряємо її статус
    shift = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Зміну не знайдено")
    if shift.closed_at:
        raise HTTPException(status_code=400, detail="Ця зміна вже була закрита раніше")

    # 2. РАХУЄМО ОЧІКУВАНИЙ ЗАЛИШОК КАСТИ
    # Беремо суму всіх транзакцій за цю зміну для конкретного рахунку (Готівка Каса)
    cash_flow = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.shift_id == shift.id,
        models.Transaction.account_id == cash_account_id
    ).scalar() or Decimal('0.00')

    # Очікувані гроші = Розмінка на ранок + (Доходи - Витрати за день)
    expected_balance = shift.opening_balance + cash_flow

    # 3. ФІКСУЄМО ПОКАЗНИКИ
    shift.closing_balance_expected = expected_balance
    shift.closing_balance_actual = close_data.closing_balance_actual
    # Різниця: Від'ємна = Нестача, Позитивна = Лишок
    shift.discrepancy = close_data.closing_balance_actual - expected_balance 
    shift.closed_at = datetime.utcnow()

    db.commit()

    # 4. АВТОМАТИЧНА ІНКАСАЦІЯ (Передача в сейф)
    if close_data.transfer_to_safe_amount > 0:
        # Захист: не можна здати в сейф більше грошей, ніж реально нарахував касир
        if close_data.transfer_to_safe_amount > close_data.closing_balance_actual:
            raise HTTPException(
                status_code=400, 
                detail="Сума інкасації не може перевищувати фактичний наявний залишок в касі"
            )

        # Використовуємо нашу функцію переміщення з Етапу 2.1
        transfer_data = schemas.TransferCreate(
            from_account_id=cash_account_id,
            to_account_id=safe_account_id,
            amount=close_data.transfer_to_safe_amount,
            user_id=user_id,
            shift_id=shift.id,
            description="Інкасація при закритті зміни (Z-звіт)"
        )
        transfer_funds(db, transfer_data)

    db.refresh(shift)
    return shift