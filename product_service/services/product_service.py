from sqlalchemy.orm import Session
# 🔥 1. Додаємо імпорт для обробки помилок БД
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import models
import schemas

class ProductService:
    """
    Клас для управління товарами.
    Вся логіка створення, оновлення, видалення та розрахунку вартості.
    """

    @staticmethod
    def calculate_product_cost(db: Session, data: schemas.ProductCostCheck) -> float:
        total_cost = 0.0

        # 1. Прямі інгредієнти
        for link in data.ingredients:
            ing = db.query(models.Ingredient).filter(models.Ingredient.id == link.ingredient_id).first()
            if ing:
                total_cost += ing.cost_per_unit * link.quantity

        # 2. Витратні матеріали
        for link in data.consumables:
            cons = db.query(models.Consumable).filter(models.Consumable.id == link.consumable_id).first()
            if cons:
                total_cost += cons.cost_per_unit * link.quantity

        # 3. Рецепт (Техкарта)
        if data.master_recipe_id:
            recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == data.master_recipe_id).first()
            if recipe:
                for item in recipe.items:
                    if item.ingredient:
                        # Логіка: Якщо в рецепті %, беремо від ваги виходу. Якщо ні - пряма кількість.
                        qty = 0
                        if item.is_percentage:
                            qty = (item.quantity / 100) * (data.output_weight or 0)
                        else:
                            qty = item.quantity
                        
                        total_cost += item.ingredient.cost_per_unit * qty

        return round(total_cost, 2)

    @staticmethod
    def create_product(db: Session, product: schemas.ProductCreate):
        # 1. Створення самого продукту
        db_product = models.Product(
            name=product.name,
            description=product.description,
            price=product.price,
            category_id=product.category_id,
            # image_url видалено згідно з вашою БД
            has_variants=product.has_variants,
            track_stock=product.track_stock,
            stock_quantity=product.stock_quantity,
            master_recipe_id=product.master_recipe_id,
            output_weight=product.output_weight
        )
        db.add(db_product)
        db.flush() # Отримуємо ID

        # 2. Додавання інгредієнтів (Many-to-Many)
        if product.ingredients:
            for item in product.ingredients:
                db.add(models.ProductIngredient(
                    product_id=db_product.id,
                    ingredient_id=item.ingredient_id,
                    quantity=item.quantity
                ))
        
        # 2.1 Додавання витратних матеріалів
        if product.consumables:
            for item in product.consumables:
                db.add(models.ProductConsumable(
                    product_id=db_product.id,
                    consumable_id=item.consumable_id,
                    quantity=item.quantity
                ))

        # 3. Варіанти
        if product.variants:
            for v in product.variants:
                db_variant = models.ProductVariant(
                    product_id=db_product.id,
                    name=v.name,
                    price=v.price,
                    sku=v.sku,
                    master_recipe_id=v.master_recipe_id,
                    output_weight=v.output_weight,
                    stock_quantity=v.stock_quantity
                )
                db.add(db_variant)
                db.flush()
                
                # Інгредієнти варіанту
                if v.ingredients:
                    for vi in v.ingredients:
                        db.add(models.ProductVariantIngredient(
                            variant_id=db_variant.id,
                            ingredient_id=vi.ingredient_id,
                            quantity=vi.quantity
                        ))
                
                # Матеріали варіанту
                if v.consumables:
                    for vc in v.consumables:
                        db.add(models.ProductVariantConsumable(
                            variant_id=db_variant.id,
                            consumable_id=vc.consumable_id,
                            quantity=vc.quantity
                        ))

        # 4. Модифікатори
        if product.modifier_groups:
            for group in product.modifier_groups:
                db_group = models.ProductModifierGroup(
                    product_id=db_product.id,
                    name=group.name,
                    is_required=group.is_required
                )
                db.add(db_group)
                db.flush()
                for mod in group.modifiers:
                    db.add(models.Modifier(
                        group_id=db_group.id,
                        name=mod.name,
                        price_change=mod.price_change,
                        ingredient_id=mod.ingredient_id,
                        quantity=mod.quantity
                    ))
        
        # 5. Групи процесів
        if product.process_group_ids:
            for pg_id in product.process_group_ids:
                pg = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == pg_id).first()
                if pg:
                    db_product.process_groups.append(pg)

        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def update_product(db: Session, product_id: int, product_data: schemas.ProductCreate):
        db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not db_product:
            return None

        # 1. Оновлення основних полів
        db_product.name = product_data.name
        db_product.description = product_data.description
        db_product.price = product_data.price
        db_product.category_id = product_data.category_id
        # db_product.image_url = product_data.image_url # Видалено
        db_product.has_variants = product_data.has_variants
        db_product.track_stock = product_data.track_stock
        db_product.stock_quantity = product_data.stock_quantity
        db_product.master_recipe_id = product_data.master_recipe_id
        db_product.output_weight = product_data.output_weight

        # 2. Оновлення зв'язків (Інгредієнти, Матеріали)
        # Видаляємо старі, додаємо нові (простий і надійний спосіб)
        db.query(models.ProductIngredient).filter(models.ProductIngredient.product_id == product_id).delete()
        if product_data.ingredients:
            for item in product_data.ingredients:
                db.add(models.ProductIngredient(
                    product_id=product_id, ingredient_id=item.ingredient_id, quantity=item.quantity
                ))
        
        db.query(models.ProductConsumable).filter(models.ProductConsumable.product_id == product_id).delete()
        if product_data.consumables:
            for item in product_data.consumables:
                db.add(models.ProductConsumable(
                    product_id=product_id, consumable_id=item.consumable_id, quantity=item.quantity
                ))

        # 3. ВАРІАНТИ (Розумне оновлення)
        current_variants_map = {v.name: v for v in db_product.variants}
        incoming_variants_names = set()

        if product_data.variants:
            for v_data in product_data.variants:
                incoming_variants_names.add(v_data.name)
                
                if v_data.name in current_variants_map:
                    # Оновлюємо існуючий
                    existing_variant = current_variants_map[v_data.name]
                    existing_variant.price = v_data.price
                    existing_variant.sku = v_data.sku
                    existing_variant.master_recipe_id = v_data.master_recipe_id
                    existing_variant.output_weight = v_data.output_weight
                    existing_variant.stock_quantity = v_data.stock_quantity
                    
                    # Оновлюємо вкладені списки варіанту
                    db.query(models.ProductVariantIngredient).filter(models.ProductVariantIngredient.variant_id == existing_variant.id).delete()
                    if v_data.ingredients:
                        for vi in v_data.ingredients:
                            db.add(models.ProductVariantIngredient(
                                variant_id=existing_variant.id, ingredient_id=vi.ingredient_id, quantity=vi.quantity
                            ))

                    db.query(models.ProductVariantConsumable).filter(models.ProductVariantConsumable.variant_id == existing_variant.id).delete()
                    if v_data.consumables:
                        for vc in v_data.consumables:
                            db.add(models.ProductVariantConsumable(
                                variant_id=existing_variant.id, consumable_id=vc.consumable_id, quantity=vc.quantity
                            ))
                else:
                    # Створюємо новий
                    new_variant = models.ProductVariant(
                        product_id=product_id,
                        name=v_data.name,
                        price=v_data.price,
                        sku=v_data.sku,
                        master_recipe_id=v_data.master_recipe_id,
                        output_weight=v_data.output_weight,
                        stock_quantity=v_data.stock_quantity
                    )
                    db.add(new_variant)
                    db.flush()

                    if v_data.ingredients:
                        for vi in v_data.ingredients:
                            db.add(models.ProductVariantIngredient(
                                variant_id=new_variant.id, ingredient_id=vi.ingredient_id, quantity=vi.quantity
                            ))
                    if v_data.consumables:
                        for vc in v_data.consumables:
                            db.add(models.ProductVariantConsumable(
                                variant_id=new_variant.id, consumable_id=vc.consumable_id, quantity=vc.quantity
                            ))

        # Видаляємо старі варіанти (тут спрацює ORM cascade, бо ми видаляємо об'єкти з сесії)
        for name, variant in current_variants_map.items():
            if name not in incoming_variants_names:
                db.delete(variant)

        # 4. МОДИФІКАТОРИ
        db.query(models.ProductModifierGroup).filter(
            models.ProductModifierGroup.product_id == product_id
        ).delete()
        
        if product_data.modifier_groups:
            for group in product_data.modifier_groups:
                db_group = models.ProductModifierGroup(
                    product_id=product_id, 
                    name=group.name, 
                    is_required=group.is_required
                )
                db.add(db_group)
                db.flush()
                for mod in group.modifiers:
                    db.add(models.Modifier(
                        group_id=db_group.id, 
                        name=mod.name, 
                        price_change=mod.price_change, 
                        ingredient_id=mod.ingredient_id, 
                        quantity=mod.quantity
                    ))

        # 5. ПРОЦЕСИ
        db_product.process_groups = [] 
        if product_data.process_group_ids:
            for pg_id in product_data.process_group_ids:
                pg = db.query(models.ProcessGroup).filter(
                    models.ProcessGroup.id == pg_id
                ).first()
                if pg:
                    db_product.process_groups.append(pg)

        db.commit()
        db.refresh(db_product)
        return db_product

    # 🔥 2. ДОДАЄМО МЕТОД ВИДАЛЕННЯ
    @staticmethod
    def delete_product(db: Session, product_id: int):
        try:
            # Завантажуємо товар (це активує cascade в models.py)
            product = db.query(models.Product).filter(models.Product.id == product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Видаляємо
            db.delete(product)
            db.commit()
            return True
            
        except IntegrityError as e:
            db.rollback()
            # Це перехопить помилку foreign key, якщо вона все ж таки виникне
            print(f"❌ DB Integrity Error: {e}")
            raise HTTPException(
                status_code=400, 
                detail="Неможливо видалити товар. Перевірте, чи не використовується він у замовленнях."
            )
        except Exception as e:
            db.rollback()
            print(f"❌ General Error: {e}")
            raise HTTPException(status_code=500, detail="Помилка сервера при видаленні")