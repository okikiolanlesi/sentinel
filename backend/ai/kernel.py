"""
SentinelAI Semantic Kernel Orchestration
Multi-step agentic fraud analysis pipeline using Microsoft Semantic Kernel
"""

import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.kernel import Kernel
from semantic_kernel.kernel_pydantic import KernelBaseModel
from semantic_kernel.functions import kernel_function
from dotenv import load_dotenv

load_dotenv()

from ai.scanner import analyse_message
from ai.risk_scorer import calculate_contextual_risk, get_threat_level
from database import ScanResult, User


# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://default.cognitiveservices.azure.com")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "default-key")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
CHAT_MODEL = "gpt-5.4-nano"


class FraudAnalysisPlugin(KernelBaseModel):
    """Semantic Kernel plugin for fraud analysis operations"""

    @kernel_function(description="Analyse a message for fraud indicators")
    def scan_message(self, content: str, message_type: str, sender: Optional[str] = None) -> str:
        """
        Scan a message for fraud indicators using AI.

        Args:
            content: Message content to analyse
            message_type: Type of message (sms, whatsapp, transcript)
            sender: Optional sender identifier

        Returns:
            JSON string with analysis results
        """
        import asyncio
        result = asyncio.run(analyse_message(content, message_type, sender))
        return str(result)

    @kernel_function(description="Check sender's history for previous flags")
    def check_sender_history(self, sender: str, db_session: Optional[Session] = None) -> str:
        """
        Check if a sender has been flagged before.

        Args:
            sender: Sender identifier
            db_session: Database session

        Returns:
            Summary of sender's history
        """
        if not db_session or not sender:
            return "No sender history available"

        from database import ScanResult, ThreatLevel

        flagged = db_session.query(ScanResult).filter(
            ScanResult.sender == sender,
            ScanResult.threat_level.in_([ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value])
        ).count()

        total = db_session.query(ScanResult).filter(
            ScanResult.sender == sender
        ).count()

        if total == 0:
            return "No previous messages from this sender"
        elif flagged == 0:
            return f"Sender has {total} previous messages, none flagged"
        else:
            return f"WARNING: Sender has {flagged}/{total} messages flagged as suspicious"

    @kernel_function(description="Generate a human-readable alert summary")
    def generate_alert(self, risk_score: float, threat_level: str, flags: list, reasoning: str) -> str:
        """
        Generate a human-readable alert for the fraud team.

        Args:
            risk_score: Risk score 0-100
            threat_level: HIGH, MEDIUM, LOW, or CLEAN
            flags: List of fraud indicators
            reasoning: AI reasoning

        Returns:
            Formatted alert message
        """
        if threat_level == "CLEAN":
            return f"CLEAN: No fraud indicators detected (score: {risk_score})"

        alert_parts = [
            f"⚠️ FRAUD ALERT - {threat_level} RISK",
            f"Risk Score: {risk_score}/100",
            f"Indicators: {', '.join(flags) if flags else 'None specific'}",
            f"Analysis: {reasoning}"
        ]

        return "\n".join(alert_parts)

    @kernel_function(description="Recommend final action based on all signals")
    def recommend_action(self, risk_score: float, threat_level: str, sender_flags: int, is_campaign: bool) -> str:
        """
        Recommend final action based on all available signals.

        Args:
            risk_score: Contextual risk score
            threat_level: Threat level
            sender_flags: Number of previous flags for this sender
            is_campaign: Whether this is part of an active campaign

        Returns:
            Recommended action with reasoning
        """
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


class FraudAnalysisPipeline:
    """
    Orchestrates multi-step fraud analysis using Semantic Kernel.
    """

    def __init__(self):
        self.kernel = Kernel()

        # Add Azure OpenAI service
        service_id = "azure-chat"
        self.kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                ai_model_id=CHAT_MODEL,
                endpoint=AZURE_ENDPOINT,
                api_key=AZURE_API_KEY,
                api_version=AZURE_API_VERSION
            )
        )

        # Add fraud analysis plugin
        self.fraud_plugin = FraudAnalysisPlugin()
        self.kernel.add_plugin(self.fraud_plugin, plugin_name="FraudAnalysis")

    async def run_fraud_analysis_pipeline(
        self,
        content: str,
        sender: Optional[str],
        message_type: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Run the complete fraud analysis pipeline.

        Steps:
        1. Scan message with AI
        2. Check sender history
        3. Apply contextual risk scoring
        4. Detect if part of campaign
        5. Generate alert
        6. Recommend action

        Args:
            content: Message content
            sender: Sender identifier
            message_type: Type of message
            db: Database session

        Returns:
            Comprehensive fraud intelligence report
        """
        # Step 1: AI analysis
        ai_result = await analyse_message(content, message_type, sender)

        # Step 2: Check sender history
        sender_history = self.fraud_plugin.check_sender_history(sender or "", db)

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
        alert = self.fraud_plugin.generate_alert(
            risk_score=risk_context["final_score"],
            threat_level=get_threat_level(risk_context["final_score"]),
            flags=ai_result.get("flags", []),
            reasoning=ai_result.get("reasoning", "")
        )

        # Step 6: Recommend action
        recommendation = self.fraud_plugin.recommend_action(
            risk_score=risk_context["final_score"],
            threat_level=get_threat_level(risk_context["final_score"]),
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
            "final_threat_level": get_threat_level(risk_context["final_score"]),
            "final_risk_score": risk_context["final_score"]
        }


# Singleton instance
_pipeline_instance: Optional[FraudAnalysisPipeline] = None


def get_fraud_pipeline() -> FraudAnalysisPipeline:
    """Get or create the fraud analysis pipeline singleton"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = FraudAnalysisPipeline()
    return _pipeline_instance
