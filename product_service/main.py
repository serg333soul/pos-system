from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_
import models, schemas, database

app = FastAPI()

models.Base.metadata.create_all(bind=database.engine)

# --- ENDPOINTS ДЛЯ КАТЕГОРІЙ ---
@app.post("/categories/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db)):
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category: raise HTTPException(status_code=400, detail="Category already exists")
    new_category = models.Category(name=category.name, slug=category.slug, color=category.color, parent_id=category.parent_id)
    db.add(new_category)
    db.commit(); db.refresh(new_category)
    return new_category

@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return db.query(models.Category).offset(skip).limit(limit).all()

# --- UNITS ---
@app.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Unit).filter(or_(models.Unit.name == unit.name, models.Unit.symbol == unit.symbol)).first()
    if exists: raise HTTPException(status_code=400, detail="Одиниця існує")
    db_unit = models.Unit(name=unit.name, symbol=unit.symbol)
    db.add(db_unit); db.commit(); db.refresh(db_unit)
    return db_unit

@app.get("/units/", response_model=List[schemas.Unit])
def read_units(db: Session = Depends(database.get_db)):
    return db.query(models.Unit).all()

# --- INGREDIENTS ---
@app.post("/ingredients/", response_model=schemas.Ingredient)
def create_ingredient(ingredient: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Ingredient).filter(models.Ingredient.name == ingredient.name).first()
    if exists: raise HTTPException(status_code=400, detail="Ingredient already exists")
    new_item = models.Ingredient(**ingredient.dict())
    db.add(new_item); db.commit(); db.refresh(new_item)
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
    db.commit(); db.refresh(db_ingredient)
    return db_ingredient

