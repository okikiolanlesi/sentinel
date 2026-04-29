"""
SentinelAI Voice Analysis Routes
==================================
Audio transcription + deepfake detection using Azure Whisper + GPT-5.4-nano.

v2 fixes:
  1. Transcript now routed through full analyse_message() pipeline
     (rules + retrieval + CoT + self-consistency + calibration)
  2. deepfake_probability scored separately by a dedicated GPT call
  3. Fixed 500 on silent/short audio → clean 400 with helpful message
  4. temperature lowered to 0.1 for consistent scoring
  5. Deepfake prompt upgraded with concrete signal rubric
"""

import os
import io
import json
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import AzureOpenAI
from dotenv import load_dotenv

from database import get_db, User, VoiceAnalysis, ThreatLevel, UserRole
from auth_utils import get_current_user, require_role, log_audit
from ai.scanner import analyse_message
from ai.risk_scorer import calculate_contextual_risk, get_threat_level

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice Analysis"])

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://default.cognitiveservices.azure.com")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "default-key")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    timeout=60.0,
    max_retries=2,
)

WHISPER_MODEL = "whisper"
VOICE_ANALYSIS_MODEL = "gpt-5.4-nano"


# ─────────────────────────────────────────────────────────────────────────────
# DEEPFAKE ANALYSIS PROMPT — dedicated, upgraded rubric
# ─────────────────────────────────────────────────────────────────────────────

DEEPFAKE_DETECTION_PROMPT = """You are SentinelAI's voice deepfake analyst. You receive a call/voice transcript
and must assess the probability that the voice was AI-generated or cloned.

IMPORTANT: You are analysing TEXT, not audio. You cannot detect acoustic artifacts directly.
Instead, you assess deepfake probability from CONTENT SIGNALS in the transcript:

## DEEPFAKE PROBABILITY SIGNALS (add to probability score)

HIGH signals (+25 each):
- Executive impersonation: speaker claims to be CEO/MD/Director demanding urgent action
- Secrecy instruction: "tell no one", "keep this between us", "don't mention this"
- Large sudden transfer demand outside normal business process
- Unusual urgency: "right now", "immediately", "before end of day" combined with transfer

MEDIUM signals (+15 each):
- Caller references knowing personal/internal company details in unusual ways
- Speech sounds uncharacteristically formal for the person being impersonated
- Unusual request channel (voice note/WhatsApp voice instead of official call)
- Caller deflects when asked to verify identity through normal channels

LOW signals (+8 each):
- Generic greeting that doesn't use the recipient's name
- Caller unable to answer basic verification questions
- Pressures to skip standard approval processes

## FRAUD CONTENT SIGNALS (for risk_score, separate from deepfake)

Treat the transcript like an SMS/chat for fraud detection purposes using Nigerian fraud patterns:
- EFCC/CBN/Police impersonation demanding payment
- Bank credential requests (OTP, PIN, card details)
- Transfer demands with secrecy instructions
- Prize/lottery claims
- Investment scams

## OUTPUT (strict JSON only, nothing else):
{
  "deepfake_probability": <integer 0-100>,
  "deepfake_signals": ["<signal_1>", "<signal_2>"],
  "deepfake_reasoning": "<1-2 sentences on why this voice may/may not be AI-generated>",
  "risk_score": <integer 0-100>,
  "threat_level": "<HIGH|MEDIUM|LOW|CLEAN>",
  "flags": ["<fraud_flag_1>", "<fraud_flag_2>"],
  "reasoning": "<2-3 sentences on fraud risk in the transcript>",
  "is_scam": <true|false>
}

THRESHOLDS:
- deepfake_probability 70+  = likely AI-generated voice
- deepfake_probability 40-69 = suspicious, inconclusive
- deepfake_probability 0-39  = likely human
- risk_score: same rules as SMS (80+ = HIGH/BLOCK, 50-79 = MEDIUM/REVIEW, etc.)
"""


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class VoiceAnalysisResponse(BaseModel):
    id: str
    transcript: str
    deepfake_probability: float
    deepfake_signals: List[str]
    deepfake_reasoning: str
    risk_score: float
    threat_level: str
    flags: list
    reasoning: str
    is_scam: bool
    source: str
    created_at: datetime


