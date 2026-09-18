from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Pipeline, Deal, User
from app.schemas import PipelineCreate, PipelineOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[PipelineOut])
def list_pipelines(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Pipeline).order_by(Pipeline.created_at.desc()).all()


@router.post('/', response_model=PipelineOut)
def create_pipeline(payload: PipelineCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pipeline = Pipeline(name=payload.name, stages=payload.stages)
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.get('/{pipeline_id}', response_model=PipelineOut)
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail='Pipeline not found')
    return pipeline


@router.put('/{pipeline_id}', response_model=PipelineOut)
def update_pipeline(pipeline_id: int, payload: PipelineCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail='Pipeline not found')
    pipeline.name = payload.name
    pipeline.stages = payload.stages
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.delete('/{pipeline_id}')
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail='Pipeline not found')
    db.delete(pipeline)
    db.commit()
    return {'deleted': True}