from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    # 1. Створюємо сам товар
    db_product = models.Product(
        name=product.name,
        price=product.price,
        description=product.description,
        category_id=product.category_id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product) # Отримуємо ID нового товару

    # 2. Додаємо інгредієнти рецепта
    for item in product.recipe:
        db_recipe_item = models.ProductIngredient(
            product_id=db_product.id,
            ingredient_id=item.ingredient_id,
            quantity=item.quantity
        )
        db.add(db_recipe_item)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    
    # БЕЗПЕЧНИЙ ЦИКЛ
    for p in products:
        # Якщо у товара є рецепт
        if p.recipe:
            for r in p.recipe:
                # Перевіряємо, чи існує інгредієнт (щоб не впало, якщо його видалили)
                if r.ingredient:
                    r.ingredient_name = r.ingredient.name
                else:
                    r.ingredient_name = "Видалено"
            
    return products

# --- ОБРОБКА ЗАМОВЛЕННЯ (НОВЕ) ---
@app.post("/orders/checkout/") # <--- Змінили URL, щоб було логічно
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    """
    1. Створює запис про замовлення (Order).
    2. Додає товари в історію (OrderItem).
    3. Списує інгредієнти зі складу.
    """
    
    # 1. Створюємо чек (Order)
    new_order = models.Order(
        total_price=order_data.total_price,
        payment_method=order_data.payment_method
        # created_at додається автоматично
    )
    db.add(new_order)
    db.commit()      # Комітимо, щоб отримати ID замовлення
    db.refresh(new_order)

    # 2. Проходимо по кожному купленому товару
    for item in order_data.items:
        # Знаходимо товар в базі, щоб дізнатися його назву і рецепт
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        
        if not product:
            continue # Якщо товара вже не існує, пропускаємо (хоча це дивно)

        # А. Додаємо запис в історію (OrderItem)
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_name=product.name,
            quantity=item.quantity,
            price_at_moment=product.price
        )
        db.add(order_item)

        # Б. Списуємо інгредієнти (Стара логіка)
        for recipe_item in product.recipe:
            ingredient = recipe_item.ingredient
            if ingredient:
                amount_to_deduct = recipe_item.quantity * item.quantity
                ingredient.stock_quantity -= amount_to_deduct
                db.add(ingredient)

    # 3. Зберігаємо всі зміни (Історію + Списання)
    db.commit()
    
    return {"message": "Замовлення успішне", "order_id": new_order.id}

# --- ОТРИМАТИ ІСТОРІЮ ЗАМОВЛЕНЬ ---
@app.get("/orders/", response_model=List[schemas.OrderRead])
def get_orders(skip: int = 0, limit: int = 50, db: Session = Depends(database.get_db)):
    # Повертаємо замовлення, сортуючи від нових до старих
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders