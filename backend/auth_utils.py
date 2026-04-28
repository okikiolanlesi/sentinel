"""
SentinelAI Authentication Utilities
JWT token handling, password hashing, and API key generation
"""

import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import hmac

from database import get_db, User, AuditLog, UserRole

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-jwt-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


# bcrypt has a hard 72-byte limit — silently truncate to be safe with long passwords.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly (avoids passlib<>bcrypt compat issues)."""
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def generate_api_key() -> str:
    """Generate a unique API key in format: sk-sentinel-{32 random hex chars}"""
    random_part = secrets.token_hex(16)  # 32 hex characters
    return f"sk-sentinel-{random_part}"


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks"""
    # Hash both values and compare the hashes
    hash1 = hashlib.sha256(val1.encode()).digest()
    hash2 = hashlib.sha256(val2.encode()).digest()
    return hmac.compare_digest(hash1, hash2)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def log_audit(db: Session, user_id: str, action: str, resource: str,
              details: str = None, ip_address: str = None):
    """Log an action to the audit log"""
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address
    )
    db.add(audit_entry)
    db.commit()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Raises HTTPException if token is invalid or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*roles: UserRole):
    """
    Dependency factory that requires the user to have one of the specified roles.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            allowed_roles = ", ".join([r.value for r in roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}",
            )
        return current_user
    return role_checker


async def get_current_user_from_api_key(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to authenticate via API key header (X-API-Key).
    Used for external integrations like GTBank/MTN API calls.
    """
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user by API key using indexed lookup, then constant-time verify
    users = db.query(User).filter(User.api_key != None, User.is_active == True).all()
    for u in users:
        if constant_time_compare(api_key, u.api_key):
            return u

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
