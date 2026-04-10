# FILE: product_service/routers/recipes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import database, schemas, models

router = APIRouter(prefix="/recipes", tags=["Recipes"])

@router.post("/", response_model=schemas.MasterRecipe)
def create_recipe(recipe: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    new_recipe = models.MasterRecipe(name=recipe.name, description=recipe.description)
    db.add(new_recipe)
    db.flush() 
    
    for item in recipe.items:
        db.add(models.MasterRecipeItem(
            recipe_id=new_recipe.id, 
            ingredient_id=item.ingredient_id, 
            quantity=item.quantity, 
            is_percentage=item.is_percentage
        ))
    
    db.commit()
    db.refresh(new_recipe)
    return new_recipe

@router.get("/", response_model=List[schemas.MasterRecipe])
def read_recipes(db: Session = Depends(database.get_db)):
    # 🔥 ВИПРАВЛЕНО: Прибрали .joinedload(models.MasterRecipeItem.ingredient)
    # Тепер ми завантажуємо лише елементи рецепту (ID інгредієнтів та їх кількість)
    recipes = db.query(models.MasterRecipe).options(
        joinedload(models.MasterRecipe.items)
    ).all()
    
    for recipe in recipes:
        for i in recipe.items:
            # Заглушка: оскільки БД розділені, моноліт знає лише ID, а не назву.
            # Назви тепер має "склеювати" фронтенд.
            i.ingredient_name = f"ID Інгредієнта: {i.ingredient_id}"
            
    return recipes

@router.put("/{recipe_id}", response_model=schemas.MasterRecipe)
def update_recipe(recipe_id: int, recipe_data: schemas.MasterRecipeCreate, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Рецепт не знайдено")
        
    db_recipe.name = recipe_data.name
    db_recipe.description = recipe_data.description
    
    db_recipe.items = [] 
    db.flush() 
    
    for item in recipe_data.items:
        db.add(models.MasterRecipeItem(
            recipe_id=db_recipe.id, 
            ingredient_id=item.ingredient_id, 
            quantity=item.quantity, 
            is_percentage=item.is_percentage
        ))
        
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

@router.get("/{recipe_id}", response_model=schemas.MasterRecipe)
def read_recipe(recipe_id: int, db: Session = Depends(database.get_db)):
    # 🔥 ВИПРАВЛЕНО: Прибрали .joinedload(...) для ingredient
    recipe = db.query(models.MasterRecipe).options(
        joinedload(models.MasterRecipe.items)
    ).filter(models.MasterRecipe.id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(status_code=404, detail="Рецепт не знайдено")
        
    for i in recipe.items:
        # 🔥 ВИПРАВЛЕНО: Змінили логіку отримання назви
        i.ingredient_name = f"ID Інгредієнта: {i.ingredient_id}"
        
    return recipe

@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(database.get_db)):
    db_recipe = db.query(models.MasterRecipe).filter(models.MasterRecipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Рецепт не знайдено")
    db.delete(db_recipe)
    db.commit()
    return {"status": "deleted"}