from sqlalchemy.orm import Session
from datetime import datetime
import models

class InventoryLogger:
    @staticmethod
    def log(db: Session, entity_type: str, entity_id: int, entity_name: str, 
            balance_before: float, balance_after: float, reason: str):
        """
        entity_type: 'product', 'variant', 'ingredient', 'consumable'
        """
        try:
            change_amount = balance_after - balance_before
            
            # Якщо змін немає, нічого не пишемо
            if change_amount == 0:
                return

            transaction = models.InventoryTransaction(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                change_amount=change_amount,
                balance_after=balance_after,
                reason=reason,
                created_at=datetime.utcnow()
            )
            db.add(transaction)
            # Commit не робимо, бо це частина великої транзакції в OrderService
        except Exception as e:
            print(f"⚠️ Помилка логування складу: {e}")