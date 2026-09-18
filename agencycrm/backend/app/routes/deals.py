from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Deal, User, Pipeline
from app.schemas import DealCreate, DealOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[DealOut])
def list_deals(
    pipeline_id: Optional[int] = Query(None),
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Deal).order_by(Deal.updated_at.desc())
    if pipeline_id:
        query = query.filter(Deal.pipeline_id == pipeline_id)
    if stage:
        query = query.filter(Deal.stage == stage)
    return query.all()


@router.post('/', response_model=DealOut)
def create_deal(payload: DealCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deal = Deal(**payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get('/{deal_id}', response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail='Deal not found')
    return deal


@router.put('/{deal_id}', response_model=DealOut)
def update_deal(deal_id: int, payload: DealCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail='Deal not found')
    for key, value in payload.model_dump().items():
        setattr(deal, key, value)
    db.commit()
    db.refresh(deal)
    return deal


@router.patch('/{deal_id}/stage')
def update_deal_stage(deal_id: int, stage: str = Query(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail='Deal not found')
    deal.stage = stage
    db.commit()
    return {'id': deal.id, 'stage': deal.stage}


@router.delete('/{deal_id}')
def delete_deal(deal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail='Deal not found')
    db.delete(deal)
    db.commit()
    return {'deleted': True}