class VoiceHistoryItem(BaseModel):
    id: str
    transcript_preview: str
    deepfake_probability: float
    risk_score: float
    threat_level: str
    is_scam: bool
    created_at: datetime


class VoiceHistoryResponse(BaseModel):
    items: List[VoiceHistoryItem]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSE VOICE ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analyse", response_model=VoiceAnalysisResponse)
async def analyse_voice(
    file: UploadFile = File(..., description="Audio file (webm, wav, mp3, mpeg)"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    """
    Full voice fraud + deepfake analysis:
    1. Transcribe with Azure Whisper
    2. Run transcript through full 5-layer fraud scanner (same as SMS)
    3. Run dedicated deepfake probability assessment
    4. Combine results into unified response
    """
    try:
        # Validate file type
        allowed_types = ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg",
                         "audio/ogg", "audio/x-wav", "audio/x-m4a"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{file.content_type}'. "
                       f"Allowed: webm, wav, mp3, mpeg, ogg, m4a",
            )

        audio_content = await file.read()

        if len(audio_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is empty. Please upload a valid audio file.",
            )

        if len(audio_content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 25MB",
            )

        # ── Step 1: Transcribe with Whisper ──────────────────────────────────
        try:
            transcription = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=(file.filename or "audio.wav", io.BytesIO(audio_content), file.content_type),
                response_format="text",
            )
            transcript = str(transcription).strip()
        except Exception as e:
            err = str(e).lower()
            # Whisper-specific errors → return a clean 400, not 500
            if any(x in err for x in ["empty", "silent", "no speech", "audio", "too short"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not transcribe audio. The file may be silent, "
                           "too short, or contain no speech. Please upload a clear "
                           "voice recording.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {str(e)}",
            )

        if not transcript or len(transcript.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript too short or empty. Please provide a clear audio "
                       "recording with speech content.",
            )

        # ── Step 2: Route transcript through full fraud scanner ──────────────
        # This gives us rules + retrieval + CoT + self-consistency + calibration
        fraud_result = await analyse_message(
            content=transcript,
            message_type="transcript",
            sender="voice_analysis",
        )

        # ── Step 3: Dedicated deepfake probability assessment ────────────────
        deepfake_prob = 0.0
        deepfake_signals: List[str] = []
        deepfake_reasoning = "No deepfake indicators detected in transcript."

        try:
            df_response = client.chat.completions.create(
                model=VOICE_ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": DEEPFAKE_DETECTION_PROMPT},
                    {"role": "user", "content": f"Transcript:\n{transcript}"},
                ],
                temperature=0.1,
                max_completion_tokens=400,
                response_format={"type": "json_object"},
            )
            df_result = json.loads(df_response.choices[0].message.content)
            deepfake_prob = float(df_result.get("deepfake_probability", 0))
            deepfake_signals = df_result.get("deepfake_signals", [])
            deepfake_reasoning = df_result.get("deepfake_reasoning", "")

            # If deepfake analysis gave a higher fraud score, use the higher one
            df_fraud_score = float(df_result.get("risk_score", 0))
            if df_fraud_score > fraud_result["risk_score"]:
                fraud_result["risk_score"] = df_fraud_score
                for flag in df_result.get("flags", []):
                    if flag not in fraud_result["flags"]:
                        fraud_result["flags"].append(flag)

        except Exception as e:
            logger.warning(f"Deepfake assessment failed (non-critical): {e}")
            # Use content-based heuristic as fallback
            if fraud_result["is_scam"] and any(
                f in fraud_result["flags"]
                for f in ["bec_executive_secrecy", "bec_deepfake",
                          "executive_impersonation", "transfer_secrecy"]
            ):
                deepfake_prob = 75.0
                deepfake_reasoning = "BEC/executive impersonation pattern detected — " \
                                     "elevated deepfake probability based on content signals."

        # ── Step 4: Apply contextual risk scoring ────────────────────────────
        risk_context = calculate_contextual_risk(
            base_score=fraud_result["risk_score"],
            sender="voice_analysis",
            db=db,
        )
        final_score = risk_context["final_score"]
        final_threat = get_threat_level(final_score)

        # ── Step 5: Save to database ─────────────────────────────────────────
        all_flags = list(set(fraud_result.get("flags", []) + deepfake_signals))
        full_reasoning = fraud_result.get("reasoning", "")
        if deepfake_reasoning and deepfake_reasoning != "No deepfake indicators detected in transcript.":
            full_reasoning = f"{full_reasoning} | DEEPFAKE: {deepfake_reasoning}"

        voice_analysis = VoiceAnalysis(
            user_id=current_user.id,
            transcript=transcript,
            deepfake_probability=deepfake_prob,
            risk_score=final_score,
            threat_level=ThreatLevel(final_threat),
            flags=all_flags,
            ai_reasoning=full_reasoning,
        )
        db.add(voice_analysis)
        db.commit()
        db.refresh(voice_analysis)

        log_audit(
            db=db, user_id=current_user.id, action="VOICE_ANALYSED",
            resource="voice_analyses",
            details=f"Voice analysis: deepfake={deepfake_prob:.0f}%, risk={final_score:.0f}",
        )

        return VoiceAnalysisResponse(
            id=voice_analysis.id,
            transcript=transcript,
            deepfake_probability=deepfake_prob,
            deepfake_signals=deepfake_signals,
            deepfake_reasoning=deepfake_reasoning,
            risk_score=final_score,
            threat_level=final_threat,
            flags=all_flags,
            reasoning=full_reasoning,
            is_scam=final_threat in ["HIGH", "MEDIUM"],
            source=fraud_result.get("source", "gpt+calibration"),
            created_at=voice_analysis.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Voice analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice analysis failed: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=VoiceHistoryResponse)
