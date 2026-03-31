# FILE: product_service/routers/product_rooms.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database

# 🔥 Імпортуємо наш новий сервіс
from services.product_room_service import ProductRoomService

router = APIRouter(
    prefix="/product_rooms",
    tags=["Product Rooms"]
)

# --- УПРАВЛІННЯ КІМНАТАМИ (CRUD залишаємо в роутері, бо тут немає бізнес-логіки) ---

@router.post("/", response_model=schemas.ProductRoomRead)
def create_room(room: schemas.ProductRoomCreate, db: Session = Depends(database.get_db)):
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
    if not room: raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.delete("/{room_id}")
def delete_room(room_id: int, db: Session = Depends(database.get_db)):
    room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Кімнату не знайдено")
    
    # Відв'язуємо товари перед видаленням
    db.query(models.Product).filter(models.Product.room_id == room_id).update({"room_id": None})
    db.delete(room)
    db.commit()
    return {"message": "Кімнату успішно видалено"}

# --- ДОДАВАННЯ/ВИДАЛЕННЯ ТОВАРІВ (Делегуємо сервісу!) ---

@router.post("/{room_id}/add-product/{product_id}")
def add_product_to_room(room_id: int, product_id: int, db: Session = Depends(database.get_db)):
    # 🔥 Роутер став чистим!
    return ProductRoomService.add_product_to_room(db, room_id, product_id)

@router.delete("/{room_id}/remove-product/{product_id}")
def remove_product_from_room(room_id: int, product_id: int, db: Session = Depends(database.get_db)):
    # 🔥 Роутер став чистим!
    return ProductRoomService.remove_product_from_room(db, room_id, product_id)