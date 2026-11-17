from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Request
import os
import uuid

JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_DAYS = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(request: Request, db):
    """Extract user from session_token cookie or Authorization header."""
    # Try cookie first
    session_token = request.cookies.get('session_token')
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header.split(' ')[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if it's a JWT token (email/password auth)
    if session_token.count('.') == 2:  # JWT format
        payload = decode_access_token(session_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = payload.get('sub')
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    else:
        # It's a session token (Google OAuth)
        session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
        if not session_doc:
            raise HTTPException(status_code=401, detail="Session not found")
        
        # Check expiry
        expires_at = session_doc["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        
        user_id = session_doc["user_id"]
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_doc

def generate_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"