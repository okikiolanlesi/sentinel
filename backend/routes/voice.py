"""
SentinelAI Voice Analysis Routes
Audio transcription and deepfake detection using Azure OpenAI
"""

import os
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv

from database import get_db, User, VoiceAnalysis, ThreatLevel, AuditLog, UserRole
from auth_utils import get_current_user, require_role, log_audit
from ai.scanner import analyse_message
from ai.risk_scorer import calculate_contextual_risk, get_threat_level

load_dotenv()

router = APIRouter(prefix="/api/voice", tags=["Voice Analysis"])

# Azure OpenAI Configuration for Whisper
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://default.cognitiveservices.azure.com")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "default-key")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    timeout=60.0,
    max_retries=2
)

WHISPER_MODEL = "whisper"
VOICE_ANALYSIS_MODEL = "gpt-5.4-nano"

# System prompt for voice/deepfake analysis
VOICE_FRAUD_ANALYST_PROMPT = """
You are an expert fraud analyst specializing in detecting deepfake voices and social engineering in call center contexts.

YOUR TASK:
Analyse the provided transcript for signs of:
1. DEEPFAKE INDICATORS: Unnatural speech patterns, robotic tone, inconsistent pacing, audio artifacts described in text
2. SOCIAL ENGINEERING: Urgency tactics, pressure to act immediately, requests for sensitive information
3. IMPERSONATION: Claiming to be executives, officials, bank representatives, law enforcement
4. FRAUD PATTERNS: Requests for transfers, credential harvesting, fake emergencies

AFRICAN CONTEXT:
Be alert for patterns common in Nigerian/West African voice scams:
- Fake bank security calls
- Impersonation of EFCC, CBN officials
- Fake kidnapping/duress calls
- Romance scam voice notes
- Investment pitch scams

SCORING:
- deepfake_probability: 0-100 based on unnatural speech patterns in transcript
- risk_score: 0-100 overall fraud risk
- threat_level: HIGH (80+), MEDIUM (50-79), LOW (20-49), CLEAN (0-19)

Respond ONLY with valid JSON:
{
    "deepfake_probability": 25,
    "risk_score": 65,
    "threat_level": "MEDIUM",
    "flags": ["urgency_tactics", "impersonation_attempt"],
    "reasoning": "Transcript shows pressure tactics and claims to be from bank security...",
    "is_scam": true
}
"""


# Pydantic models
class VoiceAnalysisResponse(BaseModel):
    id: str
    transcript: str
    deepfake_probability: float
    risk_score: float
    threat_level: str
    flags: list
    reasoning: str
    is_scam: bool
    created_at: datetime


class VoiceHistoryItem(BaseModel):
    id: str
    transcript_preview: str
    deepfake_probability: float
    risk_score: float
    threat_level: str
    created_at: datetime


class VoiceHistoryResponse(BaseModel):
    items: list[VoiceHistoryItem]
    total: int
    page: int
    page_size: int
    pages: int


