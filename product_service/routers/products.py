# FILE: product_service/routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
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

# 🔥 НОВИЙ РОУТ: Отримати розрахунковий залишок варіанту
@router.get("/{product_id}/variants/{variant_id}/calculated-stock")
def get_variant_calculated_stock(
    product_id: int, 
    variant_id: int, 
    db: Session = Depends(database.get_db)
):
    """
    Повертає максимальну кількість одиниць, яку можна виготовити 
    на основі залишків інгредієнтів.
    """
    stock = ProductService.calculate_max_possible_stock(db, variant_id)
    return {"calculated_stock": stock}

# 🔥 НОВИЙ РОУТ: Розумна історія (Товар + Варіанти)
@router.get("/{product_id}/history", response_model=List[schemas.InventoryTransactionRead])
def get_product_history(product_id: int, db: Session = Depends(database.get_db)):
    """
    Отримує об'єднану історію руху коштів/товарів.
    Якщо це простий товар - повертає його історію.
    Якщо товар з варіантами - підтягує історію всіх його варіантів.
    """
    product = db.query(models.Product).options(joinedload(models.Product.variants)).filter(models.Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Формуємо критерії пошуку: (Type=Product AND ID=X)
    criteria = [
        and_(models.InventoryTransaction.entity_type == "product", models.InventoryTransaction.entity_id == product_id)
    ]

    # Якщо є варіанти, додаємо: OR (Type=Variant AND ID in [v1, v2...])
    if product.variants:
        variant_ids = [v.id for v in product.variants]
        if variant_ids:
            criteria.append(
                and_(models.InventoryTransaction.entity_type == "product_variant", models.InventoryTransaction.entity_id.in_(variant_ids))
            )

    # Виконуємо запит з OR
    history = db.query(models.InventoryTransaction).filter(or_(*criteria)).order_by(models.InventoryTransaction.created_at.desc()).all()
    return history

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
    # Використовуємо .options(joinedload(...)) для глибокого завантаження всієї структури [4, 5]
    products = db.query(models.Product).options(
        joinedload(models.Product.category),
        # Завантажуємо варіанти -> їхні матеріали -> об'єкт матеріалу (де лежить name) [6, 7]
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable),
        # Завантажуємо варіанти -> їхні інгредієнти -> об'єкт інгредієнта [7, 8]
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients).joinedload(models.ProductVariantIngredient.ingredient),
        # Завантажуємо матеріали та інгредієнти для простого товару [9, 10]
        joinedload(models.Product.consumables).joinedload(models.ProductConsumable.consumable),
        joinedload(models.Product.ingredients).joinedload(models.ProductIngredient.ingredient)
    ).all()

    # Тепер об'єкти вже в пам'яті, і ми можемо безпечно переприсвоїти імена для схем Pydantic [1, 7]
    for p in products:

        # Захист для основного товару
        if p.stock_quantity is None: p.stock_quantity = 0.0
        if p.price is None: p.price = 0.0
        if p.output_weight is None: p.output_weight = 0.0

        # Для простого товару
        for c in p.consumables:
            if c.consumable: c.consumable_name = c.consumable.name
        for i in p.ingredients:
            if i.ingredient: i.ingredient_name = i.ingredient.name
            
        # Для варіантів (це те, що у тебе "відпадало")
        for v in p.variants:
            # Захист для варіантів
            if v.stock_quantity is None: v.stock_quantity = 0.0
            if v.price is None: v.price = 0.0
            if v.output_weight is None: v.output_weight = 0.0

            if v.master_recipe_id and not p.track_stock:
                try:
                    v.stock_quantity = ProductService.calculate_max_possible_stock(db, v.id)
                except Exception as e:
                    print(f"⚠️ Помилка розрахунку для варіанта {v.id}: {e}")
                    v.stock_quantity = 0.0
            
            # ПЕРЕВІРКА: чи не приходить None?
            if v.stock_quantity is None:
                v.stock_quantity = 0.0

            for vc in v.consumables:
                if vc.consumable: 
                    vc.consumable_name = vc.consumable.name
            for vi in v.ingredients:
                if vi.ingredient: 
                    vi.ingredient_name = vi.ingredient.name
                    
    return products

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(database.get_db)):
    # Застосовуємо аналогічну логіку joinedload для одного товару [2, 7]
    p = db.query(models.Product).options(
        joinedload(models.Product.category),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients).joinedload(models.ProductVariantIngredient.ingredient),
        joinedload(models.Product.consumables).joinedload(models.ProductConsumable.consumable),
        joinedload(models.Product.ingredients).joinedload(models.ProductIngredient.ingredient)
    ).filter(models.Product.id == product_id).first()

    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Мапінг імен (тепер consumable гарантовано не буде None завдяки joinedload) [11]
    for c in p.consumables:
        if c.consumable: c.consumable_name = c.consumable.name
    for i in p.ingredients:
        if i.ingredient: i.ingredient_name = i.ingredient.name
        
    for v in p.variants:
        for vc in v.consumables:
            if vc.consumable: 
                vc.consumable_name = vc.consumable.name
        for vi in v.ingredients:
            if vi.ingredient: 
                vi.ingredient_name = vi.ingredient.name
                
    return p

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    # Використовуємо сервіс, який ми вже написали для безпечного видалення
    success = ProductService.delete_product(db, product_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return {"status": "deleted", "message": f"Product {product_id} and all its components removed"}

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