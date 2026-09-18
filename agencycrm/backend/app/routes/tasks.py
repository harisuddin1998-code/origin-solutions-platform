from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task, User
from app.schemas import TaskCreate, TaskOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Task).order_by(Task.created_at.desc()).all()


@router.post('/', response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put('/{task_id}', response_model=TaskOut)
def update_task(task_id: int, payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    for key, value in payload.model_dump().items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.patch('/{task_id}/status')
def update_task_status(task_id: int, status: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    task.status = status
    db.commit()
    return {'id': task.id, 'status': task.status}


@router.delete('/{task_id}')
def delete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    db.delete(task)
    db.commit()
    return {'deleted': True}