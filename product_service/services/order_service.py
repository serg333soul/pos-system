# FILE: product_service/services/order_service.py

from sqlalchemy.orm import Session
import models, schemas

class OrderService:
    """
    Цей клас відповідає виключно за обробку замовлень.
    Він не знає про HTTP-запити, він працює тільки з базою даних.
    """

    @staticmethod
    def process_checkout(db: Session, order_data: schemas.OrderCreate):
        # 1. Спочатку створюємо запис про саме замовлення в таблиці orders
        new_order = models.Order(
            total_price=order_data.total_price,
            payment_method=order_data.payment_method,
            customer_id=order_data.customer_id
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order) # Отримуємо ID новоствореного замовлення

        # 2. Тепер проходимось по кожному товару в кошику
        for item in order_data.items:
            # Знаходимо товар в базі
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not product:
                continue # Якщо товар видалено, пропускаємо (але в ідеалі треба кидати помилку)

            # Базові дані для чеку
            item_name = product.name
            price = product.price
            details_list = [] # Сюди будемо писати: "Варіант L", "Сироп", "Без цукру"
            
            target_recipe_id = None # Який рецепт списувати?
            base_weight = 0.0       # Яка вага для розрахунку відсотків?

            # --- А. СПИСАННЯ ВИТРАТНИХ МАТЕРІАЛІВ ТОВАРУ ---
            # Наприклад: серветка, яка йде до будь-якого бургера
            for pc in product.consumables:
                if pc.consumable:
                    # Віднімаємо зі складу: (к-сть на 1 шт) * (к-сть замовлених шт)
                    pc.consumable.stock_quantity -= pc.quantity * item.quantity
                    db.add(pc.consumable) # Позначаємо, що об'єкт змінився

            # --- Б. ЛОГІКА ВАРІАНТІВ (L, M, S) ---
            if item.variant_id:
                # Якщо це варіативний товар, шукаємо конкретний варіант
                variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
                if variant:
                    item_name = f"{product.name} ({variant.name})"
                    price = variant.price
                    details_list.append(f"Варіант: {variant.name}")
                    
                    # Визначаємо рецепт саме цього варіанту
                    target_recipe_id = variant.master_recipe_id or product.master_recipe_id
                    base_weight = variant.output_weight

                    # Списання матеріалів варіанту (наприклад, стакан 300мл)
                    for vc in variant.consumables:
                        if vc.consumable:
                            vc.consumable.stock_quantity -= vc.quantity * item.quantity
                            db.add(vc.consumable)
            else:
                # Якщо товар простий (без варіантів)
                target_recipe_id = product.master_recipe_id
                base_weight = product.output_weight

            # --- В. СПИСАННЯ ІНГРЕДІЄНТІВ (ТЕХ. КАРТА) ---
            if target_recipe_id:
                recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == target_recipe_id).first()
                if recipe:
                    for r_item in recipe.items:
                        if r_item.ingredient:
                            # Якщо вказано у %, рахуємо від base_weight. Якщо ні - беремо фіксовану вагу.
                            deduction = (r_item.quantity / 100.0 * base_weight) if r_item.is_percentage else r_item.quantity
                            r_item.ingredient.stock_quantity -= deduction * item.quantity
                            db.add(r_item.ingredient)

            # --- Г. СПИСАННЯ МОДИФІКАТОРІВ (Добавки) ---
            for mod_item in item.modifiers:
                mod = db.query(models.Modifier).filter(models.Modifier.id == mod_item.modifier_id).first()
                if mod:
                    details_list.append(mod.name)
                    # Якщо модифікатор прив'язаний до інгредієнта (напр. молоко), списуємо
                    if mod.ingredient:
                        mod.ingredient.stock_quantity -= mod.quantity * item.quantity
                        db.add(mod.ingredient)

            # 3. Фіксуємо рядок в історії замовлень (таблиця order_items)
            db.add(models.OrderItem(
                order_id=new_order.id,
                product_name=item_name,
                quantity=item.quantity,
                price_at_moment=price,
                details=", ".join(details_list) # Перетворюємо список деталей в рядок
            ))

        # Зберігаємо всі зміни в БД одним махом (транзакція)
        db.commit()
        return new_order