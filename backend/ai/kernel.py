"""
SentinelAI Semantic Kernel Orchestration
Multi-step agentic fraud analysis pipeline using Microsoft Semantic Kernel
"""

import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from ai.scanner import analyse_message
from ai.risk_scorer import calculate_contextual_risk, get_threat_level

# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://default.cognitiveservices.azure.com")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "default-key")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
CHAT_MODEL = "gpt-5.4-nano"


def check_sender_history(sender: str, db: Optional[Session] = None) -> str:
    if not db or not sender:
        return "No sender history available"

    from database import ScanResult, ThreatLevel

    flagged = db.query(ScanResult).filter(
        ScanResult.sender == sender,
        ScanResult.threat_level.in_([ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value])
    ).count()

    total = db.query(ScanResult).filter(
        ScanResult.sender == sender
    ).count()

    if total == 0:
        return "No previous messages from this sender"
    elif flagged == 0:
        return f"Sender has {total} previous messages, none flagged"
    else:
        return f"WARNING: Sender has {flagged}/{total} messages flagged as suspicious"


def generate_alert(risk_score: float, threat_level: str, flags: list, reasoning: str) -> str:
    if threat_level == "CLEAN":
        return f"CLEAN: No fraud indicators detected (score: {risk_score})"

    return "\n".join([
        f"⚠️ FRAUD ALERT - {threat_level} RISK",
        f"Risk Score: {risk_score}/100",
        f"Indicators: {', '.join(flags) if flags else 'None specific'}",
        f"Analysis: {reasoning}"
    ])


def recommend_action(risk_score: float, threat_level: str, sender_flags: int, is_campaign: bool) -> str:
    if threat_level == "HIGH" or risk_score >= 80:
        action = "BLOCK"
        urgency = "IMMEDIATE"
    elif threat_level == "MEDIUM" or risk_score >= 50:
        action = "REVIEW"
        urgency = "STANDARD"
    else:
        action = "ALLOW"
        urgency = "LOW"

    if is_campaign:
        urgency = "CRITICAL - Part of active campaign"

    return f"Action: {action} | Priority: {urgency}"


async def run_fraud_analysis_pipeline(
    content: str,
    sender: Optional[str],
    message_type: str,
    db: Session
) -> Dict[str, Any]:
    """
    Run the complete fraud analysis pipeline.
    Steps: AI scan → sender history → contextual scoring → campaign detection → alert → recommendation
    """
    # Step 1: AI analysis
    ai_result = await analyse_message(content, message_type, sender)

    # Step 2: Check sender history
    sender_history = check_sender_history(sender or "", db)

    # Step 3: Contextual risk scoring
    risk_context = calculate_contextual_risk(
        base_score=ai_result["risk_score"],
        sender=sender or "",
        db=db
    )

    # Step 4: Campaign detection
    from ai.risk_scorer import detect_campaign
    campaign_info = detect_campaign(db)
    is_campaign = campaign_info["campaigns_detected"] > 0

    # Step 5: Generate alert
    final_score = risk_context["final_score"]
    final_threat = get_threat_level(final_score)

    alert = generate_alert(
        risk_score=final_score,
        threat_level=final_threat,
        flags=ai_result.get("flags", []),
        reasoning=ai_result.get("reasoning", "")
    )

    # Step 6: Recommend action
    recommendation = recommend_action(
        risk_score=final_score,
        threat_level=final_threat,
        sender_flags=len(risk_context.get("factors", [])),
        is_campaign=is_campaign
    )

    return {
        "ai_analysis": ai_result,
        "sender_history": sender_history,
        "risk_context": risk_context,
        "campaign_detected": is_campaign,
        "alert": alert,
        "recommendation": recommendation,
        "final_threat_level": final_threat,
        "final_risk_score": final_score
    }