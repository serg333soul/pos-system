# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import requests # 🔥 ДОДАНО ДЛЯ HTTP-ЗАПИТІВ ДО ІНШИХ МІКРОСЕРВІСІВ
import models
import schemas
import traceback

# Імпортуємо Клієнти-Адаптери
from services.inventory_client import InventoryClient 
from services.finance_client import FinanceClient

class OrderService:

    @staticmethod
    def cancel_order(db: Session, order_id: int) -> bool:
        """
        Логіка скасування чека: повернення грошей та продуктів на склад.
        """
        try:
            order = db.query(models.Order).filter(models.Order.id == order_id).first()
            if not order:
                print(f"⚠️ [REFUND] Чек #{order_id} не знайдено в базі.")
                return False

            print(f"🔄 [REFUND] Початок скасування чека #{order_id}...")

            FinanceClient.register_order_refund(
                order_id=order.id,
                amount=float(order.total_price),
                payment_method=order.payment_method
            )

            InventoryClient.refund_stock_async(order.id, order.items)

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
            bonuses_to_spend = 0.0
            new_order = models.Order(
                created_at=datetime.utcnow(),
                payment_method=order_data.payment_method,
                total_price=0, 
                customer_id=order_data.customer_id,
                bonuses_spent=bonuses_to_spend
            )
            db.add(new_order)
            db.flush()
            
            transaction_reason = f"sale_order_{new_order.id}"

            processed_items, total_price = InventoryClient.process_order_items(
                db, order_data.items, transaction_reason
            )

            # --- 🔥 ПРАВИЛЬНИЙ МІКРОСЕРВІСНИЙ ПІДХІД ДО БОНУСІВ ---
            
            if getattr(order_data, 'use_bonuses', False) and order_data.customer_id:
                try:
                    # 1. Робимо синхронний HTTP-запит до мікросервісу CRM
                    # Звертаємось по внутрішній Docker-мережі до контейнера pos_customer_api
                    crm_url = f"http://customer_api:8003/customers/{order_data.customer_id}"
                    response = requests.get(crm_url, timeout=3.0)
                    
                    if response.status_code == 200:
                        customer_data = response.json()
                        available_bonuses = float(customer_data.get("bonus_balance", 0))
                        
                        # 2. Розраховуємо скільки РЕАЛЬНО можна списати 
                        # (не більше ніж баланс і не більше ніж сума чека)
                        bonuses_to_spend = min(available_bonuses, total_price)
                        print(f"💎 [LOYALTY] Баланс підтверджено сервісом CRM: {available_bonuses} ₴. Буде списано: {bonuses_to_spend} ₴")
                        
                        # 3. Віднімаємо бонуси від підсумкової ціни
                        total_price -= bonuses_to_spend
                    else:
                        print(f"⚠️ [LOYALTY] Відмова CRM! Статус {response.status_code}. Чек пробивається без знижки.")
                        order_data.use_bonuses = False # Скасовуємо списання
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ [LOYALTY] Сервіс CRM недоступний ({e}). Пробиваємо чек без знижки.")
                    order_data.use_bonuses = False # Скасовуємо списання

            # Зберігаємо позиції
            for p_item, orig_item in zip(processed_items, order_data.items):
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_id=orig_item.product_id,
                    variant_id=orig_item.variant_id,
                    product_name=p_item["product_name"],
                    quantity=p_item["quantity"],
                    price_at_moment=p_item["price_at_moment"], 
                    details=p_item["details"],
                    consumable_overrides=p_item["consumable_overrides"]
                ))

            # Фіксуємо підсумкову суму з урахуванням знижки
            new_order.total_price = round(total_price, 2)
            # Перезаписуємо 0 на реальну суму знижки!
            new_order.bonuses_spent = bonuses_to_spend
            
            db.commit()
            db.refresh(new_order)
            
            InventoryClient.deduct_stock_async(new_order.id, transaction_reason, order_data.items)
            
            # 🔥 Передаємо use_bonuses (справжнє значення, яке ми перевірили)
            FinanceClient.register_order_income(
                db=db,
                order_id=new_order.id,
                total_price=new_order.total_price,
                payment_method=order_data.payment_method,
                user_id=1, 
                customer_id=order_data.customer_id,
                bonuses_spent=bonuses_to_spend,
                use_bonuses=getattr(order_data, 'use_bonuses', False)
                
            )
            
            print(f"✅ [CHECKOUT] Замовлення #{new_order.id} успішно створено! До сплати: {new_order.total_price}")
            return new_order

        except HTTPException as http_ex:
            db.rollback()
            raise http_ex
        except Exception as e:
            db.rollback()
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Помилка обробки замовлення.")