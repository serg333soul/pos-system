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
def read_products():
    db = SessionLocal()
    products = db.query(ProductDB).all()
    db.close()
    return products
