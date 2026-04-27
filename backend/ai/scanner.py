"""
SentinelAI Message Scanner
Fraud detection using Azure OpenAI GPT-5.4-nano
Specialized for African telecom fraud patterns
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://default.cognitiveservices.azure.com")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "default-key")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
CHAT_MODEL = "gpt-5.4-nano"

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    timeout=30.0,
    max_retries=2
)

# System prompt for fraud detection - specialized for African markets
FRAUD_ANALYST_SYSTEM_PROMPT = """
You are an expert telecom fraud analyst specializing in African markets, particularly Nigeria and West Africa.
You are trained to detect scams, fraud, and social engineering attempts in SMS, WhatsApp messages, and call transcripts.

YOUR EXPERTISE INCLUDES:
- Nigerian 419 scams (advance fee fraud)
- Fake bank alerts and BVN (Bank Verification Number) scams
- OTP (One-Time Password) theft attempts
- Prize/lottery scams
- Fake loan offers
- Impersonation of banks (GTBank, Access Bank, Zenith Bank, Opay, UBA)
- Impersonation of telcos (MTN, Airtel, Glo, 9mobile)
- Impersonation of government officials (EFCC, CBN, NIBSS)
- Romance scams and pig butchering
- Investment/crypto scams
- Fake job offers
- Phishing links and social engineering

YOUR TASK:
Analyze the provided message and return a structured JSON response with:
1. risk_score: 0-100 (how likely this is fraudulent)
2. threat_level: "HIGH", "MEDIUM", "LOW", or "CLEAN"
3. flags: Array of specific fraud indicators detected
4. action: "BLOCK" (high confidence scam), "REVIEW" (suspicious), or "ALLOW" (appears legitimate)
5. reasoning: Clear explanation in plain English
6. is_scam: Boolean indicating if this appears to be a scam

SCORING GUIDELINES:
- 80-100 (HIGH): Clear scam indicators, immediate block recommended
- 50-79 (MEDIUM): Suspicious patterns, human review recommended
- 20-49 (LOW): Minor red flags, likely legitimate but monitor
- 0-19 (CLEAN): No fraud indicators detected

AFRICAN FRAUD PATTERNS TO WATCH FOR:
- Urgency: "Act now", "Your account will be closed", "Immediate action required"
- Threats: "Legal action", "Arrest warrant", "Account suspension"
- Requests for sensitive info: BVN, PIN, password, OTP, card details
- Too good to be true: Lottery wins, inheritance, bonus payments
- Impersonation: Claiming to be from CBN, EFCC, bank security, telco
- Fake links: Shortened URLs, misspelled bank domains
- Grammar patterns common in West African scams
- Phone number patterns used in known scams

Respond ONLY with valid JSON in this exact format:
{
    "risk_score": 75,
    "threat_level": "MEDIUM",
    "flags": ["urgency_tactics", "impersonation_attempt"],
    "action": "REVIEW",
    "reasoning": "Message uses urgency tactics and claims to be from bank security...",
    "is_scam": true
}
"""


async def analyse_message(
    content: str,
    message_type: str,
    sender: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyse a single message for fraud indicators using Azure OpenAI.

    Args:
        content: The message content to analyse
        message_type: Type of message (sms, whatsapp, transcript)
        sender: Optional sender identifier (phone number, email, etc.)

    Returns:
        Dict with risk_score, threat_level, flags, action, reasoning, is_scam
    """
    try:
        # Build the user prompt with context
        sender_context = f"Sender: {sender}\n" if sender else ""

        user_prompt = f"""
{sender_context}Message Type: {message_type}

Message Content:
{content}

Analyse this message for fraud indicators and return your assessment as JSON.
"""

        # Call Azure OpenAI with timeout handling
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": FRAUD_ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            ),
            timeout=30.0
        )

        # Parse the response
        raw_response = response.choices[0].message.content
        print(f"Raw API response: {raw_response}")  # Debug logging

        result = json.loads(raw_response)

        # Validate required fields exist
        required_fields = ["risk_score", "threat_level", "flags", "action", "reasoning", "is_scam"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        # Ensure risk_score is within bounds
        result["risk_score"] = max(0, min(100, float(result["risk_score"])))

        # Ensure threat_level is valid
        valid_levels = ["HIGH", "MEDIUM", "LOW", "CLEAN"]
        if result["threat_level"] not in valid_levels:
            result["threat_level"] = "MEDIUM"

        # Ensure action is valid
        valid_actions = ["BLOCK", "REVIEW", "ALLOW"]
        if result["action"] not in valid_actions:
            result["action"] = "REVIEW"

        # Ensure flags is a list
        if not isinstance(result["flags"], list):
            result["flags"] = []

        # Ensure is_scam is boolean
        result["is_scam"] = bool(result.get("is_scam", False))

        return result

    except asyncio.TimeoutError:
        print("Azure OpenAI request timed out")
        return _get_default_response("Azure OpenAI request timed out")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        return _get_default_response("Failed to parse AI response")
    except Exception as e:
        print(f"Error analysing message: {e}")
        return _get_default_response(f"Analysis error: {str(e)}")


def _get_default_response(error_msg: str) -> Dict[str, Any]:
    """Return a default medium-risk response when AI analysis fails"""
    return {
        "risk_score": 50.0,
        "threat_level": "MEDIUM",
        "flags": ["analysis_error"],
        "action": "REVIEW",
        "reasoning": f"AI analysis failed: {error_msg}. Manual review recommended.",
        "is_scam": False
    }


async def batch_analyse(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Analyse multiple messages concurrently.

    Args:
        messages: List of dicts with keys: content, message_type, sender (optional)

    Returns:
        List of analysis results in same order as input
    """
    tasks = [
        analyse_message(
            content=msg.get("content", ""),
            message_type=msg.get("message_type", "sms"),
            sender=msg.get("sender")
        )
        for msg in messages
    ]

    # Run all analyses concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions in results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Message {i} failed: {result}")
            processed_results.append(_get_default_response(f"Batch analysis error: {str(result)}"))
        else:
            processed_results.append(result)

    return processed_results
