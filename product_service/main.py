from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_ # Для пошуку "або ім'я або телефон"

# Імпортуємо наші файли
import models, schemas, database

app = FastAPI()

# 1. Створюємо таблиці в БД при старті (якщо їх немає)
models.Base.metadata.create_all(bind=database.engine)

# --- ENDPOINTS ДЛЯ КАТЕГОРІЙ ---

# Створити категорію
@app.post("/categories/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db)):
    # Перевіряємо, чи існує така категорія
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    # Створюємо нову
    new_category = models.Category(name=category.name, slug=category.slug)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

# Отримати список категорій
@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    return categories

# ... (імпорти та категорії залишаються зверху) ...

# --- ОДИНИЦІ ВИМІРУ ---

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

# --- ІНГРЕДІЄНТИ ---

@app.post("/ingredients/", response_model=schemas.Ingredient)
def create_ingredient(ingredient: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    # Перевірка на дублікат
    exists = db.query(models.Ingredient).filter(models.Ingredient.name == ingredient.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ingredient already exists")

    new_item = models.Ingredient(
        name=ingredient.name,
        unit_id=ingredient.unit_id,
        cost_per_unit=ingredient.cost_per_unit,
        stock_quantity=ingredient.stock_quantity
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/ingredients/", response_model=List[schemas.Ingredient])
def read_ingredients(db: Session = Depends(database.get_db)):
    return db.query(models.Ingredient).all()

# --- ТОВАРИ (PRODUCTS) ---

# --- PRODUCTS (ОНОВЛЕНО) ---
@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    # 1. Створюємо Product
    db_product = models.Product(
        name=product.name,
        price=product.price,
        description=product.description,
        category_id=product.category_id,
        has_variants=product.has_variants
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 2. Якщо є прості рецепти (для простих товарів)
    if not product.has_variants and product.recipe:
        for item in product.recipe:
            db_recipe = models.ProductRecipe(
                product_id=db_product.id,
                ingredient_id=item.ingredient_id,
                quantity=item.quantity
            )
            db.add(db_recipe)

    # 3. Якщо є ВАРІАНТИ
    if product.has_variants and product.variants:
        for v in product.variants:
            db_variant = models.ProductVariant(
                product_id=db_product.id,
                name=v.name,
                price=v.price,
                sku=v.sku
            )
            db.add(db_variant)
            db.commit() # Треба ID варіанту
            db.refresh(db_variant)

            # Рецепт варіанту
            for r_item in v.recipe:
                db_var_recipe = models.VariantRecipe(
                    variant_id=db_variant.id,
                    ingredient_id=r_item.ingredient_id,
                    quantity=r_item.quantity
                )
                db.add(db_var_recipe)

    # 4. Модифікатори
    for group in product.modifier_groups:
        db_group = models.ProductModifierGroup(
            product_id=db_product.id,
            name=group.name,
            is_required=group.is_required
        )
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        
        for mod in group.modifiers:
            db_mod = models.Modifier(
                group_id=db_group.id,
                name=mod.name,
                price_change=mod.price_change,
                ingredient_id=mod.ingredient_id,
                quantity=mod.quantity
            )
            db.add(db_mod)

    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    # Завантажуємо продукти з усіма зв'язками
    products = db.query(models.Product).all()
    # Мапінг для схем (Pydantic сам спробує, але для VariantRecipe треба обережно)
    # Тут SQLAlchemy lazy loading підтягне variants та їх рецепти
    return products

# --- CRM: КЛІЄНТИ ---

# 1. Створити клієнта
@app.post("/customers/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    # Перевірка на дублікат телефону
    exists = db.query(models.Customer).filter(models.Customer.phone == customer.phone).first()
    if exists:
        raise HTTPException(status_code=400, detail="Клієнт з таким телефоном вже існує")
    
    new_customer = models.Customer(**customer.dict())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

# 5. Редагувати (Оновити)
@app.put("/customers/{customer_id}", response_model=schemas.Customer)
def update_customer(customer_id: int, customer_data: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Оновлюємо поля
    db_customer.name = customer_data.name
    db_customer.phone = customer_data.phone
    db_customer.email = customer_data.email
    db_customer.notes = customer_data.notes
    
    try:
        db.commit()
        db.refresh(db_customer)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Можливо, такий телефон вже існує")
        
    return db_customer

# 2. Пошук клієнтів (Живий пошук)
@app.get("/customers/search/", response_model=List[schemas.Customer])
def search_customers(q: str, db: Session = Depends(database.get_db)):
    # Шукаємо, де запит схожий на Ім'я АБО на Телефон
    search_term = f"%{q}%"
    results = db.query(models.Customer).filter(
        or_(
            models.Customer.name.ilike(search_term),
            models.Customer.phone.ilike(search_term)
        )
    ).limit(10).all()
    return results

# 3. Отримати всіх (для адмінки)
@app.get("/customers/", response_model=List[schemas.Customer])
def read_customers(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    return db.query(models.Customer).offset(skip).limit(limit).all()

# 4. Видалити
@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return {"status": "deleted"}

# --- ОБРОБКА ЗАМОВЛЕННЯ (НОВЕ) ---
# --- CHECKOUT (ОНОВЛЕНО ДЛЯ ВАРІАНТІВ) ---
@app.post("/orders/checkout/")
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    # 1. Створюємо Order
    new_order = models.Order(
        total_price=order_data.total_price,
        payment_method=order_data.payment_method,
        customer_id=order_data.customer_id
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 2. Обробка товарів
    for item in order_data.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product: continue

        item_name = product.name
        price = product.price
        details_list = []

        # А. Якщо це ВАРІАНТ
        if item.variant_id:
            variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
            if variant:
                item_name = f"{product.name} ({variant.name})"
                price = variant.price
                details_list.append(f"Варіант: {variant.name}")
                
                # Списання по рецепту варіанту
                for r in variant.variant_recipe:
                     if r.ingredient:
                        r.ingredient.stock_quantity -= r.quantity * item.quantity
                        db.add(r.ingredient)
        else:
            # Списання по простому рецепту
             for r in product.recipe:
                 if r.ingredient:
                    r.ingredient.stock_quantity -= r.quantity * item.quantity
                    db.add(r.ingredient)

        # Б. Обробка МОДИФІКАТОРІВ
        for mod_item in item.modifiers:
            mod = db.query(models.Modifier).filter(models.Modifier.id == mod_item.modifier_id).first()
            if mod:
                details_list.append(mod.name)
                # Якщо модифікатор щось списує (напр. коробку)
                if mod.ingredient:
                    mod.ingredient.stock_quantity -= mod.quantity * item.quantity
                    db.add(mod.ingredient)

        # 3. Запис в історію
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_name=item_name,
            quantity=item.quantity,
            price_at_moment=price,
            details=", ".join(details_list)
        )
        db.add(order_item)

    db.commit()
    return {"status": "ok", "order_id": new_order.id}

# --- ОТРИМАТИ ІСТОРІЮ ЗАМОВЛЕНЬ ---
@app.get("/orders/", response_model=List[schemas.OrderRead])
def get_orders(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    # Повертаємо замовлення, сортуючи від нових до старих
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders

# --- ІСТОРІЯ ПОКУПОК КЛІЄНТА ---
@app.get("/customers/{customer_id}/orders/", response_model=List[schemas.OrderRead])
def read_customer_orders(customer_id: int, db: Session = Depends(database.get_db)):
    # Знаходимо всі чеки цього клієнта, сортуємо від нових до старих
    orders = db.query(models.Order)\
        .filter(models.Order.customer_id == customer_id)\
        .order_by(models.Order.created_at.desc())\
        .all()
    return orders
