"""
SentinelAI Dashboard Routes
Statistics, threat feed, trends, and audit log
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel

from database import get_db, User, ScanResult, VoiceAnalysis, AuditLog, ThreatLevel, UserRole
from auth_utils import get_current_user, require_role, log_audit
from ai.risk_scorer import get_risk_summary, detect_campaign

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# Pydantic models
class DashboardStats(BaseModel):
    total_scanned: int
    threats_detected: int
    deepfakes_found: int
    avg_risk_score: float
    blocked_today: int
    active_campaigns: int
    breakdown: dict


class ThreatFeedItem(BaseModel):
    id: str
    content_preview: str
    risk_score: float
    threat_level: str
    message_type: str
    sender: Optional[str]
    created_at: datetime


class ThreatFeedResponse(BaseModel):
    items: list[ThreatFeedItem]


class TrendItem(BaseModel):
    date: str
    total_scanned: int
    threats_detected: int


class TrendsResponse(BaseModel):
    trends: list[TrendItem]


class AuditLogItem(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource: str
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overall dashboard statistics.

    Returns comprehensive stats including:
    - Total messages scanned
    - Threats detected
    - Deepfakes found
    - Average risk score
    - Blocked today
    - Active campaigns
    - Breakdown by threat level
    """
    try:
        # Get risk summary
        risk_summary = get_risk_summary(db)

        # Count deepfakes found
        deepfakes_found = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.deepfake_probability >= 70
        ).count()

        # Count blocked today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        blocked_today = db.query(ScanResult).filter(
            ScanResult.created_at >= today_start,
            ScanResult.action == "BLOCK"
        ).count()

        # Detect active campaigns
        campaign_info = detect_campaign(db)
        active_campaigns = campaign_info["campaigns_detected"]

        return DashboardStats(
            total_scanned=risk_summary["total_scanned"],
            threats_detected=risk_summary["threats_detected"],
            deepfakes_found=deepfakes_found,
            avg_risk_score=risk_summary["avg_risk_score"],
            blocked_today=blocked_today,
            active_campaigns=active_campaigns,
            breakdown=risk_summary["breakdown"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )


@router.get("/threat-feed", response_model=ThreatFeedResponse)
async def get_threat_feed(
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent threats ordered by creation time.

    Returns the last N scan results, most recent first.
    """
    try:
        scans = db.query(ScanResult).filter(
            ScanResult.user_id == current_user.id
        ).order_by(
            desc(ScanResult.created_at)
        ).limit(limit).all()

        return ThreatFeedResponse(
            items=[
                ThreatFeedItem(
                    id=scan.id,
                    content_preview=scan.content[:80] + "..." if len(scan.content) > 80 else scan.content,
                    risk_score=scan.risk_score,
                    threat_level=scan.threat_level.value,
                    message_type=scan.message_type.value,
                    sender=scan.sender,
                    created_at=scan.created_at
                )
                for scan in scans
            ]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve threat feed: {str(e)}"
        )


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily scan counts and threat counts for the last N days.

    Returns array of {date, total_scanned, threats_detected}
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59)
        start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0)

        # Get scans in date range
        scans = db.query(ScanResult).filter(
            ScanResult.user_id == current_user.id,
            ScanResult.created_at >= start_date,
            ScanResult.created_at <= end_date
        ).all()

        # Group by date
        daily_stats = {}
        for scan in scans:
            date_str = scan.created_at.strftime("%Y-%m-%d")
            if date_str not in daily_stats:
                daily_stats[date_str] = {"total": 0, "threats": 0}
            daily_stats[date_str]["total"] += 1
            if scan.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM]:
                daily_stats[date_str]["threats"] += 1

        # Fill in missing dates with zeros
        trends = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            stats = daily_stats.get(date_str, {"total": 0, "threats": 0})
            trends.append(TrendItem(
                date=date_str,
                total_scanned=stats["total"],
                threats_detected=stats["threats"]
            ))
            current += timedelta(days=1)

        return TrendsResponse(trends=trends)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trends: {str(e)}"
        )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    action_filter: Optional[str] = Query(None, description="Filter by action type"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Get paginated audit log.

    Shows who did what and when.
    Requires admin role.
    """
    try:
        # Build query
        query = db.query(AuditLog)

        if action_filter:
            query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        items = query.order_by(
            desc(AuditLog.created_at)
        ).offset(offset).limit(page_size).all()

        return AuditLogResponse(
            items=[
                AuditLogItem(
                    id=item.id,
                    user_id=item.user_id,
                    action=item.action,
                    resource=item.resource,
                    details=item.details,
                    ip_address=item.ip_address,
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
            detail=f"Failed to retrieve audit log: {str(e)}"
        )
