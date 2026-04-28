"""
SentinelAI — Scam Detection Engine
Powered by Azure OpenAI GPT-5.4-nano + Few-Shot Nigerian Fraud Intelligence
TeKnowledge x Microsoft 2026 Agentic AI Hackathon
"""

import os
import json
import asyncio
import logging
from openai import AzureOpenAI
from typing import Optional

logger = logging.getLogger(__name__)

_client_instance: Optional[AzureOpenAI] = None


def get_client() -> AzureOpenAI:
    """Lazy-initialised singleton AzureOpenAI client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_ENDPOINT", "https://placeholder.azure.com"),
            api_key=os.getenv("AZURE_API_KEY", "placeholder"),
            api_version=os.getenv("AZURE_API_VERSION", "2025-01-01-preview"),
        )
    return _client_instance


CHAT_MODEL = os.getenv("AZURE_CHAT_MODEL", "gpt-5.4-nano")

DEFAULT_MEDIUM_RISK = {
    "risk_score": 50,
    "threat_level": "MEDIUM",
    "flags": ["analysis_unavailable"],
    "action": "REVIEW",
    "reasoning": "Unable to complete AI analysis. Manual review recommended.",
    "is_scam": False
}

FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
Message: "URGENT: Your GTBank account has been suspended. Verify your BVN at gtb-secure-verify.com within 24 hours or face permanent closure."
{"risk_score": 97, "threat_level": "HIGH", "flags": ["fake_domain", "urgency_language", "bank_impersonation", "bvn_request", "threat_of_closure"], "action": "BLOCK", "reasoning": "Impersonates GTBank with fake domain. BVN requests via SMS are primary identity theft vectors in Nigeria. Permanent closure threat forces panic-driven action.", "is_scam": true}

EXAMPLE 2:
Message: "CONGRATULATIONS! You won ₦2,500,000 in the MTN Anniversary Promo. Claim: send your account number to mtn-promo@gmail.com"
{"risk_score": 98, "threat_level": "HIGH", "flags": ["prize_scam", "gmail_contact", "account_details_request", "telco_impersonation"], "action": "BLOCK", "reasoning": "No legitimate Nigerian telco uses Gmail for prize distributions. Account number request designed to steal banking credentials.", "is_scam": true}

EXAMPLE 3:
Message: "Your OTP is 847291. Share this code with our customer care agent to complete verification."
{"risk_score": 99, "threat_level": "HIGH", "flags": ["otp_sharing_request", "credential_theft", "social_engineering"], "action": "BLOCK", "reasoning": "Legitimate banks NEVER ask customers to share OTP codes. This is a direct account takeover attempt by definition.", "is_scam": true}

EXAMPLE 4:
Message: "CBN ALERT: All accounts must be re-verified at cbn-verify-ng.com with your BVN and NIN or be frozen."
{"risk_score": 96, "threat_level": "HIGH", "flags": ["cbn_impersonation", "fake_domain", "bvn_request", "nin_request", "false_authority"], "action": "BLOCK", "reasoning": "CBN never sends individual verification requests via SMS. Collecting BVN and NIN together enables complete identity theft.", "is_scam": true}

EXAMPLE 5:
Message: "Your GTBank account XXXXXX1234 has been credited with ₦150,000.00. Balance: ₦387,450.22. Date: 24-Apr-2026. Not you? Call 07300000000."
{"risk_score": 3, "threat_level": "CLEAN", "flags": [], "action": "ALLOW", "reasoning": "Standard GTBank credit alert with masked account number, official helpline, no links or credential requests.", "is_scam": false}

EXAMPLE 6:
Message: "Earn ₦150,000 daily from home, 2 hours work, no experience needed. WhatsApp us now. Limited slots."
{"risk_score": 85, "threat_level": "HIGH", "flags": ["unrealistic_income_promise", "job_scam", "whatsapp_redirect"], "action": "BLOCK", "reasoning": "No legitimate employer offers ₦150,000/day for 2 hours with no experience. Consistent with money mule recruitment.", "is_scam": true}

EXAMPLE 7:
Message: "This is the MD calling. Transfer ₦15,000,000 to GTBank 0123456789, Acme Supplies. Tell no one, I will explain later."
{"risk_score": 98, "threat_level": "HIGH", "flags": ["executive_impersonation", "large_transfer_request", "secrecy_instruction", "deepfake_likely", "bec_pattern"], "action": "BLOCK", "reasoning": "Classic deepfake CEO fraud. Large transfer combined with secrecy instruction is the highest-risk combination in Nigerian corporate fraud.", "is_scam": true}

EXAMPLE 8:
Message: "Your Access Bank loan repayment of ₦45,000 is due 30th April. Pay via mobile app or any branch. Helpline: 01-2712005"
{"risk_score": 4, "threat_level": "CLEAN", "flags": [], "action": "ALLOW", "reasoning": "Legitimate loan repayment reminder. Official helpline provided, no links, directs to official payment channels.", "is_scam": false}

EXAMPLE 9:
Message: "Pre-approved loan of ₦500,000 available. Pay ₦3,000 insurance fee to account 0987654321 Wema Bank to activate."
{"risk_score": 78, "threat_level": "MEDIUM", "flags": ["upfront_fee_request", "advance_fee", "unsolicited_loan"], "action": "REVIEW", "reasoning": "Advance fee loan fraud. Legitimate lenders never require upfront fees. Medium risk due to less aggressive language.", "is_scam": true}

EXAMPLE 10:
Message: "EFCC: Your account is linked to money laundering. Pay ₦200,000 bond immediately to avoid arrest today."
{"risk_score": 97, "threat_level": "HIGH", "flags": ["law_enforcement_impersonation", "arrest_threat", "extortion", "payment_demand"], "action": "BLOCK", "reasoning": "EFCC never calls to demand bond payments via SMS. Pure extortion using false authority and arrest threats.", "is_scam": true}
"""