@app.delete("/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: int, db: Session = Depends(database.get_db)):
    db_ingredient = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ingredient: raise HTTPException(status_code=404)
    try: db.delete(db_ingredient); db.commit()
    except: db.rollback(); raise HTTPException(status_code=400, detail="Used elsewhere")
    return {"status": "deleted"}

# --- НОВЕ: CONSUMABLES CRUD ---
@app.post("/consumables/", response_model=schemas.Consumable)
def create_consumable(item: schemas.ConsumableCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Consumable).filter(models.Consumable.name == item.name).first()
    if exists: raise HTTPException(status_code=400, detail="Вже існує")
    new_c = models.Consumable(**item.dict())
    db.add(new_c); db.commit(); db.refresh(new_c)
    return new_c

@app.get("/consumables/", response_model=List[schemas.Consumable])
def read_consumables(db: Session = Depends(database.get_db)):
    return db.query(models.Consumable).all()

@app.put("/consumables/{id}", response_model=schemas.Consumable)
def update_consumable(id: int, item: schemas.ConsumableCreate, db: Session = Depends(database.get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: raise HTTPException(status_code=404)
    for k, v in item.dict().items(): setattr(db_c, k, v)
    db.commit(); db.refresh(db_c)
    return db_c

@app.delete("/consumables/{id}")
def delete_consumable(id: int, db: Session = Depends(database.get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: raise HTTPException(status_code=404)
    db.delete(db_c); db.commit()
    return {"status": "deleted"}


# --- RECIPES ---
@app.post("/recipes/", response_model=schemas.MasterRecipe)
def create_recipe(recipe: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    new_recipe = models.MasterRecipe(name=recipe.name, description=recipe.description)
    db.add(new_recipe); db.commit(); db.refresh(new_recipe)
    for item in recipe.items:
        db.add(models.MasterRecipeItem(recipe_id=new_recipe.id, ingredient_id=item.ingredient_id, quantity=item.quantity, is_percentage=item.is_percentage))
    db.commit(); db.refresh(new_recipe)
    return new_recipe

@app.get("/recipes/", response_model=List[schemas.MasterRecipe])
def read_recipes(db: Session = Depends(database.get_db)):
    recipes = db.query(models.MasterRecipe).all()
    for r in recipes:
        for i in r.items: i.ingredient_name = i.ingredient.name if i.ingredient else "Unknown"
    return recipes

@app.put("/recipes/{recipe_id}", response_model=schemas.MasterRecipe)
def update_recipe(recipe_id: int, recipe_data: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe: raise HTTPException(status_code=404)
    db_recipe.name = recipe_data.name; db_recipe.description = recipe_data.description
    db_recipe.items = []
    db.flush()
    for item in recipe_data.items:
        db.add(models.MasterRecipeItem(recipe_id=db_recipe.id, ingredient_id=item.ingredient_id, quantity=item.quantity, is_percentage=item.is_percentage))
    db.commit(); db.refresh(db_recipe)
    return db_recipe

@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(database.get_db)):
    # ... (перевірка використання) ...
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    db.delete(db_recipe); db.commit()
    return {"status": "deleted"}

# --- НОВІ ENDPOINTS ДЛЯ ПРОЦЕСІВ ---

@app.post("/processes/groups/", response_model=schemas.ProcessGroup)
def create_process_group(group: schemas.ProcessGroupCreate, db: Session = Depends(database.get_db)):
    new_group = models.ProcessGroup(name=group.name)
    db.add(new_group); db.commit(); db.refresh(new_group)
    
    for opt in group.options:
        db.add(models.ProcessOption(group_id=new_group.id, name=opt.name))
    
    db.commit(); db.refresh(new_group)
    return new_group

@app.get("/processes/groups/", response_model=List[schemas.ProcessGroup])
def read_process_groups(db: Session = Depends(database.get_db)):
    return db.query(models.ProcessGroup).all()

@app.delete("/processes/groups/{id}")
def delete_process_group(id: int, db: Session = Depends(database.get_db)):
    group = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == id).first()
    if not group: raise HTTPException(status_code=404)
    db.delete(group); db.commit()
    return {"status": "deleted"}

@app.post("/processes/options/", response_model=schemas.ProcessOption)
def add_process_option(option: schemas.ProcessOptionCreate, group_id: int, db: Session = Depends(database.get_db)):
    new_opt = models.ProcessOption(group_id=group_id, name=option.name)
    db.add(new_opt); db.commit(); db.refresh(new_opt)
    return new_opt

@app.delete("/processes/options/{id}")
def delete_process_option(id: int, db: Session = Depends(database.get_db)):
    opt = db.query(models.ProcessOption).filter(models.ProcessOption.id == id).first()
    if not opt: raise HTTPException(status_code=404)
    db.delete(opt); db.commit()
    return {"status": "deleted"}

# --- PRODUCTS (ОНОВЛЕНО ДЛЯ ПРОЦЕСІВ) ---
@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    db_product = models.Product(
        name=product.name, price=product.price, description=product.description, 
        category_id=product.category_id, has_variants=product.has_variants,
        master_recipe_id=product.master_recipe_id, output_weight=product.output_weight
    )
    db.add(db_product); db.commit(); db.refresh(db_product)
    
    # Consumables
    for cons in product.consumables:
        db.add(models.ProductConsumable(product_id=db_product.id, consumable_id=cons.consumable_id, quantity=cons.quantity))

    # Variants
    if product.has_variants and product.variants:
        for v in product.variants:
            db_variant = models.ProductVariant(
                product_id=db_product.id, name=v.name, price=v.price, sku=v.sku,
                master_recipe_id=v.master_recipe_id, output_weight=v.output_weight
            )
            db.add(db_variant); db.flush()
            for vc in v.consumables:
                db.add(models.ProductVariantConsumable(variant_id=db_variant.id, consumable_id=vc.consumable_id, quantity=vc.quantity))
    
    # Modifiers
    for group in product.modifier_groups:
        db_group = models.ProductModifierGroup(product_id=db_product.id, name=group.name, is_required=group.is_required)
        db.add(db_group); db.flush()
        for mod in group.modifiers:
            db.add(models.Modifier(group_id=db_group.id, name=mod.name, price_change=mod.price_change, ingredient_id=mod.ingredient_id, quantity=mod.quantity))
            
    # НОВЕ: Прив'язка груп процесів (Many-to-Many)
    if product.process_group_ids:
        for pg_id in product.process_group_ids:
            pg = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == pg_id).first()
            if pg:
                db_product.process_groups.append(pg)

    db.commit(); db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def read_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    # Заповнюємо назви для consumables (як і раніше)
    for p in products:
        for c in p.consumables:
            if c.consumable: c.consumable_name = c.consumable.name
            else: c.consumable_name = "DELETED"
        if p.variants:
            for v in p.variants:
                for vc in v.consumables:
                    if vc.consumable: vc.consumable_name = vc.consumable.name
                    else: vc.consumable_name = "Unknown"
    return products

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_data: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product: raise HTTPException(status_code=404)

    # Base update
    db_product.name = product_data.name
    db_product.description = product_data.description
    db_product.price = product_data.price
    db_product.category_id = product_data.category_id
    db_product.has_variants = product_data.has_variants
    db_product.master_recipe_id = product_data.master_recipe_id
    db_product.output_weight = product_data.output_weight

    # Cleaning old relations
    db_product.variants = []
    db_product.modifier_groups = []
    db_product.consumables = []
    
    # НОВЕ: Очищуємо старі процеси і додаємо нові
    db_product.process_groups = [] 
    if product_data.process_group_ids:
        for pg_id in product_data.process_group_ids:
            pg = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == pg_id).first()
            if pg:
                db_product.process_groups.append(pg)

    db.flush()

    # Consumables
    for cons in product_data.consumables:
        db.add(models.ProductConsumable(product_id=db_product.id, consumable_id=cons.consumable_id, quantity=cons.quantity))

    # Variants
    if product_data.has_variants and product_data.variants:
        for v in product_data.variants:
            db_variant = models.ProductVariant(
                product_id=db_product.id, name=v.name, price=v.price, sku=v.sku,
                master_recipe_id=v.master_recipe_id, output_weight=v.output_weight
            )
            db.add(db_variant); db.flush()
            for vc in v.consumables:
                db.add(models.ProductVariantConsumable(variant_id=db_variant.id, consumable_id=vc.consumable_id, quantity=vc.quantity))
                
    # Modifiers
    for group in product_data.modifier_groups:
        db_group = models.ProductModifierGroup(product_id=db_product.id, name=group.name, is_required=group.is_required)
        db.add(db_group); db.flush()
        for mod in group.modifiers:
            db.add(models.Modifier(group_id=db_group.id, name=mod.name, price_change=mod.price_change, ingredient_id=mod.ingredient_id, quantity=mod.quantity))

    db.commit(); db.refresh(db_product)
    return db_product

# ... (Customers logic remains same) ...
@app.post("/customers/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    new_customer = models.Customer(**customer.dict())
    db.add(new_customer); db.commit(); db.refresh(new_customer)
    return new_customer
# ... (Customer search, update, delete etc) ...
@app.get("/customers/search/", response_model=List[schemas.Customer])
def search_customers(q: str, db: Session = Depends(database.get_db)):
    return db.query(models.Customer).filter(or_(models.Customer.name.ilike(f"%{q}%"), models.Customer.phone.ilike(f"%{q}%"))).limit(10).all()
@app.get("/customers/", response_model=List[schemas.Customer])
def read_customers(skip: int=0, limit: int=50, db: Session = Depends(database.get_db)): return db.query(models.Customer).offset(skip).limit(limit).all()
@app.delete("/customers/{id}")
def delete_customer(id: int, db: Session = Depends(database.get_db)): 
    c = db.query(models.Customer).filter(models.Customer.id==id).first()
    if c: db.delete(c); db.commit()
    return {"status": "deleted"}


# --- CHECKOUT (ОНОВЛЕНО ДЛЯ СПИСАННЯ CONSUMABLES) ---
@app.post("/orders/checkout/")
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    new_order = models.Order(total_price=order_data.total_price, payment_method=order_data.payment_method, customer_id=order_data.customer_id)
    db.add(new_order); db.commit(); db.refresh(new_order)
    
    for item in order_data.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product: continue
        
        item_name = product.name
        price = product.price
        details_list = []
        target_recipe_id = None
        base_weight = 0.0
        
        # --- СПИСАННЯ CONSUMABLES (ТОВАРУ) ---
        # Ці списуються завжди (наприклад, серветка, що йде до будь-якого замовлення цього товару)
        for pc in product.consumables:
            if pc.consumable:
                pc.consumable.stock_quantity -= pc.quantity * item.quantity
                db.add(pc.consumable)

        # Логіка Варіантів
        if item.variant_id:
            variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
            if variant:
                item_name = f"{product.name} ({variant.name})"
                price = variant.price
                details_list.append(f"Варіант: {variant.name}")
                target_recipe_id = variant.master_recipe_id or product.master_recipe_id
                base_weight = variant.output_weight

                # --- СПИСАННЯ CONSUMABLES (ВАРІАНТУ) ---
                # Наприклад, стакан 300мл
                for vc in variant.consumables:
                    if vc.consumable:
                        vc.consumable.stock_quantity -= vc.quantity * item.quantity
                        db.add(vc.consumable)
        else:
            target_recipe_id = product.master_recipe_id
            base_weight = product.output_weight

        # Списання Інгредієнтів (як було раніше)
        if target_recipe_id:
            recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == target_recipe_id).first()
            if recipe:
                for r_item in recipe.items:
                    if r_item.ingredient:
                        deduction = (r_item.quantity / 100.0 * base_weight) if r_item.is_percentage else r_item.quantity
                        r_item.ingredient.stock_quantity -= deduction * item.quantity
                        db.add(r_item.ingredient)

        # Списання Модифікаторів
        for mod_item in item.modifiers:
            mod = db.query(models.Modifier).filter(models.Modifier.id == mod_item.modifier_id).first()
            if mod:
                details_list.append(mod.name)
                if mod.ingredient:
                    mod.ingredient.stock_quantity -= mod.quantity * item.quantity
                    db.add(mod.ingredient)

        db.add(models.OrderItem(
            order_id=new_order.id, product_name=item_name, quantity=item.quantity, 
            price_at_moment=price, details=", ".join(details_list)
        ))
        
    db.commit()
    return {"status": "ok", "order_id": new_order.id}

@app.get("/orders/", response_model=List[schemas.OrderRead])
def get_orders(skip: int=0, limit: int=50, db: Session = Depends(database.get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/customers/{customer_id}/orders/", response_model=List[schemas.OrderRead])
def read_customer_orders(customer_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(models.Order.customer_id == customer_id).order_by(models.Order.created_at.desc()).all()