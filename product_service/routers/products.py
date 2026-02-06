# FILE: product_service/routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import database, schemas, models
from services.product_service import ProductService
from services.inventory_logger import InventoryLogger

router = APIRouter(prefix="/products", tags=["Products"])

# --- КАЛЬКУЛЯТОР СОБІВАРТОСТІ ---
@router.post("/calculate-cost")
def calculate_cost(data: schemas.ProductCostCheck, db: Session = Depends(database.get_db)):
    """
    Рахує собівартість товару "на льоту".
    """
    cost = ProductService.calculate_product_cost(db, data)
    return {"total_cost": cost}

# --- CRUD ОПЕРАЦІЇ ---

@router.post("/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    return ProductService.create_product(db, product)

@router.put("/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_data: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    updated_product = ProductService.update_product(db, product_id, product_data)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product

@router.get("/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    # Дозаповнюємо назви для UI
    for p in products:
        for c in p.consumables:
            if c.consumable: c.consumable_name = c.consumable.name
        for i in p.ingredients:
            if i.ingredient: i.ingredient_name = i.ingredient.name
        for v in p.variants:
            for vc in v.consumables:
                if vc.consumable: vc.consumable_name = vc.consumable.name
            if hasattr(v, 'ingredients'):
                 for vi in v.ingredients:
                     if vi.ingredient: vi.ingredient_name = vi.ingredient.name
    return products

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for c in p.consumables:
        if c.consumable: c.consumable_name = c.consumable.name
    for i in p.ingredients:
        if i.ingredient: i.ingredient_name = i.ingredient.name
    for v in p.variants:
        for vc in v.consumables:
            if vc.consumable: vc.consumable_name = vc.consumable.name
        if hasattr(v, 'ingredients'):
             for vi in v.ingredients:
                 if vi.ingredient: vi.ingredient_name = vi.ingredient.name
    return p

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.query(models.ProductVariant).filter(models.ProductVariant.product_id == product_id).delete()
    db.query(models.ProductModifierGroup).filter(models.ProductModifierGroup.product_id == product_id).delete()
    db.query(models.ProductConsumable).filter(models.ProductConsumable.product_id == product_id).delete()
    db.query(models.ProductIngredient).filter(models.ProductIngredient.product_id == product_id).delete()
    
    db.delete(product)
    db.commit()
    return {"status": "deleted"}

@router.post("/{product_id}/stock")
def update_stock(product_id: int, qty: float, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_qty = product.stock_quantity
    product.stock_quantity = qty
    InventoryLogger.log(
        db, "product", product.id, product.name, 
        old_qty, qty, "manual_correction"
    )
    db.commit()
    return {"status": "updated", "new_quantity": qty}

# 🔥 ФІНАЛЬНИЙ ВАРІАНТ СПИСАННЯ (HARDCORE MODE) 🔥
@router.post("/deduct_stock_for_order")
def deduct_stock_for_order(items: List[schemas.StockDeductionItem], db: Session = Depends(database.get_db)):
    print(f"📦 [DEDUCT] Отримано запит: {len(items)} позицій")
    
    for item in items:
        # === 1. ВАРІАНТИ (ТУТ ВСЕ ПРАЦЮВАЛО, ЗАЛИШАЄМО ЯК Є) ===
        if item.variant_id is not None:
            variant_id = item.variant_id
            print(f"  🔹 Варіант ID: {variant_id}")

            variant = db.query(models.ProductVariant).options(
                joinedload(models.ProductVariant.ingredients).joinedload(models.ProductVariantIngredient.ingredient),
                joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable),
                joinedload(models.ProductVariant.product)
            ).filter(models.ProductVariant.id == variant_id).first()

            if variant:
                # А. Списання варіанту
                old_v = variant.stock_quantity
                variant.stock_quantity -= item.quantity
                InventoryLogger.log(
                    db, "product_variant", variant.id, 
                    f"{variant.product.name} ({variant.name})", 
                    old_v, variant.stock_quantity, 
                    f"sale_order_{item.order_id}"
                )

                # Б. Інгредієнти варіанту
                for link in variant.ingredients:
                    if link.ingredient:
                        deduct = link.quantity * item.quantity
                        old_ing = link.ingredient.stock_quantity
                        link.ingredient.stock_quantity -= deduct
                        InventoryLogger.log(
                            db, "ingredient", link.ingredient.id, link.ingredient.name,
                            old_ing, link.ingredient.stock_quantity,
                            f"sale_order_{item.order_id}_var_{variant.id}"
                        )
                
                # В. Матеріали варіанту
                for link in variant.consumables:
                    if link.consumable:
                        deduct = link.quantity * item.quantity
                        old_cons = link.consumable.stock_quantity
                        link.consumable.stock_quantity -= deduct
                        InventoryLogger.log(
                            db, "consumable", link.consumable.id, link.consumable.name,
                            old_cons, link.consumable.stock_quantity,
                            f"sale_order_{item.order_id}_var_{variant.id}"
                        )

        # === 2. ПРОСТІ ТОВАРИ (ТУТ БУЛА ПРОБЛЕМА) ===
        else:
            product_id = item.product_id
            print(f"  🔹 Простий Товар ID: {product_id}")

            # 1. Списуємо сам товар
            product = db.query(models.Product).filter(models.Product.id == product_id).first()
            if product:
                old_p = product.stock_quantity
                product.stock_quantity -= item.quantity
                InventoryLogger.log(
                    db, "product", product.id, product.name, 
                    old_p, product.stock_quantity, 
                    f"sale_order_{item.order_id}"
                )
                
                # --- 🔥 ВИПРАВЛЕННЯ: ЯВНИЙ ЗАПИТ ДО БАЗИ ---
                # Ми не покладаємось на product.ingredients, ми беремо дані напряму з таблиці
                direct_ingredients = db.query(models.ProductIngredient).filter(
                    models.ProductIngredient.product_id == product.id
                ).all()

                print(f"     🔍 Знайдено прямих інгредієнтів (SQL): {len(direct_ingredients)}")
                
                for link in direct_ingredients:
                    # Отримуємо сам об'єкт інгредієнта, щоб змінити його залишок
                    real_ingredient = db.query(models.Ingredient).filter(
                        models.Ingredient.id == link.ingredient_id
                    ).first()

                    if real_ingredient:
                        deduct = link.quantity * item.quantity
                        old_ing = real_ingredient.stock_quantity
                        
                        print(f"        -> Списуємо {real_ingredient.name}: -{deduct}")
                        
                        real_ingredient.stock_quantity -= deduct
                        InventoryLogger.log(
                            db, "ingredient", real_ingredient.id, real_ingredient.name,
                            old_ing, real_ingredient.stock_quantity,
                            f"sale_order_{item.order_id}_prod_{product.id}"
                        )

                # 3. Витратні матеріали (Також робимо надійно)
                direct_consumables = db.query(models.ProductConsumable).filter(
                    models.ProductConsumable.product_id == product.id
                ).all()

                for link in direct_consumables:
                    real_cons = db.query(models.Consumable).filter(
                        models.Consumable.id == link.consumable_id
                    ).first()
                    
                    if real_cons:
                        deduct = link.quantity * item.quantity
                        old_cons = real_cons.stock_quantity
                        real_cons.stock_quantity -= deduct
                        InventoryLogger.log(
                            db, "consumable", real_cons.id, real_cons.name,
                            old_cons, real_cons.stock_quantity,
                            f"sale_order_{item.order_id}_prod_{product.id}"
                        )

                # 4. Рецепт (якщо є)
                if product.master_recipe:
                    # Для рецепту можна залишити Lazy Loading, або теж завантажити явно, 
                    # але зазвичай з рецептами проблем менше. 
                    # Додамо joinedload тут локально для надійності.
                    recipe = db.query(models.MasterRecipe).options(
                        joinedload(models.MasterRecipe.items).joinedload(models.MasterRecipeItem.ingredient)
                    ).filter(models.MasterRecipe.id == product.master_recipe_id).first()

                    if recipe:
                        print(f"     🔍 Рецепт: {recipe.name}")
                        for r_item in recipe.items:
                            if r_item.ingredient:
                                single_qty = 0
                                if r_item.is_percentage:
                                    single_qty = (r_item.quantity / 100.0) * product.output_weight
                                else:
                                    single_qty = r_item.quantity
                                
                                deduct = single_qty * item.quantity
                                old_ing = r_item.ingredient.stock_quantity
                                r_item.ingredient.stock_quantity -= deduct
                                InventoryLogger.log(
                                    db, "ingredient", r_item.ingredient.id, r_item.ingredient.name,
                                    old_ing, r_item.ingredient.stock_quantity,
                                    f"sale_order_{item.order_id}_recipe_{recipe.id}"
                                )
            else:
                 print(f"  ❌ Товар {product_id} не знайдено!")
    
    db.commit()
    print("✅ [DEDUCT] Транзакція завершена.")
    return {"status": "deducted"}