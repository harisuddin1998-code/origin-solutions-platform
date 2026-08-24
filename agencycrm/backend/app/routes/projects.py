from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, ProjectMember, Milestone, User
from app.schemas import ProjectCreate, ProjectOut
from app.auth import get_current_user

router = APIRouter()


@router.get('/', response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post('/', response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get('/{project_id}', response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


@router.put('/{project_id}', response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete('/{project_id}')
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    db.delete(project)
    db.commit()
    return {'deleted': True}


@router.get('/{project_id}/members')
def list_members(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post('/{project_id}/members')
def add_member(project_id: int, user_id: int, role: str = 'Member', db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    return member


@router.get('/{project_id}/milestones')
def list_milestones(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Milestone).filter(Milestone.project_id == project_id).all()


@router.post('/{project_id}/milestones')
def create_milestone(project_id: int, name: str, due_date: str = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    milestone = Milestone(project_id=project_id, name=name, due_date=due_date)
    db.add(milestone)
    db.commit()
    return milestone