async def get_voice_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        total = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.user_id == current_user.id
        ).count()

        offset = (page - 1) * page_size
        items = (
            db.query(VoiceAnalysis)
            .filter(VoiceAnalysis.user_id == current_user.id)
            .order_by(VoiceAnalysis.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return VoiceHistoryResponse(
            items=[
                VoiceHistoryItem(
                    id=item.id,
                    transcript_preview=(
                        item.transcript[:120] + "..."
                        if len(item.transcript) > 120 else item.transcript
                    ),
                    deepfake_probability=item.deepfake_probability,
                    risk_score=item.risk_score,
                    threat_level=item.threat_level.value,
                    is_scam=item.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve voice history: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GET SINGLE VOICE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{analysis_id}", response_model=VoiceAnalysisResponse)
async def get_voice_analysis(
    analysis_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    try:
        analysis = db.query(VoiceAnalysis).filter(
            VoiceAnalysis.id == analysis_id,
            VoiceAnalysis.user_id == current_user.id,
        ).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Voice analysis not found")

        return VoiceAnalysisResponse(
            id=analysis.id,
            transcript=analysis.transcript,
            deepfake_probability=analysis.deepfake_probability,
            deepfake_signals=analysis.flags or [],
            deepfake_reasoning="",
            risk_score=analysis.risk_score,
            threat_level=analysis.threat_level.value,
            flags=analysis.flags or [],
            reasoning=analysis.ai_reasoning or "",
            is_scam=analysis.threat_level in [ThreatLevel.HIGH, ThreatLevel.MEDIUM],
            source="gpt+calibration",
            created_at=analysis.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve voice analysis: {str(e)}")
