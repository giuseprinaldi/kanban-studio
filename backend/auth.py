import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyCookie

# Security configuration
# In production a real JWT_SECRET must be supplied; we refuse to start without it
# so session tokens can never be signed with a publicly-known key. Local/dev runs
# fall back to a clearly-marked insecure default for zero-config convenience.
APP_ENV = os.getenv("APP_ENV", "development").lower()
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError(
            "JWT_SECRET environment variable must be set when APP_ENV=production."
        )
    SECRET_KEY = "dev-only-insecure-secret-do-not-use-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# We use APIKeyCookie to extract the session token from cookies
cookie_sec = APIKeyCookie(name="session_token", auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(session_token: Optional[str] = Security(cookie_sec)) -> str:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token payload",
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
