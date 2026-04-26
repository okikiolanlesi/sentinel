"""
SentinelAI Database Configuration and Models
SQLite database with SQLAlchemy ORM for telecom fraud detection SaaS
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.sqlite import CHAR
import enum

# Database setup
DATABASE_URL = "sqlite:///./sentinelai.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Enums
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class MessageType(str, enum.Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TRANSCRIPT = "transcript"


class ThreatLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    CLEAN = "CLEAN"


class ScanAction(str, enum.Enum):
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"
    ALLOW = "ALLOW"


# Models
class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    organisation = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    scan_results = relationship("ScanResult", back_populates="user", cascade="all, delete-orphan")
    voice_analyses = relationship("VoiceAnalysis", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_api_key", "api_key"),
    )


class ScanResult(Base):
    """Scan results for SMS, WhatsApp, and transcript analysis"""
    __tablename__ = "scan_results"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    message_type = Column(SQLEnum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    sender = Column(String(255), nullable=True, index=True)
    risk_score = Column(Float, nullable=False)
    threat_level = Column(SQLEnum(ThreatLevel), nullable=False)
    flags = Column(JSON, nullable=True)
    action = Column(SQLEnum(ScanAction), nullable=False)
    ai_reasoning = Column(Text, nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="scan_results")

    __table_args__ = (
        Index("idx_scan_threat_level", "threat_level"),
        Index("idx_scan_created_at", "created_at"),
        Index("idx_scan_sender", "sender"),
    )


class VoiceAnalysis(Base):
    """Voice analysis results for deepfake and fraud detection"""
    __tablename__ = "voice_analyses"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    transcript = Column(Text, nullable=False)
    deepfake_probability = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    threat_level = Column(SQLEnum(ThreatLevel), nullable=False)
    flags = Column(JSON, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="voice_analyses")

    __table_args__ = (
        Index("idx_voice_threat_level", "threat_level"),
        Index("idx_voice_created_at", "created_at"),
    )


class AuditLog(Base):
    """Audit log for tracking all system actions"""
    __tablename__ = "audit_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_action", "action"),
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_user", "user_id"),
    )


def get_db():
    """Dependency for database session management"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
