# FILE: product_service/routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import database, schemas, models

from services.product_service import ProductService
from services.inventory_client import InventoryClient # 🔥 Використовуємо адаптер

router = APIRouter(prefix="/products", tags=["Products"])

# --- КАЛЬКУЛЯТОР СОБІВАРТОСТІ ---
@router.post("/calculate-cost")
def calculate_cost(data: schemas.ProductCostCheck, db: Session = Depends(database.get_db)):
    return {"total_cost": ProductService.calculate_product_cost(db, data)}

@router.get("/{product_id}/variants/{variant_id}/calculated-stock")
def get_variant_calculated_stock(product_id: int, variant_id: int, db: Session = Depends(database.get_db)):
    return {"calculated_stock": ProductService.calculate_max_possible_stock(db, variant_id)}

@router.get("/{product_id}/history", response_model=List[schemas.InventoryTransactionRead])
def get_product_history(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).options(joinedload(models.Product.variants)).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant_ids = [v.id for v in product.variants] if product.variants else []
    
    # 🔥 ДЕЛЕГУЄМО: Товари більше не лізуть в таблиці складу напряму!
    return InventoryClient.get_product_history(db, product_id, variant_ids)

# --- CRUD ОПЕРАЦІЇ (КАТАЛОГ) ---

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
    # 🔥 СТЯГУЄМО ЗАЛИШКИ ЗІ СКЛАДУ ОДИН РАЗ ДЛЯ ВСІХ ТОВАРІВ
    from services.inventory_client import InventoryClient
    ing_stock, con_stock = InventoryClient.get_all_stocks()
    # 🔥 ВИПРАВЛЕНО: Видалені JOIN-и з базами складу!
    products = db.query(models.Product).options(
        joinedload(models.Product.category),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.master_recipe).joinedload(models.MasterRecipe.items),
        joinedload(models.Product.consumables),
        joinedload(models.Product.ingredients)
    ).all()

    for p in products:
        if p.stock_quantity is None: p.stock_quantity = 0.0
        if p.price is None: p.price = 0.0
        if p.output_weight is None: p.output_weight = 0.0

        for c in p.consumables:
            c.consumable_name = f"ID Матеріалу: {c.consumable_id}"
        for i in p.ingredients:
            i.ingredient_name = f"ID Інгредієнта: {i.ingredient_id}"
            
        for v in p.variants:
            if v.stock_quantity is None: v.stock_quantity = 0.0
            if v.price is None: v.price = 0.0
            if v.output_weight is None: v.output_weight = 0.0

            if v.master_recipe:
                for item in v.master_recipe.items:
                    item.ingredient_name = f"ID Інгредієнта: {item.ingredient_id}"

            if v.master_recipe_id and not p.track_stock:
                try:
                    # 🔥 ПЕРЕДАЄМО СЛОВНИКИ В КАЛЬКУЛЯТОР
                    v.stock_quantity = ProductService.calculate_max_possible_stock(db, v.id, ing_stock, con_stock)
                except Exception:
                    v.stock_quantity = 0.0
            
            if v.stock_quantity is None: v.stock_quantity = 0.0

            for vc in v.consumables:
                vc.consumable_name = f"ID Матеріалу: {vc.consumable_id}"
            for vi in v.ingredients:
                vi.ingredient_name = f"ID Інгредієнта: {vi.ingredient_id}"
                    
    return products

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(database.get_db)):
    # 🔥 ВИПРАВЛЕНО: Видалені JOIN-и з базами складу!
    p = db.query(models.Product).options(
        joinedload(models.Product.category),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients),
        joinedload(models.Product.consumables),
        joinedload(models.Product.ingredients)
    ).filter(models.Product.id == product_id).first()

    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for c in p.consumables:
        c.consumable_name = f"ID Матеріалу: {c.consumable_id}"
    for i in p.ingredients:
        i.ingredient_name = f"ID Інгредієнта: {i.ingredient_id}"
        
    for v in p.variants:
        for vc in v.consumables:
            vc.consumable_name = f"ID Матеріалу: {vc.consumable_id}"
        for vi in v.ingredients:
            vi.ingredient_name = f"ID Інгредієнта: {vi.ingredient_id}"
                
    return p

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    success = ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "deleted", "message": f"Product {product_id} and all its components removed"}

@router.post("/{product_id}/stock")
def update_stock(product_id: int, qty: float, db: Session = Depends(database.get_db)):
    from services.inventory_service import InventoryService
    
    request = schemas.InventoryAdjustRequest(
        entity_type="product",
        entity_id=product_id,
        actual_quantity=qty,
        reason="Ручне коригування з картки товару"
    )
    return InventoryService.adjust_inventory(db, request)