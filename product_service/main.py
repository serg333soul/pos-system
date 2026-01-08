from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

app = FastAPI()

# Беремо налаштування підключення до БД зі змінних оточення (або дефолтні)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres_db:5432/products_db")

# Невелика пауза, щоб БД встигла запуститися перед стартом коду
time.sleep(3)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Опис таблиці в базі даних
class ProductDB(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Integer)
    status = Column(String, default="active")

# Створюємо таблицю
Base.metadata.create_all(bind=engine)

# Модель для перевірки даних, які прийшли від клієнта
class ProductCreate(BaseModel):
    name: str
    price: int

# Маршрут 1: Створити товар
@app.post("/products/")
def create_product(product: ProductCreate):
    db = SessionLocal()
    new_product = ProductDB(name=product.name, price=product.price)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    db.close()
    return new_product

# Маршрут 2: Показати товари
@app.get("/products/")
def rea_products():
    db = SessionLocal()
    products = db.query(ProductDB).all()
    db.close()
    return products

# Маршрут 3: Оновити товар (PUT)
@app.put("/products/{product_id}")
def update_product(product_id: int, product: ProductCreate):
    db = SessionLocal()
    # Шукаємо товар
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        
    if db_product:
        # Оновлюємо поля
        db_product.name = product.name
        db_product.price = product.price
        db.commit() # Зберігаємо зміни
        db.refresh(db_product)
        db.close()
        return db_product
        
    db.close()
    return {"error": "Product not found"}

# Маршрут 4: Видалити товар (DELETE)
@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    db = SessionLocal()
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        
    if db_product:
        db.delete(db_product)
        db.commit()
        db.close()
        return {"status": "deleted"}
        
    db.close()
    return {"error": "Product not found"}    