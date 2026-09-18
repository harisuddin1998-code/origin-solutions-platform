from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Invoice, Payment, User
from app.auth import get_current_user

router = APIRouter()


@router.get('/')
def list_invoices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).all()


@router.post('/')
def create_invoice(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invoice = Invoice(**payload)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get('/{invoice_id}')
def get_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail='Invoice not found')
    return invoice


@router.post('/{invoice_id}/pay')
def record_payment(invoice_id: int, amount: float, method: str = 'Bank Transfer', db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail='Invoice not found')
    payment = Payment(invoice_id=invoice_id, amount=amount, method=method)
    invoice.status = 'Paid'
    db.add(payment)
    db.commit()
    return payment