@router.post("/analyse", response_model=VoiceAnalysisResponse)
async def analyse_voice(
    file: UploadFile = File(..., description="Audio file (webm, wav, mp3)"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Analyse an audio file for fraud indicators and deepfake detection.

    1. Transcribes audio using Azure Whisper
    2. Analyses transcript using GPT-5.4-nano
    3. Returns transcript, deepfake probability, and risk assessment
    """
    try:
        # Validate file type
        allowed_types = ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )

        # Read audio file
        audio_content = await file.read()
        if len(audio_content) > 25 * 1024 * 1024:  # 25MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 25MB"
            )

        # Step 1: Transcribe using Azure Whisper
        try:
            transcription = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=(file.filename, io.BytesIO(audio_content), file.content_type),
                response_format="text"
            )
            transcript = transcription.strip()
        except Exception as transcribe_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {str(transcribe_error)}"
            )

        if not transcript or len(transcript) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript too short. Please provide clearer audio."
            )

        # Step 2: Analyse transcript for fraud indicators
        try:
            import json
            response = client.chat.completions.create(
                model=VOICE_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": VOICE_FRAUD_ANALYST_PROMPT},
                    {"role": "user", "content": f"Transcript:\n{transcript}"}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            ai_result = json.loads(response.choices[0].message.content)
        except Exception as ai_error:
            # Fallback response
            ai_result = {
                "deepfake_probability": 50.0,
                "risk_score": 50.0,
                "threat_level": "MEDIUM",
                "flags": ["analysis_error"],
                "reasoning": f"AI analysis failed: {str(ai_error)}",
                "is_scam": False
            }

        # Validate response
        deepfake_prob = float(ai_result.get("deepfake_probability", 50.0))
        risk_score = float(ai_result.get("risk_score", 50.0))
        threat_level_str = ai_result.get("threat_level", "MEDIUM")

        # Ensure threat level is valid
        valid_levels = ["HIGH", "MEDIUM", "LOW", "CLEAN"]
        if threat_level_str not in valid_levels:
            threat_level_str = get_threat_level(risk_score)

        # Apply contextual risk scoring
        risk_context = calculate_contextual_risk(
            base_score=risk_score,
            sender="voice_analysis",  # Treat as sender for consistency
            db=db
        )

        final_threat_level = get_threat_level(risk_context["final_score"])

        # Save to database
        voice_analysis = VoiceAnalysis(
            user_id=current_user.id,
            transcript=transcript,
            deepfake_probability=deepfake_prob,
            risk_score=risk_context["final_score"],
            threat_level=ThreatLevel(final_threat_level),
            flags=ai_result.get("flags", []),
            ai_reasoning=ai_result.get("reasoning", ""),
        )

        db.add(voice_analysis)
        db.commit()
        db.refresh(voice_analysis)

        # Log analysis
        log_audit(
            db=db,
            user_id=current_user.id,
            action="VOICE_ANALYSED",
            resource="voice_analyses",
            details=f"Analysed voice file, deepfake probability: {deepfake_prob}%"
        )

        return VoiceAnalysisResponse(
            id=voice_analysis.id,
            transcript=transcript,
            deepfake_probability=deepfake_prob,
            risk_score=risk_context["final_score"],
            threat_level=final_threat_level,
            flags=voice_analysis.flags or [],
            reasoning=voice_analysis.ai_reasoning or "",
            is_scam=final_threat_level in ["HIGH", "MEDIUM"],
            created_at=voice_analysis.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice analysis failed: {str(e)}"
        )


@router.get("/history", response_model=VoiceHistoryResponse)
async def get_voice_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated voice analysis history for current user.
    """
    try:
        # Get total count
        total = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.user_id == current_user.id
        ).count()

        # Apply pagination
        offset = (page - 1) * page_size
        items = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.user_id == current_user.id
        ).order_by(VoiceAnalysis.created_at.desc()).offset(offset).limit(page_size).all()

        return VoiceHistoryResponse(
            items=[
                VoiceHistoryItem(
                    id=item.id,
                    transcript_preview=item.transcript[:100] + "..." if len(item.transcript) > 100 else item.transcript,
                    deepfake_probability=item.deepfake_probability,
                    risk_score=item.risk_score,
                    threat_level=item.threat_level.value,
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
            detail=f"Failed to retrieve voice history: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=VoiceAnalysisResponse)
async def get_voice_analysis(
    analysis_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db)
):
    """
    Get a single voice analysis result by ID.
    """
    try:
        analysis = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.id == analysis_id,
            VoiceAnalysis.user_id == current_user.id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice analysis not found"
            )

        return VoiceAnalysisResponse(
            id=analysis.id,
            transcript=analysis.transcript,
            deepfake_probability=analysis.deepfake_probability,
            risk_score=analysis.risk_score,
            threat_level=analysis.threat_level.value,
            flags=analysis.flags or [],
            reasoning=analysis.ai_reasoning or "",
            is_scam=analysis.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            created_at=analysis.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve voice analysis: {str(e)}"
        )
