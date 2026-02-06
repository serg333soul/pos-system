from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas

class ProductService:
    """
    Клас для управління товарами.
    Вся логіка створення, оновлення та розрахунку вартості.
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
                        # Логіка: Якщо в рецепті %, беремо від ваги виходу. Якщо ні - фіксована вага.
                        qty = (item.quantity / 100.0 * data.output_weight) if item.is_percentage else item.quantity
                        total_cost += item.ingredient.cost_per_unit * qty
        
        return round(total_cost, 2)

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

        # 2. ДОДАВАННЯ ВИТРАТНИХ МАТЕРІАЛІВ
        if product.consumables:
            for cons in product.consumables:
                db.add(models.ProductConsumable(
                    product_id=db_product.id, 
                    consumable_id=cons.consumable_id, 
                    quantity=cons.quantity
                ))

        # 3. 🔥 FIX: ДОДАВАННЯ ПРЯМИХ ІНГРЕДІЄНТІВ (Було відсутнє)
        if product.ingredients:
            for ing in product.ingredients:
                db.add(models.ProductIngredient(
                    product_id=db_product.id,
                    ingredient_id=ing.ingredient_id,
                    quantity=ing.quantity
                ))

        # 4. ОБРОБКА ВАРІАНТІВ
        if product.has_variants and product.variants:
            for variant_data in product.variants:
                db_variant = models.ProductVariant(
                    product_id=db_product.id,
                    name=variant_data.name,
                    price=variant_data.price,
                    sku=variant_data.sku,
                    master_recipe_id=variant_data.master_recipe_id,
                    output_weight=variant_data.output_weight,
                    stock_quantity=variant_data.stock_quantity
                )
                db.add(db_variant)
                db.flush() 
                
                for vc in variant_data.consumables:
                    db.add(models.ProductVariantConsumable(
                        variant_id=db_variant.id,
                        consumable_id=vc.consumable_id,
                        quantity=vc.quantity
                    ))
                
                for vi in variant_data.ingredients:
                    db.add(models.ProductVariantIngredient(
                        variant_id=db_variant.id,
                        ingredient_id=vi.ingredient_id,
                        quantity=vi.quantity
                    ))

        # 5. МОДИФІКАТОРИ
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

        # 6. ПРОЦЕСИ
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

        # Оновлення основних полів
        db_product.name = product_data.name
        db_product.price = product_data.price
        db_product.description = product_data.description
        db_product.category_id = product_data.category_id
        db_product.has_variants = product_data.has_variants
        db_product.master_recipe_id = product_data.master_recipe_id
        db_product.output_weight = product_data.output_weight
        db_product.track_stock = product_data.track_stock
        
        if product_data.track_stock:
             db_product.stock_quantity = product_data.stock_quantity

        # 1. Очищення старих зв'язків (Consumables + Ingredients)
        db.query(models.ProductConsumable).filter_by(product_id=product_id).delete()
        db.query(models.ProductIngredient).filter_by(product_id=product_id).delete() # 🔥 FIX
        
        # 2. Перезапис Consumables
        for cons in product_data.consumables:
            db.add(models.ProductConsumable(
                product_id=product_id, 
                consumable_id=cons.consumable_id, 
                quantity=cons.quantity
            ))
            
        # 3. 🔥 FIX: Перезапис Ingredients
        for ing in product_data.ingredients:
            db.add(models.ProductIngredient(
                product_id=product_id,
                ingredient_id=ing.ingredient_id,
                quantity=ing.quantity
            ))

        # 4. ВАРІАНТИ (Повне видалення і створення заново)
        old_variants = db.query(models.ProductVariant).filter(models.ProductVariant.product_id == product_id).all()
        for variant in old_variants:
            db.query(models.ProductVariantConsumable).filter_by(variant_id=variant.id).delete()
            db.query(models.ProductVariantIngredient).filter_by(variant_id=variant.id).delete()
            db.delete(variant)
            
        if product_data.has_variants and product_data.variants:
             for variant_data in product_data.variants:
                db_variant = models.ProductVariant(
                    product_id=product_id,
                    name=variant_data.name,
                    price=variant_data.price,
                    sku=variant_data.sku,
                    master_recipe_id=variant_data.master_recipe_id,
                    output_weight=variant_data.output_weight,
                    stock_quantity=variant_data.stock_quantity
                )
                db.add(db_variant)
                db.flush() 
                
                for vc in variant_data.consumables:
                    db.add(models.ProductVariantConsumable(
                        variant_id=db_variant.id,
                        consumable_id=vc.consumable_id,
                        quantity=vc.quantity
                    ))
                
                for vi in variant_data.ingredients:
                    db.add(models.ProductVariantIngredient(
                        variant_id=db_variant.id,
                        ingredient_id=vi.ingredient_id,
                        quantity=vi.quantity
                    ))

        # 5. МОДИФІКАТОРИ
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

        # 6. ПРОЦЕСИ
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