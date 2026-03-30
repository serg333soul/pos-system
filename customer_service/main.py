# FILE: customer_service/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel
from typing import Optional
import time
import requests  # Бібліотека для спілкування з іншими мікросервісами

import models
from database import engine, get_db

# DevOps: Захист при старті. Чекаємо, поки БД буде готова
print("⏳ [Customer API] Очікування бази даних...")
while True:
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ [Customer API] База даних готова та таблиці створено!")
        break
    except OperationalError:
        print("⏳ База ще завантажується... Повтор через 2 секунди.")
        time.sleep(2)

app = FastAPI(title="POS Customer API (CRM)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Схеми для валідації вхідних даних
class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None


@app.get("/customers/")
def get_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).all()

@app.get("/customers/search")
@app.get("/customers/search/")
def search_customers(q: str = "", db: Session = Depends(get_db)):
    """
    Пошук клієнтів за ім'ям або телефоном. 
    Використовується на екрані каси (CartDrawer).
    """
    if not q:
        return []
    
    # Використовуємо .ilike для пошуку без урахування регістру
    search_term = f"%{q}%"
    customers = db.query(models.Customer).filter(
        (models.Customer.name.ilike(search_term)) | 
        (models.Customer.phone.ilike(search_term))
    ).all()
    
    return customers

@app.post("/customers/")
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.phone == customer.phone).first()
    if db_customer:
        raise HTTPException(status_code=400, detail="Клієнт з таким номером телефону вже існує")
    
    new_customer = models.Customer(**customer.model_dump())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@app.put("/customers/{customer_id}")
def update_customer(customer_id: int, customer: CustomerUpdate, db: Session = Depends(get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Клієнт не знайдений")
    
    for key, value in customer.model_dump().items():
        setattr(db_customer, key, value)
        
    db.commit()
    db.refresh(db_customer)
    return db_customer

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Клієнт не знайдений")
    
    db.delete(db_customer)
    db.commit()
    return {"status": "success"}

# 🔥 НОВИЙ ЕНДПОІНТ: Мікросервісна взаємодія
@app.get("/customers/{customer_id}/orders/")
def get_customer_orders(customer_id: int, db: Session = Depends(get_db)):
    """
    Отримує історію замовлень шляхом запиту до сусіднього мікросервісу (product_service).
    """
    # 1. Перевіряємо, чи існує клієнт у НАШІЙ базі (customers_db)
    db_customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Клієнт не знайдений")

    # 2. Робимо HTTP запит до мікросервісу замовлень по внутрішній Docker-мережі
    # Звертаємося до pos_product_service на порт 8000
    try:
        # У майбутньому, коли ми винесемо замовлення, URL зміниться, але зараз він такий:
        target_url = f"http://pos_product_service:8000/orders/history/{customer_id}"
        response = requests.get(target_url, timeout=5.0)
        
        if response.status_code == 200:
            return response.json()
        else:
            return [] # Якщо у клієнта ще немає замовлень
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ [Customer API] Помилка зв'язку з product_service: {e}")
        # DevOps патерн "Resilience" (Стійкість): 
        # Якщо сусідній сервіс впав, ми не кладемо свій сервіс, а повертаємо порожній масив.
        return []