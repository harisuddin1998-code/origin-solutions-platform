from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post('/register')
def register(payload: LoginRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    user = User(
        name=payload.email.split('@')[0].replace('.', ' ').title(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role='Sales',
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({'user_id': user.id})
    return LoginResponse(id=user.id, name=user.name, email=user.email, role=user.role, avatar=user.avatar, token=token)


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    token = create_access_token({'user_id': user.id})
    return LoginResponse(id=user.id, name=user.name, email=user.email, role=user.role, avatar=user.avatar, token=token)


@router.get('/me')
def get_me(user: User = Depends(get_current_user)):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role, 'avatar': user.avatar}


@router.get('/users')
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    users = db.query(User).all()
    return [{'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role, 'avatar': u.avatar} for u in users]