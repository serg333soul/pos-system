# FILE: product_service/services/product_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas

class ProductService:
    """
    Клас для управління товарами.
    Допомагає розвантажити роутер від складних вкладених циклів.
    """

    @staticmethod
    def create_product(db: Session, product: schemas.ProductCreate):
        # 1. Створюємо базовий запис товару
        db_product = models.Product(
            name=product.name, 
            price=product.price, 
            description=product.description,
            category_id=product.category_id, 
            has_variants=product.has_variants,
            master_recipe_id=product.master_recipe_id, 
            output_weight=product.output_weight
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product) # Щоб отримати ID нового товару

        # 2. Прив'язуємо витратні матеріали (рівень товару)
        for cons in product.consumables:
            db.add(models.ProductConsumable(
                product_id=db_product.id, 
                consumable_id=cons.consumable_id, 
                quantity=cons.quantity
            ))

        # 3. Якщо є варіанти, створюємо їх і їхні матеріали
        if product.has_variants and product.variants:
            for v in product.variants:
                db_variant = models.ProductVariant(
                    product_id=db_product.id, 
                    name=v.name, 
                    price=v.price, 
                    sku=v.sku,
                    master_recipe_id=v.master_recipe_id, 
                    output_weight=v.output_weight
                )
                db.add(db_variant)
                db.flush() # flush потрібен, щоб отримати ID варіанту до commit
                
                # Матеріали варіанту
                for vc in v.consumables:
                    db.add(models.ProductVariantConsumable(
                        variant_id=db_variant.id, 
                        consumable_id=vc.consumable_id, 
                        quantity=vc.quantity
                    ))

        # 4. Модифікатори (групи та самі модифікатори)
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

        # 5. Прив'язка процесів (Many-to-Many)
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
        # Отримуємо існуючий товар
        db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not db_product:
            return None # Або можна кидати помилку тут

        # Оновлюємо прості поля
        db_product.name = product_data.name
        db_product.description = product_data.description
        db_product.price = product_data.price
        db_product.category_id = product_data.category_id
        db_product.has_variants = product_data.has_variants
        db_product.master_recipe_id = product_data.master_recipe_id
        db_product.output_weight = product_data.output_weight

        # ОЧИЩЕННЯ старих зв'язків (найпростіший спосіб оновлення - видалити старе і створити нове)
        # SQLAlchemy автоматично видалить дочірні записи завдяки cascade="all, delete-orphan" в моделях
        db_product.variants = []
        db_product.modifier_groups = []
        db_product.consumables = []
        
        # Оновлення процесів
        db_product.process_groups = [] 
        if product_data.process_group_ids:
            for pg_id in product_data.process_group_ids:
                pg = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == pg_id).first()
                if pg:
                    db_product.process_groups.append(pg)

        db.flush() # Застосувати видалення

        # ДАЛІ КОД ІДЕНТИЧНИЙ СТВОРЕННЮ (пункти 2, 3, 4 зверху)
        # 2. Consumables
        for cons in product_data.consumables:
            db.add(models.ProductConsumable(product_id=db_product.id, consumable_id=cons.consumable_id, quantity=cons.quantity))

        # 3. Variants
        if product_data.has_variants and product_data.variants:
            for v in product_data.variants:
                db_variant = models.ProductVariant(
                    product_id=db_product.id, name=v.name, price=v.price, sku=v.sku,
                    master_recipe_id=v.master_recipe_id, output_weight=v.output_weight
                )
                db.add(db_variant); db.flush()
                for vc in v.consumables:
                    db.add(models.ProductVariantConsumable(variant_id=db_variant.id, consumable_id=vc.consumable_id, quantity=vc.quantity))
                    
        # 4. Modifiers
        for group in product_data.modifier_groups:
            db_group = models.ProductModifierGroup(product_id=db_product.id, name=group.name, is_required=group.is_required)
            db.add(db_group); db.flush()
            for mod in group.modifiers:
                db.add(models.Modifier(group_id=db_group.id, name=mod.name, price_change=mod.price_change, ingredient_id=mod.ingredient_id, quantity=mod.quantity))

        db.commit()
        db.refresh(db_product)
        return db_product