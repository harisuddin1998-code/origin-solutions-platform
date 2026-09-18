from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Quotation, User
from app.auth import get_current_user

router = APIRouter()


@router.get('/')
def list_quotations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Quotation).order_by(Quotation.created_at.desc()).all()


@router.post('/')
def create_quotation(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quotation = Quotation(**payload)
    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    return quotation


@router.get('/{quotation_id}')
def get_quotation(quotation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail='Quotation not found')
    return quotation