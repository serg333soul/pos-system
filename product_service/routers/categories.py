# FILE: product_service/routers/categories.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models

# Створюємо роутер. Всі шляхи тут будуть починатися з /categories (ми це вкажемо в main.py, але тут можна лишити /)
# tags=["Categories"] додає гарний заголовок в документації /docs
router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db)):
    # Перевіряємо на дублікат
    db_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if db_category: 
        raise HTTPException(status_code=400, detail="Category already exists")
    
    # Створюємо нову
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

@router.get("/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return db.query(models.Category).offset(skip).limit(limit).all()