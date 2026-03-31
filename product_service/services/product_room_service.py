# FILE: product_service/services/product_room_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

class ProductRoomService:
    @staticmethod
    def add_product_to_room(db: Session, room_id: int, product_id: int):
        room = db.query(models.ProductRoom).filter(models.ProductRoom.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Кімнату не знайдено")
        
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не знайдено")
        
        if product.has_variants:
            raise HTTPException(status_code=400, detail="У кімнату можна додавати тільки прості товари")

        if product.room_id and product.room_id != room_id:
            raise HTTPException(
                status_code=400, 
                detail=f"Товар вже прикріплений до іншої кімнати (ID: {product.room_id})"
            )

        product.room_id = room_id
        db.commit()
        return {"message": f"Товар '{product.name}' успішно додано до кімнати '{room.name}'"}

    @staticmethod
    def remove_product_from_room(db: Session, room_id: int, product_id: int):
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product or product.room_id != room_id:
            raise HTTPException(status_code=404, detail="Товар не знайдено в цій кімнаті")
        
        product.room_id = None
        db.commit()
        return {"message": f"Товар '{product.name}' видалено з кімнати"}