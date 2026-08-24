from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Contact, Deal, Task, User, Notification
from app.auth import get_current_user

router = APIRouter()


@router.get('/summary')
def get_dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_contacts = db.query(Contact).count()
    total_deals = db.query(Deal).count()
    pipeline_value = db.query(func.sum(Deal.amount)).filter(
        Deal.stage.notin_(['Closed Won', 'Closed Lost'])
    ).scalar() or 0
    won_value = db.query(func.sum(Deal.amount)).filter(
        Deal.stage == 'Closed Won'
    ).scalar() or 0

    recent_deals = db.query(Deal).order_by(Deal.created_at.desc()).limit(5).all()
    upcoming_tasks = db.query(Task).filter(
        Task.assigned_to == user.id,
        Task.status != 'Completed',
    ).order_by(Task.due_date.asc()).limit(5).all()
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False,
    ).count()

    return {
        'contact_count': total_contacts,
        'deal_count': total_deals,
        'pipeline_value': pipeline_value,
        'won_value': won_value,
        'agency_name': 'Agency CRM',
        'recent_activity': [
            {'title': f'{d.name} - ${d.amount:,.0f}', 'type': 'deal'}
            for d in recent_deals
        ],
        'upcoming_tasks': [
            {'title': t.title, 'due_date': str(t.due_date) if t.due_date else ''}
            for t in upcoming_tasks
        ],
        'unread_notifications': unread_notifications,
    }