# FILE: product_service/routers/inventory.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import database, schemas, models

router = APIRouter(tags=["Inventory"])

# --- UNITS (Одиниці виміру) ---
@router.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Unit).filter(or_(models.Unit.name == unit.name, models.Unit.symbol == unit.symbol)).first()
    if exists: raise HTTPException(status_code=400, detail="Одиниця існує")
    db_unit = models.Unit(name=unit.name, symbol=unit.symbol)
    db.add(db_unit); db.commit(); db.refresh(db_unit)
    return db_unit

@router.get("/units/", response_model=List[schemas.Unit])
def read_units(db: Session = Depends(database.get_db)):
    return db.query(models.Unit).all()

# --- INGREDIENTS (Сировина) ---
@router.post("/ingredients/", response_model=schemas.Ingredient)
def create_ingredient(ingredient: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Ingredient).filter(models.Ingredient.name == ingredient.name).first()
    if exists: raise HTTPException(status_code=400, detail="Ingredient already exists")
    new_item = models.Ingredient(**ingredient.dict())
    db.add(new_item); db.commit(); db.refresh(new_item)
    return new_item

@router.get("/ingredients/", response_model=List[schemas.Ingredient])
def read_ingredients(db: Session = Depends(database.get_db)):
    return db.query(models.Ingredient).all()

@router.put("/ingredients/{ingredient_id}", response_model=schemas.Ingredient)
def update_ingredient(ingredient_id: int, ingredient_data: schemas.IngredientCreate, db: Session = Depends(database.get_db)):
    db_ingredient = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ingredient: raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Оновлюємо поля
    db_ingredient.name = ingredient_data.name
    db_ingredient.unit_id = ingredient_data.unit_id
    db_ingredient.cost_per_unit = ingredient_data.cost_per_unit
    # stock_quantity зазвичай не оновлюють через PUT, але поки лишимо
    
    db.commit(); db.refresh(db_ingredient)
    return db_ingredient

@router.delete("/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: int, db: Session = Depends(database.get_db)):
    db_ingredient = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not db_ingredient: raise HTTPException(status_code=404)
    try: 
        db.delete(db_ingredient); db.commit()
    except: 
        db.rollback(); raise HTTPException(status_code=400, detail="Використовується в рецептах")
    return {"status": "deleted"}

# --- CONSUMABLES (Витратні матеріали) ---
@router.post("/consumables/", response_model=schemas.Consumable)
def create_consumable(item: schemas.ConsumableCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.Consumable).filter(models.Consumable.name == item.name).first()
    if exists: raise HTTPException(status_code=400, detail="Вже існує")
    new_c = models.Consumable(**item.dict())
    db.add(new_c); db.commit(); db.refresh(new_c)
    return new_c

@router.get("/consumables/", response_model=List[schemas.Consumable])
def read_consumables(db: Session = Depends(database.get_db)):
    return db.query(models.Consumable).all()

@router.put("/consumables/{id}", response_model=schemas.Consumable)
def update_consumable(id: int, item: schemas.ConsumableCreate, db: Session = Depends(database.get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: raise HTTPException(status_code=404)
    for k, v in item.dict().items(): setattr(db_c, k, v)
    db.commit(); db.refresh(db_c)
    return db_c

@router.delete("/consumables/{id}")
def delete_consumable(id: int, db: Session = Depends(database.get_db)):
    db_c = db.query(models.Consumable).filter(models.Consumable.id == id).first()
    if not db_c: raise HTTPException(status_code=404)
    db.delete(db_c); db.commit()
    return {"status": "deleted"}