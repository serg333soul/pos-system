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
    # Ідеальний Eager Loading залишено без змін!
    products = db.query(models.Product).options(
        joinedload(models.Product.category),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients).joinedload(models.ProductVariantIngredient.ingredient),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.master_recipe).joinedload(models.MasterRecipe.items).joinedload(models.MasterRecipeItem.ingredient),
        joinedload(models.Product.consumables).joinedload(models.ProductConsumable.consumable),
        joinedload(models.Product.ingredients).joinedload(models.ProductIngredient.ingredient)
    ).all()

    for p in products:
        if p.stock_quantity is None: p.stock_quantity = 0.0
        if p.price is None: p.price = 0.0
        if p.output_weight is None: p.output_weight = 0.0

        for c in p.consumables:
            if c.consumable: c.consumable_name = c.consumable.name
        for i in p.ingredients:
            if i.ingredient: i.ingredient_name = i.ingredient.name
            
        for v in p.variants:
            if v.stock_quantity is None: v.stock_quantity = 0.0
            if v.price is None: v.price = 0.0
            if v.output_weight is None: v.output_weight = 0.0

            if v.master_recipe:
                for item in v.master_recipe.items:
                    if item.ingredient: item.ingredient_name = item.ingredient.name

            if v.master_recipe_id and not p.track_stock:
                try:
                    v.stock_quantity = ProductService.calculate_max_possible_stock(db, v.id)
                except Exception:
                    v.stock_quantity = 0.0
            
            if v.stock_quantity is None: v.stock_quantity = 0.0

            for vc in v.consumables:
                if vc.consumable: vc.consumable_name = vc.consumable.name
            for vi in v.ingredients:
                if vi.ingredient: vi.ingredient_name = vi.ingredient.name
                    
    return products

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(database.get_db)):
    p = db.query(models.Product).options(
        joinedload(models.Product.category),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.consumables).joinedload(models.ProductVariantConsumable.consumable),
        joinedload(models.Product.variants).joinedload(models.ProductVariant.ingredients).joinedload(models.ProductVariantIngredient.ingredient),
        joinedload(models.Product.consumables).joinedload(models.ProductConsumable.consumable),
        joinedload(models.Product.ingredients).joinedload(models.ProductIngredient.ingredient)
    ).filter(models.Product.id == product_id).first()

    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for c in p.consumables:
        if c.consumable: c.consumable_name = c.consumable.name
    for i in p.ingredients:
        if i.ingredient: i.ingredient_name = i.ingredient.name
        
    for v in p.variants:
        for vc in v.consumables:
            if vc.consumable: vc.consumable_name = vc.consumable.name
        for vi in v.ingredients:
            if vi.ingredient: vi.ingredient_name = vi.ingredient.name
                
    return p

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    success = ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "deleted", "message": f"Product {product_id} and all its components removed"}

@router.post("/{product_id}/stock")
def update_stock(product_id: int, qty: float, db: Session = Depends(database.get_db)):
    # 🔥 ВИПРАВЛЕНО: Замість ручного оновлення бази товарів, ми викликаємо
    # сервіс коригування залишків (Adjustments), який правильно рахує FIFO!
    from services.inventory_service import InventoryService
    
    request = schemas.InventoryAdjustRequest(
        entity_type="product",
        entity_id=product_id,
        actual_quantity=qty,
        reason="Ручне коригування з картки товару"
    )
    return InventoryService.adjust_inventory(db, request)

# ✂️ МАРШРУТ deduct_stock_for_order ПОВНІСТЮ ВИДАЛЕНО!
# (Його логіка вже ідеально працює в OrderService -> InventoryClient.process_order_items)