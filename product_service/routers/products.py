# FILE: product_service/routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models
from services.product_service import ProductService
from services.inventory_logger import InventoryLogger

router = APIRouter(prefix="/products", tags=["Products"])

# --- СТАНДАРТНІ CRUD ОПЕРАЦІЇ ---

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
    
    # Дозаповнюємо назви для красивого відображення на фронті
    for p in products:
        # Для самого товару
        for c in p.consumables:
            if c.consumable:
                c.consumable_name = c.consumable.name

        # ДЛЯ ВАРІАНТІВ
        if p.variants:
            for v in p.variants:
                for vc in v.consumables:
                    if vc.consumable:
                        vc.consumable_name = vc.consumable.name 
                for vi in v.ingredients:
                    if vi.ingredient:
                        vi.ingredient_name = vi.ingredient.name

    return products

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"status": "deleted"}

# ==========================================
# УПРАВЛІННЯ ЗАЛИШКАМИ ТА ІСТОРІЯ
# ==========================================

# 1. Оновити залишок простого товару (Ручна корекція)
@router.patch("/{product_id}/stock")
def update_product_stock(product_id: int, qty: float, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404)
    
    # Зберігаємо старе значення
    old_qty = product.stock_quantity
    
    # Оновлюємо
    product.stock_quantity = qty
    
    # ПИШЕМО В ЛОГ
    InventoryLogger.log(
        db, 
        entity_type="product", 
        entity_id=product.id, 
        entity_name=product.name, 
        old_balance=old_qty, 
        new_balance=qty, 
        reason="manual_correction"
    )
    
    db.commit()
    return {"status": "updated", "new_quantity": qty}

# 2. Оновити залишок варіанту (Ручна корекція)
@router.patch("/variants/{variant_id}/stock")
def update_variant_stock(variant_id: int, qty: float, db: Session = Depends(database.get_db)):
    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not variant: raise HTTPException(status_code=404)
    
    old_qty = variant.stock_quantity
    variant.stock_quantity = qty
    
    # Формуємо назву для історії: "Кава (XL)"
    p_name = variant.product.name if variant.product else "Unknown"
    full_name = f"{p_name} ({variant.name})"

    # ПИШЕМО В ЛОГ
    InventoryLogger.log(
        db, 
        entity_type="product_variant", 
        entity_id=variant.id, 
        entity_name=full_name, 
        old_balance=old_qty, 
        new_balance=qty, 
        reason="manual_correction"
    )
    
    db.commit()
    return {"status": "updated", "new_quantity": qty}

# 3. Списання при продажі (Це знадобиться для Order Service)
@router.post("/deduct_stock_for_order")
def deduct_stock_for_order(items: List[schemas.StockDeductionItem], db: Session = Depends(database.get_db)):
    for item in items:
        # ВАРІАНТИ
        if item.type == 'product_variant':
            variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.id).first()
            if variant:
                old = variant.stock_quantity
                variant.stock_quantity -= item.quantity
                InventoryLogger.log(
                    db, "product_variant", variant.id, 
                    f"{variant.product.name} ({variant.name})", 
                    old, variant.stock_quantity, 
                    f"sale_order_{item.order_id}"
                )
        # ПРОСТІ ТОВАРИ
        elif item.type == 'product':
            product = db.query(models.Product).filter(models.Product.id == item.id).first()
            if product:
                old = product.stock_quantity
                product.stock_quantity -= item.quantity
                InventoryLogger.log(
                    db, "product", product.id, product.name, 
                    old, product.stock_quantity, 
                    f"sale_order_{item.order_id}"
                )
                
    db.commit()
    return {"status": "deducted"}