from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[NotificationOut])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()


@router.post('/{notification_id}/read')
def mark_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,
    ).first()
    if notification:
        notification.read = True
        db.commit()
    return {'success': True}


@router.post('/read-all')
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False,
    ).update({'read': True})
    db.commit()
    return {'success': True}


@router.get('/unread-count')
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False,
    ).count()
    return {'count': count}