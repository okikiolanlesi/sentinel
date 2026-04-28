"""
SentinelAI Scan Routes
Message scanning, batch processing, and scan history
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db, User, ScanResult, MessageType, ThreatLevel, ScanAction, AuditLog, UserRole
from auth_utils import get_current_user, require_role, log_audit, get_current_user_from_api_key
from ai.scanner import analyse_message, batch_analyse
from ai.risk_scorer import calculate_contextual_risk, get_threat_level
from ai.kernel import run_fraud_analysis_pipeline

router = APIRouter(prefix="/api/scan", tags=["Scanning"])


# Pydantic models
class ScanRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message content to analyse")
    message_type: str = Field(default="sms", description="Type: sms, whatsapp, or transcript")
    sender: Optional[str] = Field(None, max_length=255, description="Sender identifier (phone/email)")


class ScanResponse(BaseModel):
    id: str
    risk_score: float
    threat_level: str
    flags: list
    action: str
    reasoning: str
    is_scam: bool
    created_at: datetime


class BatchScanRequest(BaseModel):
    messages: List[ScanRequest] = Field(..., max_items=50, description="Max 50 messages per batch")


class BatchScanResponse(BaseModel):
    total_scanned: int
    threats_found: int
    breakdown: dict
    results: List[ScanResponse]


class ScanHistoryResponse(BaseModel):
    items: List[ScanResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.post("/message", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_message(
    request: ScanRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Scan a single message for fraud indicators.

    Requires: analyst or admin role
    Uses Semantic Kernel fraud analysis pipeline
    """
    try:
        # Validate message type
        if request.message_type not in ["sms", "whatsapp", "transcript"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message_type. Must be: sms, whatsapp, or transcript"
            )

        # Run through Semantic Kernel fraud analysis pipeline
        result = await run_fraud_analysis_pipeline(
            content=request.content,
            sender=request.sender,
            message_type=request.message_type,
            db=db
        )

        # Save result to database
        scan_result = ScanResult(
            user_id=current_user.id,
            message_type=MessageType(request.message_type),
            content=request.content,
            sender=request.sender,
            risk_score=result["final_risk_score"],
            threat_level=ThreatLevel(result["final_threat_level"]),
            flags=result["ai_analysis"].get("flags", []),
            action=ScanAction(result["ai_analysis"].get("action", "REVIEW")),
            ai_reasoning=result["ai_analysis"].get("reasoning", ""),
            confirmed=False
        )

        db.add(scan_result)
        db.commit()
        db.refresh(scan_result)

        # Log to audit
        log_audit(
            db=db,
            user_id=current_user.id,
            action="MESSAGE_SCANNED",
            resource="scan_results",
            details=f"Scanned {request.message_type} from {request.sender or 'unknown'}",
        )

        return ScanResponse(
            id=scan_result.id,
            risk_score=scan_result.risk_score,
            threat_level=scan_result.threat_level.value,
            flags=scan_result.flags or [],
            action=scan_result.action.value,
            reasoning=scan_result.ai_reasoning or "",
            is_scam=result["ai_analysis"].get("is_scam", False),
            created_at=scan_result.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchScanResponse)
