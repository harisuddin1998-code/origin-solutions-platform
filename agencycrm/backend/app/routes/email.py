from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EmailTemplate, EmailSequence, EmailSetting, EmailLog, User
from app.schemas import EmailTemplateCreate, EmailSequenceCreate, EmailSettingCreate
from app.auth import get_current_user

router = APIRouter()


# ===== Templates =====
@router.get('/templates')
def list_templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()


@router.post('/templates')
def create_template(payload: EmailTemplateCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    template = EmailTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete('/templates/{template_id}')
def delete_template(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    db.delete(template)
    db.commit()
    return {'deleted': True}


# ===== Sequences =====
@router.get('/cadences')
def list_sequences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(EmailSequence).order_by(EmailSequence.created_at.desc()).all()


@router.post('/cadences')
def create_sequence(payload: EmailSequenceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sequence = EmailSequence(**payload.model_dump())
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence


@router.put('/cadences/{sequence_id}')
def update_sequence(sequence_id: int, payload: EmailSequenceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sequence = db.query(EmailSequence).filter(EmailSequence.id == sequence_id).first()
    if not sequence:
        raise HTTPException(status_code=404, detail='Sequence not found')
    for key, value in payload.model_dump().items():
        setattr(sequence, key, value)
    db.commit()
    return sequence


@router.delete('/cadences/{sequence_id}')
def delete_sequence(sequence_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sequence = db.query(EmailSequence).filter(EmailSequence.id == sequence_id).first()
    if not sequence:
        raise HTTPException(status_code=404, detail='Sequence not found')
    db.delete(sequence)
    db.commit()
    return {'deleted': True}


# ===== Settings =====
@router.get('/settings')
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    setting = db.query(EmailSetting).filter(EmailSetting.user_id == user.id).first()
    if not setting:
        return {'smtp_host': '', 'smtp_port': 587, 'from_email': '', 'reply_to': '', 'provider': 'SMTP'}
    return setting


@router.post('/settings')
def update_settings(payload: EmailSettingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ['Admin', 'Manager']:
        raise HTTPException(status_code=403, detail='Only managers can update email settings')
    setting = db.query(EmailSetting).filter(EmailSetting.user_id == user.id).first()
    if not setting:
        setting = EmailSetting(user_id=user.id, **payload.model_dump())
        db.add(setting)
    else:
        for key, value in payload.model_dump().items():
            setattr(setting, key, value)
    db.commit()
    db.refresh(setting)
    return setting


# ===== Logs =====
@router.get('/logs')
def list_logs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(50).all()


@router.post('/send')
def send_email(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = EmailLog(
        contact_id=payload.get('contact_id'),
        template_id=payload.get('template_id'),
        subject=payload.get('subject', ''),
        body=payload.get('body', ''),
    )
    db.add(log)
    db.commit()
    return {'success': True, 'id': log.id}