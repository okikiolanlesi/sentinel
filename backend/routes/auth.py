"""
SentinelAI Authentication Routes
User registration, login, and token management
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from database import get_db, User, AuditLog, UserRole
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_api_key,
    get_current_user,
    log_audit,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


# Pydantic models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[str] = None
    organisation: Optional[str] = None


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    organisation: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - Creates user with hashed password
    - Generates unique API key
    - Returns JWT token
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_pw = hash_password(request.password)
        api_key = generate_api_key()

        new_user = User(
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            organisation=request.organisation,
            role=UserRole.VIEWER,  # Default role
            is_active=True,
            api_key=api_key
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create JWT token
        access_token = create_access_token(
            data={"sub": new_user.id},
            expires_delta=None
        )

        # Log registration
        log_audit(
            db=db,
            user_id=new_user.id,
            action="USER_REGISTERED",
            resource="users",
            details=f"New user registered: {new_user.email}"
        )

        return RegisterResponse(
            access_token=access_token,
            user={
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "organisation": new_user.organisation,
                "role": new_user.role.value,
                "is_active": new_user.is_active
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    - Verifies email and password
    - Updates last_login timestamp
    - Logs attempt to audit log
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()

        if not user or not verify_password(request.password, user.hashed_password):
            # Log failed attempt
            log_audit(
                db=db,
                user_id="unknown",
                action="LOGIN_FAILED",
                resource="auth",
                details=f"Failed login attempt for email: {request.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact administrator."
            )

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=None
        )

        # Log successful login
        log_audit(
            db=db,
            user_id=user.id,
            action="LOGIN_SUCCESS",
            resource="auth",
            details=f"User logged in: {user.email}"
        )

        return LoginResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "organisation": user.organisation,
                "role": user.role.value,
                "is_active": user.is_active,
                "last_login": user.last_login
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.
    Requires valid JWT token.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        organisation=current_user.organisation,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/generate-key", response_model=dict)
async def generate_new_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for the current user.
    Invalidates the previous API key.
    """
    try:
        new_api_key = generate_api_key()
        current_user.api_key = new_api_key
        db.commit()

        log_audit(
            db=db,
            user_id=current_user.id,
            action="API_KEY_GENERATED",
            resource="api_keys",
            details="New API key generated"
        )

        return {
            "message": "API key regenerated successfully",
            "api_key": new_api_key,
            "warning": "Store this key securely. It will not be shown again."
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate API key: {str(e)}"
        )
