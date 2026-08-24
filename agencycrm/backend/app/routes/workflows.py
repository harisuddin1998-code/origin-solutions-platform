from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Workflow, User
from app.auth import get_current_user

router = APIRouter()


@router.get('/')
def list_workflows(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()


@router.post('/')
def create_workflow(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workflow = Workflow(**payload)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.put('/{workflow_id}')
def update_workflow(workflow_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail='Workflow not found')
    for key, value in payload.items():
        setattr(workflow, key, value)
    db.commit()
    return workflow


@router.delete('/{workflow_id}')
def delete_workflow(workflow_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail='Workflow not found')
    db.delete(workflow)
    db.commit()
    return {'deleted': True}