FRAUD_ANALYST_SYSTEM_PROMPT = f"""You are SentinelAI, an expert AI fraud analyst specialising in Nigerian and African telecom fraud. You have deep knowledge of all scam patterns targeting Nigerian consumers and businesses.

YOUR EXPERTISE:

ALWAYS BLOCK (risk 90-100):
- OTP sharing requests — banks NEVER ask for OTP sharing, ever
- Card number + CVV requests — no bank ever asks for this
- Executive impersonation + transfer + secrecy = deepfake CEO fraud
- Government impersonation (CBN, EFCC, NIMC, Police) demanding payment or credentials
- Fake bank domains collecting BVN/NIN/passwords

USUALLY BLOCK (risk 70-89):
- Prize scams from MTN/Airtel/Glo using Gmail contacts
- Job scams promising ₦50,000-₦500,000/day
- Investment scams promising guaranteed 100-300% returns
- Loan scams requiring upfront fees before disbursement

REVIEW (risk 50-69):
- Unsolicited loan offers without upfront fee requests
- Suspicious domains but without direct credential requests
- Unverifiable transaction alerts with suspicious call-back numbers

ALLOW (risk 0-49):
- Standard bank transaction alerts (masked account numbers, official helplines)
- Airtime/data bundle confirmations
- Loan repayment reminders with official channels
- USSD code instructions

KEY NIGERIAN FRAUD SIGNALS:
- Fake domains: gtb-verify.com, cbn-alert.net, access-bank-secure.com (not .com.ng or official domains)
- Gmail/Yahoo contacts for banks = always scam
- BVN + NIN + DOB together = identity theft setup
- OTP sharing request = account takeover
- Processing fee for loan/prize = advance fee fraud
- "Tell no one" + transfer request = deepfake/BEC fraud
- Arrest threat + payment demand = EFCC/Police impersonation extortion

LEGITIMATE SIGNALS:
- Masked account numbers (XXXXXX1234)
- Official bank helplines (0730-000-0000, 0700-xxx-xxxx format)
- USSD codes (*737#, *901#, *131#)
- Transaction reference numbers
- Directing to official app/branch (not links)

FEW-SHOT TRAINING EXAMPLES:
{FEW_SHOT_EXAMPLES}

RESPOND WITH ONLY VALID JSON — no text outside the JSON:
{{"risk_score": <0-100>, "threat_level": "<HIGH|MEDIUM|LOW|CLEAN>", "flags": [<array of flag strings>], "action": "<BLOCK|REVIEW|ALLOW>", "reasoning": "<1-3 sentence plain English explanation>", "is_scam": <true|false>}}"""


async def analyse_message(
    content: str,
    message_type: str = "sms",
    sender: Optional[str] = None
) -> dict:
    """
    Analyse a message for fraud using GPT-5.4-nano with Nigerian fraud intelligence.
    """
    try:
        sender_context = f"Sender: {sender}\n" if sender else ""
        user_prompt = f"""Analyse this {message_type.upper()} for fraud:

{sender_context}Message: "{content}"

JSON response only."""

        response = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": FRAUD_ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=400,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        logger.debug(f"Raw AI response: {raw}")
        result = json.loads(raw)

        return {
            "risk_score": max(0, min(100, float(result.get("risk_score", 50)))),
            "threat_level": result.get("threat_level", "MEDIUM"),
            "flags": result.get("flags", []),
            "action": result.get("action", "REVIEW"),
            "reasoning": result.get("reasoning", "Analysis completed."),
            "is_scam": bool(result.get("is_scam", False))
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return DEFAULT_MEDIUM_RISK
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return DEFAULT_MEDIUM_RISK


async def batch_analyse(messages: list) -> list:
    """
    Analyse multiple messages concurrently.
    """
    tasks = [
        analyse_message(
            content=msg.get("content", ""),
            message_type=msg.get("message_type", "sms"),
            sender=msg.get("sender")
        )
        for msg in messages
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        r if not isinstance(r, Exception) else DEFAULT_MEDIUM_RISK
        for r in results
    ]


async def evaluate_model_performance() -> dict:
    """
    Run evaluation set to measure model accuracy against known samples.
    """
    dataset_path = os.path.join(
        os.path.dirname(__file__), "data", "nigerian_scam_dataset.json"
    )

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    evaluation_set = dataset.get("evaluation_set", [])
    correct = 0
    total = len(evaluation_set)
    results = []

    for item in evaluation_set:
        result = await analyse_message(content=item["content"], message_type="sms")
        expected = item["expected_action"]
        predicted = result["action"]
        is_correct = expected == predicted
        if is_correct:
            correct += 1
        results.append({
            "id": item["id"],
            "preview": item["content"][:60] + "...",
            "expected": expected,
            "predicted": predicted,
            "risk_score": result["risk_score"],
            "correct": is_correct
        })

    return {
        "accuracy": round((correct / total * 100) if total > 0 else 0, 2),
        "correct": correct,
        "total": total,
        "results": results
    }


def get_threat_level_from_score(score: float) -> str:
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    return "CLEAN"
