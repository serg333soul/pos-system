from sqlalchemy.orm import Session
from datetime import datetime
import models

class InventoryLogger:
    @staticmethod
    def log(db: Session, entity_type: str, entity_id: int, entity_name: str,
            balance_before: float, balance_after: float, reason: str, 
            force_change: float = None): # 🔥 Додаємо опціональний параметр
        try:
            # Якщо передано явну зміну (наприклад, продаж), використовуємо її
            # Якщо ні - вираховуємо автоматично
            change_amount = force_change if force_change is not None else (balance_after - balance_before)

            # Тепер ми ігноруємо запис ТІЛЬКИ якщо зміна дійсно нульова 
            # і ми не намагаємось зафіксувати продаж
            if change_amount == 0 and force_change is None:
                return

            transaction = models.InventoryTransaction(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                change_amount=change_amount, # Запишеться напр. -2
                balance_after=balance_after,
                reason=reason,
                created_at=datetime.utcnow(),
            )
            db.add(transaction)
        except Exception as e:
            print(f"⚠️ Помилка логування складу: {e}")