from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Contact, User
from app.schemas import ContactCreate, ContactUpdate, ContactOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[ContactOut])
def list_contacts(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Contact).order_by(Contact.created_at.desc())
    if search:
        query = query.filter(
            Contact.name.ilike(f'%{search}%') |
            Contact.company.ilike(f'%{search}%') |
            Contact.email.ilike(f'%{search}%')
        )
    if status:
        query = query.filter(Contact.status == status)
    return query.all()


@router.post('/', response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = Contact(owner_id=user.id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get('/{contact_id}', response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return contact


@router.put('/{contact_id}', response_model=ContactOut)
def update_contact(contact_id: int, payload: ContactUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete('/{contact_id}')
def delete_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    db.delete(contact)
    db.commit()
    return {'deleted': True}


@router.post('/import')
def import_contacts(contacts: List[ContactCreate], db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    created = []
    for c in contacts:
        contact = Contact(owner_id=user.id, **c.model_dump())
        db.add(contact)
        created.append(contact)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


@router.get('/export/csv')
def export_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contacts = db.query(Contact).filter(Contact.owner_id == user.id).all()
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Company', 'Email', 'Phone', 'Website', 'Status', 'Source'])
    for c in contacts:
        writer.writerow([c.name, c.company, c.email, c.phone, c.website, c.status, c.source])
    return output.getvalue()