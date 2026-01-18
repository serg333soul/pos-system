# FILE: product_service/routers/recipes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models

router = APIRouter(prefix="/recipes", tags=["Recipes"])

@router.post("/", response_model=schemas.MasterRecipe)
def create_recipe(recipe: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    new_recipe = models.MasterRecipe(name=recipe.name, description=recipe.description)
    db.add(new_recipe); db.commit(); db.refresh(new_recipe)
    
    # Додаємо інгредієнти рецепту
    for item in recipe.items:
        db.add(models.MasterRecipeItem(
            recipe_id=new_recipe.id, 
            ingredient_id=item.ingredient_id, 
            quantity=item.quantity, 
            is_percentage=item.is_percentage
        ))
    db.commit(); db.refresh(new_recipe)
    return new_recipe

@router.get("/", response_model=List[schemas.MasterRecipe])
def read_recipes(db: Session = Depends(database.get_db)):
    recipes = db.query(models.MasterRecipe).all()
    # "Ліниве" завантаження імен інгредієнтів для фронтенду
    for r in recipes:
        for i in r.items: 
            i.ingredient_name = i.ingredient.name if i.ingredient else "Unknown"
    return recipes

@router.put("/{recipe_id}", response_model=schemas.MasterRecipe)
def update_recipe(recipe_id: int, recipe_data: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe: raise HTTPException(status_code=404)
    
    db_recipe.name = recipe_data.name
    db_recipe.description = recipe_data.description
    
    # Очищаємо старі інгредієнти і пишемо нові
    # (SQLAlchemy видалить старі записи items завдяки налаштуванням моделі)
    db_recipe.items = [] 
    db.flush()
    
    for item in recipe_data.items:
        db.add(models.MasterRecipeItem(
            recipe_id=db_recipe.id, 
            ingredient_id=item.ingredient_id, 
            quantity=item.quantity, 
            is_percentage=item.is_percentage
        ))
    db.commit(); db.refresh(db_recipe)
    return db_recipe

@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe: raise HTTPException(status_code=404)
    db.delete(db_recipe); db.commit()
    return {"status": "deleted"}