async def scan_batch(
    request: BatchScanRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Scan multiple messages concurrently.

    Requires: admin role
    Max 50 messages per batch
    """
    try:
        # Prepare messages for batch analysis
        messages = [
            {
                "content": msg.content,
                "message_type": msg.message_type,
                "sender": msg.sender
            }
            for msg in request.messages
        ]

        # Run batch analysis
        results = await batch_analyse(messages)

        # Save all results and build response
        saved_results = []
        breakdown = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAN": 0}
        threats_found = 0

        for i, ai_result in enumerate(results):
            msg = request.messages[i]

            # Apply contextual risk scoring
            risk_context = calculate_contextual_risk(
                base_score=ai_result["risk_score"],
                sender=msg.sender or "",
                db=db
            )

            threat_level = get_threat_level(risk_context["final_score"])

            scan_result = ScanResult(
                user_id=current_user.id,
                message_type=MessageType(msg.message_type),
                content=msg.content,
                sender=msg.sender,
                risk_score=risk_context["final_score"],
                threat_level=ThreatLevel(threat_level),
                flags=ai_result.get("flags", []),
                action=ScanAction(ai_result.get("action", "REVIEW")),
                ai_reasoning=ai_result.get("reasoning", ""),
                confirmed=False
            )

            db.add(scan_result)
            saved_results.append(scan_result)

            # Update breakdown
            breakdown[threat_level] += 1
            if threat_level in ["HIGH", "MEDIUM"]:
                threats_found += 1

        db.commit()

        # Log batch scan
        log_audit(
            db=db,
            user_id=current_user.id,
            action="BATCH_SCAN",
            resource="scan_results",
            details=f"Batch scanned {len(request.messages)} messages, found {threats_found} threats"
        )

        return BatchScanResponse(
            total_scanned=len(request.messages),
            threats_found=threats_found,
            breakdown=breakdown,
            results=[
                ScanResponse(
                    id=r.id,
                    risk_score=r.risk_score,
                    threat_level=r.threat_level.value,
                    flags=r.flags or [],
                    action=r.action.value,
                    reasoning=r.ai_reasoning or "",
                    is_scam=r.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
                    created_at=r.created_at
                )
                for r in saved_results
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch scan failed: {str(e)}"
        )


@router.get("/history", response_model=ScanHistoryResponse)
async def get_scan_history(
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Get paginated scan history for current user's organisation.

    Supports filtering by threat_level, message_type, and date range.
    """
    try:
        # Build query
        query = db.query(ScanResult).filter(ScanResult.user_id == current_user.id)

        # Apply filters
        if threat_level:
            if threat_level.upper() in ["HIGH", "MEDIUM", "LOW", "CLEAN"]:
                query = query.filter(ScanResult.threat_level == ThreatLevel(threat_level.upper()))

        if message_type:
            if message_type.lower() in ["sms", "whatsapp", "transcript"]:
                query = query.filter(ScanResult.message_type == MessageType(message_type.lower()))

        if start_date:
            try:
                start = datetime.fromisoformat(start_date)
                query = query.filter(ScanResult.created_at >= start)
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.fromisoformat(end_date)
                query = query.filter(ScanResult.created_at <= end)
            except ValueError:
                pass

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        items = query.order_by(ScanResult.created_at.desc()).offset(offset).limit(page_size).all()

        return ScanHistoryResponse(
            items=[
                ScanResponse(
                    id=item.id,
                    risk_score=item.risk_score,
                    threat_level=item.threat_level.value,
                    flags=item.flags or [],
                    action=item.action.value,
                    reasoning=item.ai_reasoning or "",
                    is_scam=item.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
                    created_at=item.created_at
                )
                for item in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan history: {str(e)}"
        )


@router.get("/evaluate", summary="Run model evaluation against Nigerian scam dataset")
async def evaluate_model(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Run SentinelAI against the built-in Nigerian scam evaluation dataset.

    Returns accuracy metrics and per-sample predictions vs expected actions.
    Admin only.
    """
    from ai.scanner import evaluate_model_performance
    try:
        results = await evaluate_model_performance()
        return {
            "status": "evaluation_complete",
            "accuracy_percent": results["accuracy"],
            "correct": results["correct"],
            "total": results["total"],
            "results": results["results"],
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation dataset not found. Expected at backend/ai/data/nigerian_scam_dataset.json",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_result(
    scan_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Get a single scan result by ID.
    """
    try:
        scan = db.query(ScanResult).filter(
            ScanResult.id == scan_id,
            ScanResult.user_id == current_user.id
        ).first()

        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan result not found"
            )

        return ScanResponse(
            id=scan.id,
            risk_score=scan.risk_score,
            threat_level=scan.threat_level.value,
            flags=scan.flags or [],
            action=scan.action.value,
            reasoning=scan.ai_reasoning or "",
            is_scam=scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            created_at=scan.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan: {str(e)}"
        )


@router.post("/{scan_id}/confirm", response_model=ScanResponse)
async def confirm_scan(
    scan_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Mark a scan result as a confirmed threat.
    """
    try:
        scan = db.query(ScanResult).filter(
            ScanResult.id == scan_id,
            ScanResult.user_id == current_user.id
        ).first()

        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan result not found"
            )

        scan.confirmed = True
        db.commit()
        db.refresh(scan)

        log_audit(
            db=db,
            user_id=current_user.id,
            action="SCAN_CONFIRMED",
            resource="scan_results",
            details=f"Confirmed threat: {scan_id}"
        )

        return ScanResponse(
            id=scan.id,
            risk_score=scan.risk_score,
            threat_level=scan.threat_level.value,
            flags=scan.flags or [],
            action=scan.action.value,
            reasoning=scan.ai_reasoning or "",
            is_scam=scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            created_at=scan.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm scan: {str(e)}"
        )


@router.post("/api", response_model=dict)
async def scan_via_api_key(
    request: ScanRequest,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """
    External integration endpoint for API key authentication.

    This is the endpoint that GTBank/MTN would call.
    Rate limited to 1000 requests per hour per API key.
    Returns minimal response.
    """
    try:
        # Validate message type
        if request.message_type not in ["sms", "whatsapp", "transcript"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message_type"
            )

        # Run AI analysis
        ai_result = await analyse_message(
            content=request.content,
            message_type=request.message_type,
            sender=request.sender
        )

        # Apply contextual risk scoring
        risk_context = calculate_contextual_risk(
            base_score=ai_result["risk_score"],
            sender=request.sender or "",
            db=db
        )

        threat_level = get_threat_level(risk_context["final_score"])

        # Save result
        scan_result = ScanResult(
            user_id=current_user.id,
            message_type=MessageType(request.message_type),
            content=request.content,
            sender=request.sender,
            risk_score=risk_context["final_score"],
            threat_level=ThreatLevel(threat_level),
            flags=ai_result.get("flags", []),
            action=ScanAction(ai_result.get("action", "REVIEW")),
            ai_reasoning=ai_result.get("reasoning", ""),
            confirmed=False
        )

        db.add(scan_result)
        db.commit()

        # Log scan
        log_audit(
            db=db,
            user_id=current_user.id,
            action="API_SCAN",
            resource="scan_results",
            details=f"API scan from {current_user.organisation or current_user.email}"
        )

        # Return minimal response
        return {
            "risk_score": risk_context["final_score"],
            "threat_level": threat_level,
            "action": ai_result.get("action", "REVIEW"),
            "flags": ai_result.get("flags", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API scan failed: {str(e)}"
        )


# --- Model Evaluation Endpoint ---
# (moved above /{scan_id} earlier so route matching works correctly)

