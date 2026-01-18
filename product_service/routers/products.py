# FILE: product_service/routers/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models
from services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    # Викликаємо сервіс, який зробить всю брудну роботу
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
    
    # --- UI Helper ---
    # Дозаповнюємо назви витратних матеріалів, щоб на фронті було гарно
    # (SQLAlchemy завантажує ID, а ми дістаємо імена зі зв'язків)
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

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Видалення товару каскадно видалить варіанти та зв'язки (завдяки налаштуванням models.py)
    db.delete(product)
    db.commit()
    return {"status": "deleted"}