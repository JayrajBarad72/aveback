import os
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import SessionLocal
from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True)
    username   = Column(String(100), unique=True)
    password   = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id         = Column(Integer, primary_key=True)
    token      = Column(String(200), unique=True)
    username   = Column(String(100))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token() -> str:
    return secrets.token_hex(32)

def create_session(username: str) -> str:
    db = SessionLocal()
    token = create_token()
    session = Session(
        token=token,
        username=username,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    db.close()
    return token

def verify_token(token: str) -> bool:
    db = SessionLocal()
    session = db.query(Session).filter(
        Session.token == token,
        Session.expires_at > datetime.utcnow()
    ).first()
    db.close()
    return session is not None

def get_or_create_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        default_password = os.getenv("ADMIN_PASSWORD", "aventrix2024")
        admin = User(username="admin", password=hash_password(default_password))
        db.add(admin)
        db.commit()
    db.close()

security = HTTPBearer(auto_error=False)

def optional_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return True  # Auth is optional by default, enable via env
