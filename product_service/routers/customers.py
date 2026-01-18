# FILE: product_service/routers/customers.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import database, schemas, models

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post("/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    # Можна додати перевірку на унікальність телефону
    new_customer = models.Customer(**customer.dict())
    db.add(new_customer); db.commit(); db.refresh(new_customer)
    return new_customer

@router.get("/search/", response_model=List[schemas.Customer])
def search_customers(q: str, db: Session = Depends(database.get_db)):
    # Пошук за ім'ям АБО телефоном (ilike - регістронезалежний)
    return db.query(models.Customer).filter(
        or_(models.Customer.name.ilike(f"%{q}%"), models.Customer.phone.ilike(f"%{q}%"))
    ).limit(10).all()

@router.get("/", response_model=List[schemas.Customer])
def read_customers(skip: int=0, limit: int=50, db: Session = Depends(database.get_db)):
    return db.query(models.Customer).offset(skip).limit(limit).all()

@router.put("/{id}", response_model=schemas.Customer)
def update_customer(id: int, data: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    c = db.query(models.Customer).filter(models.Customer.id == id).first()
    if not c: raise HTTPException(status_code=404)
    c.name = data.name
    c.phone = data.phone
    c.email = data.email
    c.notes = data.notes
    db.commit(); db.refresh(c)
    return c

@router.delete("/{id}")
def delete_customer(id: int, db: Session = Depends(database.get_db)): 
    c = db.query(models.Customer).filter(models.Customer.id==id).first()
    if c: db.delete(c); db.commit()
    return {"status": "deleted"}

@router.get("/{customer_id}/orders/", response_model=List[schemas.OrderRead])
def read_customer_orders(customer_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(models.Order.customer_id == customer_id).order_by(models.Order.created_at.desc()).all()