from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas
import uuid

class ProductService:
    """
    Клас для управління товарами.
    Вся логіка створення (Create) та оновлення (Update).
    """

    @staticmethod
    def create_product(db: Session, product: schemas.ProductCreate):
        # 1. СТВОРЕННЯ БАЗОВОГО ТОВАРУ
        db_product = models.Product(
            name=product.name, 
            price=product.price, 
            description=product.description,
            category_id=product.category_id, 
            has_variants=product.has_variants,
            master_recipe_id=product.master_recipe_id, 
            output_weight=product.output_weight,
            track_stock=product.track_stock,
            stock_quantity=product.stock_quantity
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        # 2. ДОДАВАННЯ ВИТРАТНИХ МАТЕРІАЛІВ (ЗАГАЛЬНІ)
        for cons in product.consumables:
            db.add(models.ProductConsumable(
                product_id=db_product.id, 
                consumable_id=cons.consumable_id, 
                quantity=cons.quantity
            ))

        # 3. СТВОРЕННЯ ВАРІАНТІВ
        if product.has_variants and product.variants:
            for v in product.variants:
                sku = v.sku if v.sku else str(uuid.uuid4())
                
                db_variant = models.ProductVariant(
                    product_id=db_product.id, 
                    name=v.name, 
                    price=v.price, 
                    sku=sku,
                    master_recipe_id=v.master_recipe_id, 
                    output_weight=v.output_weight,
                    stock_quantity=v.stock_quantity 
                )
                db.add(db_variant)
                db.flush() 
                
                for vc in v.consumables:
                    db.add(models.ProductVariantConsumable(
                        variant_id=db_variant.id, 
                        consumable_id=vc.consumable_id, 
                        quantity=vc.quantity
                    ))
                
                for vi in v.ingredients:
                    db.add(models.ProductVariantIngredient(
                        variant_id=db_variant.id, 
                        ingredient_id=vi.ingredient_id, 
                        quantity=vi.quantity
                    ))

        # 4. МОДИФІКАТОРИ
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

        # 5. ГРУПИ ПРОЦЕСІВ
        if product.process_group_ids:
            for pg_id in product.process_group_ids:
                pg = db.query(models.ProcessGroup).filter(
                    models.ProcessGroup.id == pg_id
                ).first()
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

        # 1. Оновлення простих полів
        db_product.name = product_data.name
        db_product.description = product_data.description
        db_product.price = product_data.price
        db_product.category_id = product_data.category_id
        db_product.has_variants = product_data.has_variants
        db_product.master_recipe_id = product_data.master_recipe_id
        db_product.output_weight = product_data.output_weight
        
        db_product.track_stock = product_data.track_stock
        if not product_data.track_stock:
             db_product.stock_quantity = product_data.stock_quantity

        # 2. Оновлення матеріалів (Consumables)
        db.query(models.ProductConsumable).filter(
            models.ProductConsumable.product_id == product_id
        ).delete()
        
        for cons in product_data.consumables:
            db.add(models.ProductConsumable(
                product_id=product_id, 
                consumable_id=cons.consumable_id, 
                quantity=cons.quantity
            ))

        # 3. ОНОВЛЕННЯ ВАРІАНТІВ
        if product_data.has_variants and product_data.variants:
            
            # [A] ВИДАЛЕННЯ: Знаходимо варіанти, яких немає в новому списку
            incoming_names = [v.name for v in product_data.variants]
            
            # Знаходимо об'єкти, які треба видалити
            variants_to_delete = db.query(models.ProductVariant).filter(
               models.ProductVariant.product_id == product_id,
               models.ProductVariant.name.notin_(incoming_names)
            ).all()

            # --- ВИПРАВЛЕННЯ: Безпечне видалення ---
            for variant in variants_to_delete:
                # Спочатку видаляємо залежності (дітей)
                db.query(models.ProductVariantConsumable).filter(
                    models.ProductVariantConsumable.variant_id == variant.id
                ).delete()
                
                db.query(models.ProductVariantIngredient).filter(
                    models.ProductVariantIngredient.variant_id == variant.id
                ).delete()
                
                # Тепер можна видаляти сам варіант
                db.delete(variant)
            # --------------------------------------

            # [B] ОНОВЛЕННЯ або СТВОРЕННЯ
            for v in product_data.variants:
                db_variant = db.query(models.ProductVariant).filter(
                    models.ProductVariant.product_id == product_id,
                    models.ProductVariant.name == v.name
                ).first()

                if db_variant:
                    # Оновлюємо
                    db_variant.price = v.price
                    db_variant.master_recipe_id = v.master_recipe_id
                    db_variant.output_weight = v.output_weight
                    db_variant.stock_quantity = v.stock_quantity
                else:
                    # Створюємо
                    sku = v.sku if v.sku else str(uuid.uuid4())
                    db_variant = models.ProductVariant(
                        product_id=product_id,
                        name=v.name,
                        price=v.price,
                        sku=sku,
                        master_recipe_id=v.master_recipe_id,
                        output_weight=v.output_weight,
                        stock_quantity=v.stock_quantity
                    )
                    db.add(db_variant)
                
                db.flush() 

                # [C] Очищаємо та перезаписуємо склад варіанту
                db.query(models.ProductVariantConsumable).filter(
                    models.ProductVariantConsumable.variant_id == db_variant.id
                ).delete()

                db.query(models.ProductVariantIngredient).filter(
                    models.ProductVariantIngredient.variant_id == db_variant.id
                ).delete()

                for vc in v.consumables:
                    db.add(models.ProductVariantConsumable(
                        variant_id=db_variant.id, 
                        consumable_id=vc.consumable_id, 
                        quantity=vc.quantity
                    ))
                
                for vi in v.ingredients:
                    db.add(models.ProductVariantIngredient(
                        variant_id=db_variant.id, 
                        ingredient_id=vi.ingredient_id, 
                        quantity=vi.quantity
                    ))
        else:
            # Якщо зняли галочку "Варіанти" - видаляємо все
            # Тут теж треба безпечне видалення, якщо у варіантів є діти
            all_variants = db.query(models.ProductVariant).filter(
                models.ProductVariant.product_id == product_id
            ).all()
            
            for variant in all_variants:
                db.query(models.ProductVariantConsumable).filter_by(variant_id=variant.id).delete()
                db.query(models.ProductVariantIngredient).filter_by(variant_id=variant.id).delete()
                db.delete(variant)

        # 4. МОДИФІКАТОРИ
        db.query(models.ProductModifierGroup).filter(
            models.ProductModifierGroup.product_id == product_id
        ).delete()
        
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