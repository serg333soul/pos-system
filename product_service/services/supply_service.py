# FILE: product_service/services/supply_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas

# 🔥 Єдиний місток до складу:
from services.inventory_client import InventoryClient

class SupplyService:
    @staticmethod
    def create_supply(db: Session, data: schemas.SupplyCreate):
        # 1. Знаходимо ім'я постачальника
        name_to_save = data.supplier_name
        if data.supplier_id and not name_to_save:
            supplier = db.query(models.Supplier).filter(models.Supplier.id == data.supplier_id).first()
            if supplier:
                name_to_save = supplier.name

        # 2. Створюємо шапку накладної
        supply = models.Supply(
            supplier_id=data.supplier_id,
            supplier_name=name_to_save,
            invoice_number=data.invoice_number,
            notes=data.notes,
            total_cost=0
        )
        db.add(supply)
        db.flush() # Отримуємо supply.id

        total_supply_cost = 0.0

        for item in data.items:
            line_total = item.quantity * item.cost_per_unit
            total_supply_cost += line_total
            
            # 🔥 3. ДЕЛЕГУЄМО ОПРИХОДУВАННЯ СКЛАДУ (Через Клієнт-Адаптер)
            display_name = InventoryClient.receive_stock(
                db=db,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                quantity=item.quantity,
                cost_per_unit=item.cost_per_unit,
                reason=f"Постачання #{supply.id}"
            )

            # 4. Створюємо запис партії у модулі Закупівель (SupplyItem)
            db_item = models.SupplyItem(
                supply_id=supply.id,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                entity_name=display_name, # Назва, яку нам повернув склад
                quantity=item.quantity,
                remaining_quantity=item.quantity, # Цю цифру склад потім списуватиме по FIFO
                cost_per_unit=item.cost_per_unit,
                total_cost=line_total
            )
            db.add(db_item)

        supply.total_cost = total_supply_cost
        db.commit()
        db.refresh(supply)
        return supply