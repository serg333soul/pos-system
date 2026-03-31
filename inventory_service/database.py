# FILE: customer_service/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 🔥 Читаємо готову адресу з docker-compose.yml
# Якщо її немає, підключаємося до локальної бази (для тестів)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/customers_db"
)

# Створюємо двигун (engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Створюємо фабрику сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовий клас для моделей
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()