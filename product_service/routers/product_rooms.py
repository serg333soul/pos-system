from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database

router = APIRouter(
    prefix="/product_rooms",
    tags=["Product Rooms"]
)

# --- УПРАВЛІННЯ КІМНАТАМИ ---

@router.post("/", response_model=schemas.ProductRoomRead)
def create_room(room: schemas.ProductRoomCreate, db: Session = Depends(database.get_db)):
    # Перевірка на унікальність назви кімнати
    db_room = db.query(models.ProductRoom).filter(models.ProductRoom.name == room.name).first()
    if db_room:
        raise HTTPException(status_code=400, detail="Кімната з такою назвою вже існує")
    
    new_room = models.ProductRoom(**room.dict())
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

@router.get("/", response_model=List[schemas.ProductRoomRead])
def get_rooms(db: Session = Depends(database.get_db)):
    return db.query(models.ProductRoom).all()

@router.get("/{room_id}", response_model=schemas.ProductRoomRead)
def get_room(room_id: int, db: Session = Depends(database.get_db)):
    room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Кімнату не знайдено")
    return room

@router.put("/{room_id}", response_model=schemas.ProductRoomRead)
def update_room(room_id: int, room_update: schemas.ProductRoomCreate, db: Session = Depends(database.get_db)):
    db_room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Кімнату не знайдено")
    
    for key, value in room_update.dict().items():
        setattr(db_room, key, value)
    
    db.commit()
    db.refresh(db_room)
    return db_room

@router.delete("/{room_id}")
def delete_room(room_id: int, db: Session = Depends(database.get_db)):
    db_room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Кімнату не знайдено")
    
    # Перед видаленням кімнати, очищуємо room_id у всіх прикріплених товарів
    db.query(models.Product).filter(models.Product.room_id == room_id).update({"room_id": None})
    
    db.delete(db_room)
    db.commit()
    return {"message": "Кімнату видалено, товари відкріплено"}

# --- УПРАВЛІННЯ ТОВАРАМИ В КІМНАТІ ---

@router.post("/{room_id}/add-product/{product_id}")
def assign_product_to_room(room_id: int, product_id: int, db: Session = Depends(database.get_db)):
    # Перевірка існування кімнати
    room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Кімнату не знайдено")
    
    # Перевірка товару
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    
    # Перевірка: товар має бути простим (без варіантів)
    if product.has_variants:
        raise HTTPException(status_code=400, detail="У кімнату можна додавати тільки прості товари")

    # Перевірка умови (1): товар не може бути в двох кімнатах одночасно
    if product.room_id and product.room_id != room_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Товар вже прикріплений до іншої кімнати (ID: {product.room_id})"
        )

    product.room_id = room_id
    db.commit()
    return {"message": f"Товар '{product.name}' успішно додано до кімнати '{room.name}'"}

@router.delete("/{room_id}/remove-product/{product_id}")
def remove_product_from_room(room_id: int, product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(
        models.Product.id == product_id, 
        models.Product.room_id == room_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Цей товар не знайдено в даній кімнаті")
    
    product.room_id = None
    db.commit()
    return {"message": "Товар відкріплено від кімнати"}