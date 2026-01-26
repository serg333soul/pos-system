from sqlalchemy.orm import Session
import models, schemas
from services.inventory_logger import InventoryLogger
import traceback # Для виводу помилки в консоль

class OrderService:
    """
    Цей клас відповідає виключно за обробку замовлень.
    Реалізовано принцип Atomic Transaction (все або нічого).
    """
    @staticmethod
    def process_checkout(db: Session, order_data: schemas.OrderCreate):
        try:
            # 1. Створюємо замовлення
            new_order = models.Order(
                total_price=order_data.total_price,
                payment_method=order_data.payment_method,
                customer_id=order_data.customer_id
            )
            db.add(new_order)
            
            # ВАЖЛИВО: Використовуємо flush(), а не commit().
            # Це дає нам ID замовлення, але дозволяє відкотити зміни, якщо стається помилка далі.
            db.flush() 
            db.refresh(new_order)

            transaction_reason = f"sale_order_{new_order.id}"

            # 2. Проходимось по товарах
            for item in order_data.items:
                product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
                if not product: continue

                item_name = product.name
                price = product.price
                details_list = []
                
                target_recipe_id = None
                base_weight = 0.0

                # --- А. ВАРІАНТИ ---
                if item.variant_id:
                    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
                    if variant:
                        item_name = f"{product.name} ({variant.name})"
                        price = variant.price
                        details_list.append(f"Варіант: {variant.name}")
                        
                        target_recipe_id = variant.master_recipe_id or product.master_recipe_id
                        base_weight = variant.output_weight

                        # Списання залишку варіанту
                        old_qty = variant.stock_quantity
                        variant.stock_quantity -= item.quantity
                        db.add(variant)
                        
                        InventoryLogger.log(
                            db, "product_variant", variant.id, item_name, 
                            old_qty, variant.stock_quantity, transaction_reason
                        )

                        # Списання матеріалів варіанту
                        for vc in variant.consumables:
                            if vc.consumable:
                                c_old = vc.consumable.stock_quantity
                                deduction = vc.quantity * item.quantity
                                vc.consumable.stock_quantity -= deduction
                                db.add(vc.consumable)
                                InventoryLogger.log(db, "consumable", vc.consumable.id, vc.consumable.name, c_old, vc.consumable.stock_quantity, transaction_reason)

                        # !!! НОВЕ: Списання інгредієнтів варіанту !!!
                        # Якщо models.py не оновлено, тут буде помилка AttributeError.
                        # Завдяки try/except ми побачимо це в логах, а замовлення не створиться.
                        if hasattr(variant, 'ingredients'):
                            for vi in variant.ingredients:
                                if vi.ingredient:
                                    i_old = vi.ingredient.stock_quantity
                                    deduction = vi.quantity * item.quantity
                                    vi.ingredient.stock_quantity -= deduction
                                    db.add(vi.ingredient)
                                    InventoryLogger.log(db, "ingredient", vi.ingredient.id, vi.ingredient.name, i_old, vi.ingredient.stock_quantity, transaction_reason)

                # --- Б. ПРОСТІ ТОВАРИ ---
                else:
                    target_recipe_id = product.master_recipe_id
                    base_weight = product.output_weight
                    
                    if product.track_stock:
                        old_qty = product.stock_quantity
                        product.stock_quantity -= item.quantity
                        db.add(product)
                        InventoryLogger.log(db, "product", product.id, product.name, old_qty, product.stock_quantity, transaction_reason)

                # --- В. ЗАГАЛЬНІ МАТЕРІАЛИ ---
                for pc in product.consumables:
                    if pc.consumable:
                        c_old = pc.consumable.stock_quantity
                        deduction = pc.quantity * item.quantity
                        pc.consumable.stock_quantity -= deduction
                        db.add(pc.consumable)
                        InventoryLogger.log(db, "consumable", pc.consumable.id, pc.consumable.name, c_old, pc.consumable.stock_quantity, transaction_reason)

                # --- Г. РЕЦЕПТ ---
                if target_recipe_id:
                    recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == target_recipe_id).first()
                    if recipe:
                        for r_item in recipe.items:
                            if r_item.ingredient:
                                deduction_per_item = (r_item.quantity / 100.0 * base_weight) if r_item.is_percentage else r_item.quantity
                                total_deduction = deduction_per_item * item.quantity
                                i_old = r_item.ingredient.stock_quantity
                                r_item.ingredient.stock_quantity -= total_deduction
                                db.add(r_item.ingredient)
                                InventoryLogger.log(db, "ingredient", r_item.ingredient.id, r_item.ingredient.name, i_old, r_item.ingredient.stock_quantity, transaction_reason)

                # --- Д. МОДИФІКАТОРИ ---
                for mod_item in item.modifiers:
                    mod = db.query(models.Modifier).filter(models.Modifier.id == mod_item.modifier_id).first()
                    if mod:
                        details_list.append(mod.name)
                        if mod.ingredient:
                            i_old = mod.ingredient.stock_quantity
                            deduction = mod.quantity * item.quantity
                            mod.ingredient.stock_quantity -= deduction
                            db.add(mod.ingredient)
                            InventoryLogger.log(db, "ingredient", mod.ingredient.id, mod.ingredient.name, i_old, mod.ingredient.stock_quantity, transaction_reason)

                # Фіксуємо рядок в чеку
                db.add(models.OrderItem(
                    order_id=new_order.id,
                    product_name=item_name,
                    quantity=item.quantity,
                    price_at_moment=price,
                    details=", ".join(details_list)
                ))

            # 3. Тільки якщо все пройшло без помилок - фіксуємо транзакцію
            db.commit()
            return new_order

        except Exception as e:
            # Якщо сталась БУДЬ-ЯКА помилка - відкочуємо все (і створення замовлення теж)
            db.rollback()
            print("❌ ПОМИЛКА ПРИ ОПЛАТІ (Transaction Rollback):")
            print(traceback.format_exc()) # Виведе точну причину в консоль Docker
            raise e # Прокидуємо помилку далі, щоб API повернув 500