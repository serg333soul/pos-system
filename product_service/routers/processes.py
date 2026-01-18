# FILE: product_service/routers/processes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, schemas, models

router = APIRouter(prefix="/processes", tags=["Processes"])

# --- Групи (напр. Помол) ---
@router.post("/groups/", response_model=schemas.ProcessGroup)
def create_process_group(group: schemas.ProcessGroupCreate, db: Session = Depends(database.get_db)):
    new_group = models.ProcessGroup(name=group.name)
    db.add(new_group); db.commit(); db.refresh(new_group)
    
    for opt in group.options:
        db.add(models.ProcessOption(group_id=new_group.id, name=opt.name))
    
    db.commit(); db.refresh(new_group)
    return new_group

@router.get("/groups/", response_model=List[schemas.ProcessGroup])
def read_process_groups(db: Session = Depends(database.get_db)):
    return db.query(models.ProcessGroup).all()

@router.delete("/groups/{id}")
def delete_process_group(id: int, db: Session = Depends(database.get_db)):
    group = db.query(models.ProcessGroup).filter(models.ProcessGroup.id == id).first()
    if not group: raise HTTPException(status_code=404)
    db.delete(group); db.commit()
    return {"status": "deleted"}

# --- Опції (напр. Під турку) ---
@router.post("/options/", response_model=schemas.ProcessOption)
def add_process_option(option: schemas.ProcessOptionCreate, group_id: int, db: Session = Depends(database.get_db)):
    new_opt = models.ProcessOption(group_id=group_id, name=option.name)
    db.add(new_opt); db.commit(); db.refresh(new_opt)
    return new_opt

@router.delete("/options/{id}")
def delete_process_option(id: int, db: Session = Depends(database.get_db)):
    opt = db.query(models.ProcessOption).filter(models.ProcessOption.id == id).first()
    if not opt: raise HTTPException(status_code=404)
    db.delete(opt); db.commit()
    return {"status": "deleted"}