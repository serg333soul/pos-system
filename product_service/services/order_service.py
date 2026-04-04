# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models
import schemas
import traceback

# Імпортуємо Клієнти-Адаптери
from services.inventory_client import InventoryClient 
from services.finance_client import FinanceClient # 🔥 ДОДАНО ІМПОРТ

class OrderService:

    @staticmethod
    def cancel_order(db: Session, order_id: int) -> bool:
        """
        Логіка скасування чека: повернення грошей та продуктів на склад.
        """
        try:
            # 1. Знаходимо замовлення з усіма позиціями
            order = db.query(models.Order).filter(models.Order.id == order_id).first()
            if not order:
                print(f"⚠️ [REFUND] Чек #{order_id} не знайдено в базі.")
                return False

            print(f"🔄 [REFUND] Початок скасування чека #{order_id}...")

            # 2. Відправляємо наказ ФІНАНСАМ повернути гроші
            FinanceClient.register_order_refund(
                order_id=order.id,
                amount=float(order.total_price),
                payment_method=order.payment_method
            )

            # 3. Відправляємо наказ СКЛАДУ повернути інгредієнти
            # 🔥 Передаємо об'єкти OrderItem напряму, щоб InventoryClient міг легко їх прочитати
            InventoryClient.refund_stock_async(order.id, order.items)

            # 4. Видаляємо замовлення (або можна змінити статус на 'cancelled', якщо є таке поле)
            db.delete(order)
            db.commit()
            
            print(f"✅ [REFUND] Чек #{order_id} скасовано. RabbitMQ відпрацює повернення на фоні.")
            return True

        except Exception as e:
            db.rollback()
            print(f"❌ [REFUND] КРИТИЧНА ПОМИЛКА при скасуванні чека #{order_id}: {e}")
            print(traceback.format_exc())
            return False

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
            processed_items, total_price = InventoryClient.process_order_items(
                db, order_data.items, transaction_reason
            )

            # 3. Записуємо "зліпок" (Snapshot) позицій в чек
            # 🔥 Використовуємо zip, щоб брати ID з оригінального запиту
            for p_item, orig_item in zip(processed_items, order_data.items):
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_id=orig_item.product_id, # Зберігаємо ID
                    variant_id=orig_item.variant_id, # Зберігаємо ID
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
            
            # 5. Відправляємо команду на списання складу в RabbitMQ
            InventoryClient.deduct_stock_async(new_order.id, transaction_reason, order_data.items)
            print(f"✅ [CHECKOUT] Замовлення #{new_order.id} успішно створено! Сума: {new_order.total_price}")
            
            return new_order

        except HTTPException as http_ex:
            db.rollback()
            print(f"⚠️ [CHECKOUT] HTTP помилка при оплаті: {http_ex.detail}")
            raise http_ex
        except Exception as e:
            db.rollback()
            print("❌ [CHECKOUT] КРИТИЧНА ПОМИЛКА ПРИ ОПЛАТІ:")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення. Деталі в логах сервера.")