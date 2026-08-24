from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Company, User
from app.schemas import CompanyCreate, CompanyOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Company).order_by(Company.created_at.desc()).all()


@router.post('/', response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get('/{company_id}', response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail='Company not found')
    return company


@router.put('/{company_id}', response_model=CompanyOut)
def update_company(company_id: int, payload: CompanyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail='Company not found')
    for key, value in payload.model_dump().items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


@router.delete('/{company_id}')
def delete_company(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail='Company not found')
    db.delete(company)
    db.commit()
    return {'deleted': True}


@router.get('/search/{query}')
def search_companies(query: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    results = db.query(Company).filter(
        Company.name.ilike(f'%{query}%') | Company.domain.ilike(f'%{query}%')
    ).limit(10).all()
    return results