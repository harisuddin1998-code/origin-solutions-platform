from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Proposal, User
from app.auth import get_current_user

router = APIRouter()


@router.get('/')
def list_proposals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Proposal).order_by(Proposal.created_at.desc()).all()


@router.post('/')
def create_proposal(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proposal = Proposal(**payload)
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.put('/{proposal_id}')
def update_proposal(proposal_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail='Proposal not found')
    for key, value in payload.items():
        setattr(proposal, key, value)
    db.commit()
    return proposal


@router.get('/{proposal_id}')
def get_proposal(proposal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail='Proposal not found')
    return proposal