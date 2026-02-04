import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# 1. Додаємо кореневу папку сервісу в шлях пошуку модулів,
# щоб можна було імпортувати main, database, models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db
from main import app
# Імпортуємо моделі, щоб SQLAlchemy знала про них при створенні таблиць
import models 

# 2. Налаштування тестової бази даних (SQLite in-memory)
# check_same_thread=False потрібен для SQLite, коли він працює з FastAPI
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Важливо: зберігає дані між запитами в межах одного тесту
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Фікстура, яка створює чисту базу даних для кожного тесту
    і повертає сесію SQLAlchemy.
    """
    # Створюємо всі таблиці, визначені в models.py
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Видаляємо таблиці після тесту, щоб наступний тест був чистим
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """
    Фікстура клієнта FastAPI, яка автоматично підміняє
    залежність get_db на нашу тестову сесію.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    # Підміняємо реальну залежність (PostgreSQL) на тестову (SQLite)
    app.dependency_overrides[get_db] = override_get_db
    
    # Створюємо клієнта для запитів (використовує httpx під капотом)
    with TestClient(app) as c:
        yield c
    
    # Очищаємо підміну після тесту
    app.dependency_overrides.clear()