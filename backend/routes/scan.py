"""
SentinelAI Scan Routes
Message scanning, batch processing, and scan history

v2 fix: ScanResponse now includes content, sender, message_type, source,
        calibration_log so history shows the full message + AI reasoning.
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


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="sms", description="sms | whatsapp | transcript")
    sender: Optional[str] = Field(None, max_length=255)


class ScanResponse(BaseModel):
    id: str
    # ── Original message fields (NEW — so history shows the full message) ──
    content: str
    sender: Optional[str]
    message_type: str
    # ── AI verdict fields ──
    risk_score: float
    threat_level: str
    flags: list
    action: str
    reasoning: str          # AI's plain-English explanation
    is_scam: bool
    source: str             # "rule_engine" | "gpt+calibration" | "fallback"
    calibration_log: list   # Any overrides the calibrator applied
    created_at: datetime


class BatchScanRequest(BaseModel):
    messages: List[ScanRequest] = Field(..., max_items=50)


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


def _build_scan_response(scan: ScanResult, is_scam: bool = None, source: str = "gpt+calibration", calibration_log: list = None) -> ScanResponse:
    """Build a ScanResponse from a ScanResult DB row, including message content."""
    if is_scam is None:
        is_scam = scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM]
    return ScanResponse(
        id=scan.id,
        content=scan.content or "",
        sender=scan.sender,
        message_type=scan.message_type.value if scan.message_type else "sms",
        risk_score=scan.risk_score,
        threat_level=scan.threat_level.value,
        flags=scan.flags or [],
        action=scan.action.value,
        reasoning=scan.ai_reasoning or "",
        is_scam=is_scam,
        source=source,
        calibration_log=calibration_log or [],
        created_at=scan.created_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SCAN A SINGLE MESSAGE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/message", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_message(
    request: ScanRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """Scan a single message through the full 5-layer fraud analysis pipeline."""
    try:
        if request.message_type not in ["sms", "whatsapp", "transcript"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message_type. Must be: sms, whatsapp, or transcript"
            )

        result = await run_fraud_analysis_pipeline(
            content=request.content,
            sender=request.sender,
            message_type=request.message_type,
            db=db
        )

        ai = result["ai_analysis"]

        scan_result = ScanResult(
            user_id=current_user.id,
            message_type=MessageType(request.message_type),
            content=request.content,
            sender=request.sender,
            risk_score=result["final_risk_score"],
            threat_level=ThreatLevel(result["final_threat_level"]),
            flags=ai.get("flags", []),
            action=ScanAction(ai.get("action", "REVIEW")),
            ai_reasoning=ai.get("reasoning", ""),
            confirmed=False,
        )

        db.add(scan_result)
        db.commit()
        db.refresh(scan_result)

        log_audit(
            db=db, user_id=current_user.id, action="MESSAGE_SCANNED",
            resource="scan_results",
            details=f"Scanned {request.message_type} from {request.sender or 'unknown'}",
        )

        return ScanResponse(
            id=scan_result.id,
            content=request.content,
            sender=request.sender,
            message_type=request.message_type,
            risk_score=scan_result.risk_score,
            threat_level=scan_result.threat_level.value,
            flags=scan_result.flags or [],
            action=scan_result.action.value,
            reasoning=scan_result.ai_reasoning or "",
            is_scam=ai.get("is_scam", False),
            source=ai.get("source", "gpt+calibration"),
            calibration_log=ai.get("calibration_log", []),
            created_at=scan_result.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# BATCH SCAN
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/batch", response_model=BatchScanResponse)
async def scan_batch(
    request: BatchScanRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Scan up to 50 messages concurrently."""
    try:
        messages = [
            {"content": m.content, "message_type": m.message_type, "sender": m.sender}
            for m in request.messages
        ]
        results = await batch_analyse(messages)

        saved = []
        breakdown = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAN": 0}
        threats_found = 0

        for i, ai_result in enumerate(results):
            msg = request.messages[i]
            risk_context = calculate_contextual_risk(
                base_score=ai_result["risk_score"],
                sender=msg.sender or "",
                db=db,
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
                confirmed=False,
            )
            db.add(scan_result)
            saved.append((scan_result, ai_result))
            breakdown[threat_level] += 1
            if threat_level in ["HIGH", "MEDIUM"]:
                threats_found += 1

        db.commit()

        log_audit(
            db=db, user_id=current_user.id, action="BATCH_SCAN",
            resource="scan_results",
            details=f"Batch: {len(request.messages)} messages, {threats_found} threats",
        )

        return BatchScanResponse(
            total_scanned=len(request.messages),
            threats_found=threats_found,
            breakdown=breakdown,
            results=[
                ScanResponse(
                    id=r.id,
                    content=r.content or "",
                    sender=r.sender,
                    message_type=r.message_type.value,
                    risk_score=r.risk_score,
                    threat_level=r.threat_level.value,
                    flags=r.flags or [],
                    action=r.action.value,
                    reasoning=r.ai_reasoning or "",
                    is_scam=r.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
                    source=ai.get("source", "gpt+calibration"),
                    calibration_log=ai.get("calibration_log", []),
                    created_at=r.created_at,
                )
                for r, ai in saved
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch scan failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# SCAN HISTORY — now returns full message + AI reasoning
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=ScanHistoryResponse)
async def get_scan_history(
    threat_level: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Get paginated scan history.
    Each item includes: original message content, sender, AI reasoning,
    risk score, flags, action, and any calibration overrides.
    """
    try:
        query = db.query(ScanResult).filter(ScanResult.user_id == current_user.id)

        if threat_level and threat_level.upper() in ["HIGH", "MEDIUM", "LOW", "CLEAN"]:
            query = query.filter(ScanResult.threat_level == ThreatLevel(threat_level.upper()))

        if message_type and message_type.lower() in ["sms", "whatsapp", "transcript"]:
            query = query.filter(ScanResult.message_type == MessageType(message_type.lower()))

        if start_date:
            try:
                query = query.filter(ScanResult.created_at >= datetime.fromisoformat(start_date))
            except ValueError:
                pass

        if end_date:
            try:
                query = query.filter(ScanResult.created_at <= datetime.fromisoformat(end_date))
            except ValueError:
                pass

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(ScanResult.created_at.desc()).offset(offset).limit(page_size).all()

        return ScanHistoryResponse(
            items=[
                ScanResponse(
                    id=item.id,
                    content=item.content or "",
                    sender=item.sender,
                    message_type=item.message_type.value if item.message_type else "sms",
                    risk_score=item.risk_score,
                    threat_level=item.threat_level.value,
                    flags=item.flags or [],
                    action=item.action.value,
                    reasoning=item.ai_reasoning or "",
                    is_scam=item.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
                    source="gpt+calibration",
                    calibration_log=[],
                    created_at=item.created_at,
                )
                for item in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GET SINGLE SCAN
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/evaluate", summary="Run model evaluation")
async def evaluate_model(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    from ai.scanner import evaluate_model_performance
    try:
        results = await evaluate_model_performance()
        return {
            "status": "evaluation_complete",
            "accuracy_percent": results["accuracy"],
            "precision_percent": results.get("precision"),
            "recall_percent": results.get("recall"),
            "f1_percent": results.get("f1"),
            "correct": results["correct"],
            "total": results["total"],
            "confusion": results.get("confusion"),
            "results": results["results"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_result(
    scan_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """Get a single scan result by ID — includes full message and AI reasoning."""
    try:
        scan = db.query(ScanResult).filter(
            ScanResult.id == scan_id,
            ScanResult.user_id == current_user.id
        ).first()

        if not scan:
            raise HTTPException(status_code=404, detail="Scan result not found")

        return ScanResponse(
            id=scan.id,
            content=scan.content or "",
            sender=scan.sender,
            message_type=scan.message_type.value if scan.message_type else "sms",
            risk_score=scan.risk_score,
            threat_level=scan.threat_level.value,
            flags=scan.flags or [],
            action=scan.action.value,
            reasoning=scan.ai_reasoning or "",
            is_scam=scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            source="gpt+calibration",
            calibration_log=[],
            created_at=scan.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scan: {str(e)}")


@router.post("/{scan_id}/confirm", response_model=ScanResponse)
async def confirm_scan(
    scan_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """Mark a scan result as a confirmed threat."""
    try:
        scan = db.query(ScanResult).filter(
            ScanResult.id == scan_id,
            ScanResult.user_id == current_user.id
        ).first()

        if not scan:
            raise HTTPException(status_code=404, detail="Scan result not found")

        scan.confirmed = True
        db.commit()
        db.refresh(scan)

        log_audit(db=db, user_id=current_user.id, action="SCAN_CONFIRMED",
                  resource="scan_results", details=f"Confirmed: {scan_id}")

        return ScanResponse(
            id=scan.id,
            content=scan.content or "",
            sender=scan.sender,
            message_type=scan.message_type.value if scan.message_type else "sms",
            risk_score=scan.risk_score,
            threat_level=scan.threat_level.value,
            flags=scan.flags or [],
            action=scan.action.value,
            reasoning=scan.ai_reasoning or "",
            is_scam=scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            source="gpt+calibration",
            calibration_log=[],
            created_at=scan.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to confirm scan: {str(e)}")


@router.post("/api", response_model=dict)
async def scan_via_api_key(
    request: ScanRequest,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """External API key endpoint for enterprise integrations (GTBank, MTN, etc.)."""
    try:
        if request.message_type not in ["sms", "whatsapp", "transcript"]:
            raise HTTPException(status_code=400, detail="Invalid message_type")

        ai_result = await analyse_message(
            content=request.content,
            message_type=request.message_type,
            sender=request.sender,
        )

        risk_context = calculate_contextual_risk(
            base_score=ai_result["risk_score"],
            sender=request.sender or "",
            db=db,
        )
        threat_level = get_threat_level(risk_context["final_score"])

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
            confirmed=False,
        )
        db.add(scan_result)
        db.commit()

        log_audit(db=db, user_id=current_user.id, action="API_SCAN",
                  resource="scan_results",
                  details=f"API scan from {current_user.organisation or current_user.email}")

        return {
            "risk_score": risk_context["final_score"],
            "threat_level": threat_level,
            "action": ai_result.get("action", "REVIEW"),
            "flags": ai_result.get("flags", []),
            "reasoning": ai_result.get("reasoning", ""),
            "source": ai_result.get("source", "gpt+calibration"),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"API scan failed: {str(e)}")
