"""
SentinelAI - Telecom Fraud Detection SaaS
Main FastAPI Application Entry Point

A B2B SaaS platform for detecting scams, fraud, and deepfake voices
in real-time across SMS, WhatsApp, and phone call transcripts.

Built for the TeKnowledge x Microsoft 2026 Agentic AI Hackathon.
"""

import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from database import init_db, get_db, User, UserRole, SessionLocal
from auth_utils import hash_password, generate_api_key
from routes import auth, scan, voice, dashboard, users

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-jwt-secret-key-change-in-production")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Runs on startup and shutdown.
    """
    # Startup
    print("🚀 Starting SentinelAI...")

    # Initialize database
    init_db()
    print("✓ Database initialized")

    # Create default admin user if none exists
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_exists:
            # Create default admin
            admin_user = User(
                email="admin@sentinelai.io",
                hashed_password=hash_password("SentinelAdmin2026!"),
                full_name="System Administrator",
                organisation="SentinelAI",
                role=UserRole.ADMIN,
                is_active=True,
                api_key=generate_api_key()
            )
            db.add(admin_user)
            db.commit()
            print("✓ Default admin user created:")
            print("  Email: admin@sentinelai.io")
            print("  Password: SentinelAdmin2026!")
        else:
            print("✓ Admin user already exists")
    except Exception as e:
        db.rollback()
        print(f"⚠ Warning: Could not create default admin: {e}")
    finally:
        db.close()

    print("✓ SentinelAI ready!")
    print(f"  Environment: {ENVIRONMENT}")
    print(f"  API Docs: http://localhost:8000/docs")

    yield

    # Shutdown
    print("👋 Shutting down SentinelAI...")


# Create FastAPI application
app = FastAPI(
    title="SentinelAI",
    description="""
## SentinelAI - Telecom Fraud Detection SaaS

Enterprise-grade AI platform for detecting scams, fraud, and deepfake voices in real-time.

### Features
- **Message Scanning**: Detect fraud in SMS, WhatsApp, and call transcripts
- **Voice Analysis**: Transcribe and analyze audio for deepfake detection
- **Dashboard**: Real-time threat intelligence and statistics
- **User Management**: Role-based access control for teams
- **API Integration**: External API key authentication for enterprise customers

### Authentication
Most endpoints require JWT authentication. Get a token via `/api/auth/login` and include it in the `Authorization: Bearer <token>` header.

### API Key Authentication
External integrations (GTBank, MTN, etc.) can use API key authentication via the `X-API-Key` header.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware - Allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log and handle unexpected exceptions"""
    # In production, you'd log this to a monitoring service
    print(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )


# Include routers
app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(voice.router)
app.include_router(dashboard.router)
app.include_router(users.router)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "SentinelAI",
        "version": "1.0.0",
        "description": "Telecom Fraud Detection SaaS",
        "docs": "/docs",
        "health": "/health"
    }


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if ENVIRONMENT == "development" else False,
        log_level="info"
    )
