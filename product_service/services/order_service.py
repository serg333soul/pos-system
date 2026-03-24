# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models
import schemas
import traceback

# 🔥 ВАЖЛИВО: Модуль Продажів тепер знає тільки про Клієнт-Адаптер
from services.inventory_client import InventoryClient 

class OrderService:
    @staticmethod
    def process_checkout(db: Session, order_data: schemas.OrderCreate):
        try:
            print(f"🛒 [CHECKOUT] Початок обробки замовлення. Позицій: {len(order_data.items)}")
            
            # 1. Створюємо замовлення у базі продажів (Orders)
            new_order = models.Order(
                created_at=datetime.utcnow(),
                payment_method=order_data.payment_method,
                total_price=0, 
                customer_id=order_data.customer_id
            )
            db.add(new_order)
            db.flush() # Отримуємо new_order.id
            
            transaction_reason = f"sale_order_{new_order.id}"

            # 2. ДЕЛЕГУЄМО ЛОГІКУ СКЛАДУ ЧЕРЕЗ КЛІЄНТ (АДАПТЕР)
            # У майбутньому цей рядок перетвориться на HTTP запит: requests.post(...)
            processed_items, total_price = InventoryClient.process_order_items(
                db, order_data.items, transaction_reason
            )

            # 3. Записуємо "зліпок" (Snapshot) позицій в чек
            for p_item in processed_items:
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_name=p_item["product_name"],
                    quantity=p_item["quantity"],
                    price_at_moment=p_item["price_at_moment"], 
                    details=p_item["details"],
                    consumable_overrides=p_item["consumable_overrides"]
                ))

            # 4. Фіксуємо підсумкову суму і зберігаємо чек
            new_order.total_price = round(total_price, 2)
            db.commit()
            db.refresh(new_order)
            print(f"✅ [CHECKOUT] Замовлення {new_order.id} успішно створено! Сума: {new_order.total_price}")
            return new_order

        except HTTPException as http_ex:
            db.rollback()
            print(f"⚠️ HTTP помилка при оплаті: {http_ex.detail}")
            raise http_ex
        except Exception as e:
            db.rollback()
            print("❌ КРИТИЧНА ПОМИЛКА ПРИ ОПЛАТІ:")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення. Деталі в логах сервера.")