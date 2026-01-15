from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_
import models, schemas, database

app = FastAPI()

models.Base.metadata.create_all(bind=database.engine)

# --- ENDPOINTS ДЛЯ КАТЕГОРІЙ (ОНОВЛЕНО) ---

@app.post("/categories/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db)):
    # Перевіряємо дублікат
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    # Створюємо нову з урахуванням кольору і батька
    new_category = models.Category(
        name=category.name, 
        slug=category.slug,
        color=category.color,
        parent_id=category.parent_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    return categories

# --- ІНШІ ENDPOINTS (Залишаються без змін, код скорочено для зручності) ---

@app.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitCreate, db: Session = Depends(database.get_db)):
    db_unit = models.Unit(name=unit.name, symbol=unit.symbol)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.get("/units/", response_model=List[schemas.Unit])
def read_units(db: Session = Depends(database.get_db)):
    return db.query(models.Unit).all()

@app.post("/ingredients/", response_model=schemas.Ingredient)
def create_ingredient(ingredient: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Ingredient).filter(models.Ingredient.name == ingredient.name).first()
    if exists: raise HTTPException(status_code=400, detail="Ingredient already exists")
    new_item = models.Ingredient(name=ingredient.name, unit_id=ingredient.unit_id, cost_per_unit=ingredient.cost_per_unit, stock_quantity=ingredient.stock_quantity)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/ingredients/", response_model=List[schemas.Ingredient])
def read_ingredients(db: Session = Depends(database.get_db)):
    return db.query(models.Ingredient).all()

@app.put("/ingredients/{ingredient_id}", response_model=schemas.Ingredient)
def update_ingredient(ingredient_id: int, ingredient_data: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    db_ingredient = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ingredient: raise HTTPException(status_code=404, detail="Ingredient not found")
    db_ingredient.name = ingredient_data.name
    db_ingredient.unit_id = ingredient_data.unit_id
    db_ingredient.cost_per_unit = ingredient_data.cost_per_unit
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient

@app.delete("/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: int, db: Session = Depends(database.get_db)):
    db_ingredient = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ingredient: raise HTTPException(status_code=404, detail="Ingredient not found")
    try:
        db.delete(db_ingredient)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Неможливо видалити: інгредієнт використовується")
    return {"status": "deleted"}

@app.post("/recipes/", response_model=schemas.MasterRecipe)
def create_recipe(recipe: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    new_recipe = models.MasterRecipe(name=recipe.name, description=recipe.description)
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)
    
    for item in recipe.items:
        db.add(models.MasterRecipeItem(recipe_id=new_recipe.id, ingredient_id=item.ingredient_id, quantity=item.quantity))
    
    db.commit()
    db.refresh(new_recipe)
    return new_recipe

@app.get("/recipes/", response_model=List[schemas.MasterRecipe])
def read_recipes(db: Session = Depends(database.get_db)):
    recipes = db.query(models.MasterRecipe).all()
    # Мануально додамо назви інгредієнтів для зручності
    for r in recipes:
        for i in r.items:
            i.ingredient_name = i.ingredient.name if i.ingredient else "Unknown"
    return recipes

@app.put("/recipes/{recipe_id}", response_model=schemas.MasterRecipe)
def update_recipe(recipe_id: int, recipe_data: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe: raise HTTPException(status_code=404, detail="Recipe not found")
    
    db_recipe.name = recipe_data.name
    db_recipe.description = recipe_data.description
    
    # Видаляємо старі елементи
    db_recipe.items = []
    db.flush()
    
    # Додаємо нові
    for item in recipe_data.items:
        db.add(models.MasterRecipeItem(recipe_id=db_recipe.id, ingredient_id=item.ingredient_id, quantity=item.quantity))
        
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(database.get_db)):
    # Перевіримо, чи використовується рецепт
    in_prod = db.query(models.Product).filter(models.Product.master_recipe_id == recipe_id).first()
    in_var = db.query(models.ProductVariant).filter(models.ProductVariant.master_recipe_id == recipe_id).first()
    
    if in_prod or in_var:
        raise HTTPException(status_code=400, detail="Цей рецепт використовується у товарах. Спочатку відв'яжіть його.")
        
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe: raise HTTPException(status_code=404)
    db.delete(db_recipe)
    db.commit()
    return {"status": "deleted"}

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    db_product = models.Product(
        name=product.name, 
        price=product.price, 
        description=product.description, 
        category_id=product.category_id, 
        has_variants=product.has_variants,
        master_recipe_id=product.master_recipe_id # <-- Зберігаємо лінк на рецепт
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Варіанти
    if product.has_variants and product.variants:
        for v in product.variants:
            db_variant = models.ProductVariant(
                product_id=db_product.id, name=v.name, price=v.price, sku=v.sku,
                master_recipe_id=v.master_recipe_id # <-- Лінк на рецепт для варіанту
            )
            db.add(db_variant)
    
    # Модифікатори
    for group in product.modifier_groups:
        db_group = models.ProductModifierGroup(product_id=db_product.id, name=group.name, is_required=group.is_required)
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        for mod in group.modifiers:
            db.add(models.Modifier(group_id=db_group.id, name=mod.name, price_change=mod.price_change, ingredient_id=mod.ingredient_id, quantity=mod.quantity))
            
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    return db.query(models.Product).all()

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_data: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product: raise HTTPException(status_code=404)

    db_product.name = product_data.name
    db_product.description = product_data.description
    db_product.price = product_data.price
    db_product.category_id = product_data.category_id
    db_product.has_variants = product_data.has_variants
    db_product.master_recipe_id = product_data.master_recipe_id # <-- Оновлюємо лінк
    
    # Очистка старих
    db_product.variants = []
    db_product.modifier_groups = []
    db.flush()

    # Створення нових
    if product_data.has_variants and product_data.variants:
        for v in product_data.variants:
            db.add(models.ProductVariant(
                product_id=db_product.id, name=v.name, price=v.price, sku=v.sku,
                master_recipe_id=v.master_recipe_id # <--
            ))
            
    for group in product_data.modifier_groups:
        db_group = models.ProductModifierGroup(product_id=db_product.id, name=group.name, is_required=group.is_required)
        db.add(db_group)
        db.flush()
        for mod in group.modifiers:
            db.add(models.Modifier(group_id=db_group.id, name=mod.name, price_change=mod.price_change, ingredient_id=mod.ingredient_id, quantity=mod.quantity))

    db.commit()
    db.refresh(db_product)
    return db_product


@app.post("/customers/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Customer).filter(models.Customer.phone == customer.phone).first()
    if exists: raise HTTPException(status_code=400, detail="Клієнт вже існує")
    new_customer = models.Customer(**customer.dict())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@app.put("/customers/{customer_id}", response_model=schemas.Customer)
def update_customer(customer_id: int, customer_data: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer: raise HTTPException(status_code=404, detail="Customer not found")
    db_customer.name = customer_data.name
    db_customer.phone = customer_data.phone
    db_customer.email = customer_data.email
    db_customer.notes = customer_data.notes
    try: db.commit(); db.refresh(db_customer)
    except: db.rollback(); raise HTTPException(status_code=400, detail="Помилка оновлення")
    return db_customer

@app.get("/customers/search/", response_model=List[schemas.Customer])
def search_customers(q: str, db: Session = Depends(database.get_db)):
    search_term = f"%{q}%"
    return db.query(models.Customer).filter(or_(models.Customer.name.ilike(search_term), models.Customer.phone.ilike(search_term))).limit(10).all()

@app.get("/customers/", response_model=List[schemas.Customer])
def read_customers(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    return db.query(models.Customer).offset(skip).limit(limit).all()

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()
    return {"status": "deleted"}

# --- CHECKOUT (ЛОГІКА СПИСАННЯ) ---

@app.post("/orders/checkout/")
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    new_order = models.Order(total_price=order_data.total_price, payment_method=order_data.payment_method, customer_id=order_data.customer_id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    for item in order_data.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product: continue
        
        item_name = product.name
        price = product.price
        details_list = []
        
        # 1. Знаходимо, який рецепт використовувати
        target_recipe_id = None
        
        if item.variant_id:
            variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
            if variant:
                item_name = f"{product.name} ({variant.name})"
                price = variant.price
                details_list.append(f"Варіант: {variant.name}")
                # Пріоритет: Рецепт варіанту -> Рецепт товару
                target_recipe_id = variant.master_recipe_id or product.master_recipe_id
        else:
            # Для простого товару
            target_recipe_id = product.master_recipe_id

        # 2. Списуємо інгредієнти з рецепту (якщо є)
        if target_recipe_id:
            recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == target_recipe_id).first()
            if recipe:
                for r_item in recipe.items:
                    if r_item.ingredient:
                        # Списання: к-сть в рецепті * к-сть товару
                        r_item.ingredient.stock_quantity -= r_item.quantity * item.quantity
                        db.add(r_item.ingredient)

        # 3. Списуємо модифікатори
        for mod_item in item.modifiers:
            mod = db.query(models.Modifier).filter(models.Modifier.id == mod_item.modifier_id).first()
            if mod:
                details_list.append(mod.name)
                if mod.ingredient:
                    mod.ingredient.stock_quantity -= mod.quantity * item.quantity
                    db.add(mod.ingredient)

        db.add(models.OrderItem(
            order_id=new_order.id, 
            product_name=item_name, 
            quantity=item.quantity, 
            price_at_moment=price, 
            details=", ".join(details_list)
        ))
        
    db.commit()
    return {"status": "ok", "order_id": new_order.id}

@app.get("/orders/", response_model=List[schemas.OrderRead])
def get_orders(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/customers/{customer_id}/orders/", response_model=List[schemas.OrderRead])
def read_customer_orders(customer_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(models.Order.customer_id == customer_id).order_by(models.Order.created_at.desc()).all()