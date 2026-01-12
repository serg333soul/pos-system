from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Формуємо посилання: postgresql://user:password@hostname/dbname
# Ці змінні ми прописали в docker-compose.yml ще на початку
USER = os.getenv("POSTGRES_USER", "user")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "products_db")
HOST = "pos_postgres" # Ім'я контейнера з БД

SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}/{DB_NAME}"

# Створюємо двигун (engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Створюємо фабрику сесій (через неї ми будемо робити запити)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовий клас для всіх наших майбутніх таблиць
Base = declarative_base()

# Функція для отримання сесії (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()