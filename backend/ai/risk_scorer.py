"""
SentinelAI Risk Scorer
Contextual risk scoring that goes beyond single message analysis
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import ScanResult, ThreatLevel


def get_threat_level(score: float) -> str:
    """
    Convert a numeric risk score to a threat level.

    Args:
        score: Risk score from 0-100

    Returns:
        Threat level string: HIGH, MEDIUM, LOW, or CLEAN
    """
    if score >= 80:
        return ThreatLevel.HIGH.value
    elif score >= 50:
        return ThreatLevel.MEDIUM.value
    elif score >= 20:
        return ThreatLevel.LOW.value
    else:
        return ThreatLevel.CLEAN.value


def calculate_contextual_risk(
    base_score: float,
    sender: str,
    db: Session
) -> Dict[str, Any]:
    """
    Calculate contextual risk score based on sender history and patterns.

    Adjustments:
    - Sender history: +15 if same sender flagged before
    - Campaign detection: +20 if 10+ similar messages in last 60 minutes
    - Time pattern: +10 if message between 1AM-5AM

    Args:
        base_score: Base risk score from AI analysis (0-100)
        sender: Sender identifier (phone number, email, etc.)
        db: Database session

    Returns:
        Dict with final_score, original_score, and factors list
    """
    final_score = base_score
    factors = []

    # Check sender history - if same sender has been flagged before
    if sender:
        flagged_count = db.query(ScanResult).filter(
            ScanResult.sender == sender,
            ScanResult.threat_level.in_([ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value])
        ).count()

        if flagged_count > 0:
            final_score += 15
            factors.append(f"sender_history ({flagged_count} previous flags)")

    # Check campaign detection - 10+ similar messages in last 60 minutes
    one_hour_ago = datetime.utcnow() - timedelta(minutes=60)
    recent_count = db.query(ScanResult).filter(
        ScanResult.created_at >= one_hour_ago,
        ScanResult.threat_level.in_([ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value])
    ).count()

    if recent_count >= 10:
        final_score += 20
        factors.append(f"active_campaign ({recent_count} threats in last hour)")

    # Check time pattern - messages between 1AM-5AM
    current_hour = datetime.utcnow().hour
    if 1 <= current_hour < 5:
        final_score += 10
        factors.append("suspicious_time (1AM-5AM)")

    # Cap final score at 100
    final_score = min(100, final_score)

    return {
        "final_score": final_score,
        "original_score": base_score,
        "factors": factors
    }


def detect_campaign(
    db: Session,
    time_window_minutes: int = 60,
    threshold: int = 10
) -> Dict[str, Any]:
    """
    Detect active scam campaigns by analyzing recent scan patterns.

    Args:
        db: Database session
        time_window_minutes: Time window to analyze
        threshold: Number of similar messages to trigger campaign alert

    Returns:
        Dict with campaign detection results
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

    # Get high-threat scans in the time window
    recent_threats = db.query(ScanResult).filter(
        ScanResult.created_at >= cutoff_time,
        ScanResult.threat_level == ThreatLevel.HIGH.value
    ).all()

    # Group by sender to find coordinated campaigns
    sender_counts: Dict[str, int] = {}
    for scan in recent_threats:
        if scan.sender:
            sender_counts[scan.sender] = sender_counts.get(scan.sender, 0) + 1

    # Find senders exceeding threshold
    active_campaigns = [
        {"sender": sender, "count": count}
        for sender, count in sender_counts.items()
        if count >= threshold
    ]

    return {
        "campaigns_detected": len(active_campaigns),
        "campaigns": active_campaigns,
        "total_threats_analyzed": len(recent_threats)
    }


def get_risk_summary(db: Session) -> Dict[str, Any]:
    """
    Get overall risk statistics for the dashboard.

    Returns:
        Dict with risk statistics
    """
    # Count by threat level
    threat_counts = db.query(
        ScanResult.threat_level,
        func.count(ScanResult.id)
    ).group_by(ScanResult.threat_level).all()

    breakdown = {level: count for level, count in threat_counts}

    # Average risk score
    avg_score = db.query(func.avg(ScanResult.risk_score)).scalar() or 0

    # Total scanned
    total = db.query(func.count(ScanResult.id)).scalar() or 0

    # Threats detected (HIGH + MEDIUM)
    threats = db.query(func.count(ScanResult.id)).filter(
        ScanResult.threat_level.in_([ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value])
    ).scalar() or 0

    return {
        "total_scanned": total,
        "threats_detected": threats,
        "avg_risk_score": round(avg_score, 2),
        "breakdown": {
            "HIGH": breakdown.get("HIGH", 0),
            "MEDIUM": breakdown.get("MEDIUM", 0),
            "LOW": breakdown.get("LOW", 0),
            "CLEAN": breakdown.get("CLEAN", 0)
        }
    }
