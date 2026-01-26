from sqlalchemy.orm import Session
import models
from datetime import datetime

class InventoryLogger:
    @staticmethod
    def log(db: Session, entity_type: str, entity_id: int, entity_name: str, old_balance: float, new_balance: float, reason: str = "manual"):
        change = new_balance - old_balance
        if change == 0: return

        transaction = models.InventoryTransaction(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            change_amount=change,
            balance_after=new_balance,
            reason=reason,
            created_at=datetime.utcnow()
        )
        db.add(transaction)