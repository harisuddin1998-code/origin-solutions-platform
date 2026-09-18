from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Event, User
from app.schemas import EventCreate
from app.auth import get_current_user

router = APIRouter()


@router.get('/')
def list_events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Event).order_by(Event.start_time.desc()).all()


@router.post('/')
def create_event(payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete('/{event_id}')
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')
    db.delete(event)
    db.commit()
    return {'deleted': True}