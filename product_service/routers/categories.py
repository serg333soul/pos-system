from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models

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

# !!! НОВЕ: Оновлення категорії !!!
@router.put("/{category_id}", response_model=schemas.Category)
def update_category(category_id: int, category_data: schemas.CategoryCreate, db: Session = Depends(database.get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Оновлюємо поля
    db_category.name = category_data.name
    db_category.slug = category_data.slug
    db_category.color = category_data.color
    
    # Захист від циклічності (категорія не може бути батьком сама собі)
    if category_data.parent_id == category_id:
         raise HTTPException(status_code=400, detail="Category cannot be its own parent")
         
    db_category.parent_id = category_data.parent_id

    db.commit()
    db.refresh(db_category)
    return db_category

# !!! НОВЕ: Видалення категорії !!!
@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(database.get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(db_category)
    db.commit()
    return {"status": "deleted"}