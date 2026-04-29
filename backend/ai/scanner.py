from dotenv import load_dotenv
load_dotenv()
"""
SentinelAI — Scam Detection Engine v2 (Hardened)
=================================================
Powered by Azure OpenAI GPT-5.4-nano + 5-layer accuracy stack:

  1. RULE PRE-FLIGHT     — deterministic regex catches obvious cases
  2. DYNAMIC FEW-SHOT    — retrieve 3 most similar examples from labelled corpus
  3. CHAIN-OF-THOUGHT    — extract signals first, then score (not direct guess)
  4. SELF-CONSISTENCY    — for borderline cases (40-75), run twice and reconcile
  5. CALIBRATION         — post-process to enforce floors / ceilings / consistency

TeKnowledge x Microsoft 2026 Agentic AI Hackathon
"""

import os
import json
import asyncio
import logging
from openai import AzureOpenAI
from typing import Optional, Dict, Any

from ai.rules import apply_rules
from ai.retriever import retrieve_similar_examples, format_examples_for_prompt
from ai.calibrator import calibrate

logger = logging.getLogger(__name__)

_client_instance: Optional[AzureOpenAI] = None


def get_client() -> AzureOpenAI:
    """Lazy-initialised singleton AzureOpenAI client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_ENDPOINT", "https://placeholder.azure.com"),
            api_key=os.getenv("AZURE_API_KEY", "placeholder"),
            api_version=os.getenv("AZURE_API_VERSION", "2024-02-01"),
        )
    return _client_instance


CHAT_MODEL = os.getenv("AZURE_CHAT_MODEL", "gpt-5.4-nano")

DEFAULT_MEDIUM_RISK = {
    "risk_score": 50,
    "threat_level": "MEDIUM",
    "flags": ["analysis_unavailable"],
    "action": "REVIEW",
    "reasoning": "Unable to complete AI analysis. Manual review recommended.",
    "is_scam": False,
    "source": "fallback",
    "calibration_log": [],
    "self_consistency_applied": False,
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FEW-SHOT EXAMPLES (always included as baseline)
# ─────────────────────────────────────────────────────────────────────────────

CORE_FEW_SHOT = """
EXAMPLE A (Bank impersonation + fake domain):
Message: "URGENT: Your GTBank account has been suspended. Verify your BVN at gtb-secure-verify.com within 24 hours or face permanent closure."
Output: {"risk_score": 97, "threat_level": "HIGH", "flags": ["fake_domain", "urgency_language", "bank_impersonation", "bvn_request", "threat_of_closure"], "action": "BLOCK", "reasoning": "Impersonates GTBank with fake domain. BVN requests via SMS are primary identity theft vectors in Nigeria. Permanent closure threat forces panic-driven action.", "is_scam": true}

EXAMPLE B (OTP sharing — always 95+):
Message: "Your OTP is 847291. Share this code with our customer care agent to complete verification."
Output: {"risk_score": 99, "threat_level": "HIGH", "flags": ["otp_sharing_request", "credential_theft", "social_engineering"], "action": "BLOCK", "reasoning": "Legitimate banks NEVER ask customers to share OTP codes. This is a direct account takeover attempt by definition.", "is_scam": true}

EXAMPLE C (Deepfake CEO / BEC):
Message: "This is the MD calling. Transfer ₦15,000,000 to GTBank 0123456789, Acme Supplies. Tell no one, I will explain later."
Output: {"risk_score": 98, "threat_level": "HIGH", "flags": ["executive_impersonation", "large_transfer_request", "secrecy_instruction", "deepfake_likely", "bec_pattern"], "action": "BLOCK", "reasoning": "Classic deepfake CEO fraud. Large transfer combined with secrecy instruction is the highest-risk combination in Nigerian corporate fraud.", "is_scam": true}

EXAMPLE D (Legitimate bank alert):
Message: "Your GTBank account XXXXXX1234 has been credited with N150,000.00. Balance: N387,450.22. Date: 24-Apr-2026. Not you? Call 07300000000."
Output: {"risk_score": 3, "threat_level": "CLEAN", "flags": [], "action": "ALLOW", "reasoning": "Standard GTBank credit alert with masked account number, official helpline, no links or credential requests.", "is_scam": false}

EXAMPLE E (Government impersonation extortion):
Message: "EFCC: Your account is linked to money laundering. Pay N200,000 bond immediately to avoid arrest today."
Output: {"risk_score": 97, "threat_level": "HIGH", "flags": ["law_enforcement_impersonation", "arrest_threat", "extortion", "payment_demand"], "action": "BLOCK", "reasoning": "EFCC never calls to demand bond payments via SMS. Pure extortion using false authority and arrest threats.", "is_scam": true}

EXAMPLE F (Advance-fee loan — medium risk):
Message: "Pre-approved loan of N500,000 available. Pay N3,000 insurance fee to account 0987654321 Wema Bank to activate."
Output: {"risk_score": 78, "threat_level": "MEDIUM", "flags": ["upfront_fee_request", "advance_fee", "unsolicited_loan"], "action": "REVIEW", "reasoning": "Advance fee loan fraud. Legitimate lenders never require upfront fees. Medium risk due to less aggressive language.", "is_scam": true}
"""


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT BUILDER — assembled per-request with retrieved examples
# ─────────────────────────────────────────────────────────────────────────────

def _build_system_prompt(retrieved_examples_block: str) -> str:
    """Assemble the full system prompt with dynamic few-shot block."""
    return f"""You are SentinelAI, an expert AI fraud analyst specialising in Nigerian and African telecom fraud. You analyse SMS, WhatsApp, and voice transcripts for banks, fintechs, telcos, and call centres.

# YOUR REASONING PROCESS (chain-of-thought)
For every message, internally walk through these steps before scoring:
  1. Identify the message TYPE (bank alert, promotional, request, transactional)
  2. List every specific FRAUD SIGNAL you can detect (be exhaustive)
  3. List every LEGITIMACY SIGNAL you can detect
  4. Apply the SCORING RUBRIC below based on signals counted
  5. Cross-check: do the score, threat_level, and action all agree?

# SCORING RUBRIC (apply strictly)

## ALWAYS BLOCK (risk 90-100) - these are categorical:
- OTP / PIN sharing requests -> 95+ minimum
- Card number + CVV requests -> 95+ minimum
- Executive impersonation + transfer + secrecy = deepfake CEO fraud -> 95+
- Government impersonation (CBN, EFCC, NDLEA, NIMC, Police) demanding payment or credentials -> 95+
- Fake bank domains harvesting BVN/NIN/passwords -> 90+

## USUALLY BLOCK (risk 70-89):
- Prize scams from MTN/Airtel/Glo/9mobile using Gmail/Yahoo contacts
- Job scams promising N50,000-N500,000/day for minimal work
- Investment scams promising guaranteed 100-300% returns
- Loan scams requiring upfront fees before disbursement

## REVIEW (risk 50-69):
- Unsolicited loan offers without explicit upfront fee requests
- Suspicious domains without direct credential requests
- Unverifiable transaction alerts with suspicious call-back numbers

## ALLOW (risk 0-49):
- Standard bank transaction alerts (masked account numbers, official helplines)
- Airtime/data bundle confirmations
- Loan repayment reminders citing official channels (apps, branches, USSD)
- USSD code instructions (*737#, *901#, *131# etc.)

# NIGERIAN FRAUD SIGNAL CHEATSHEET

CONFIRMED FRAUD SIGNALS:
- Fake domains (gtb-verify.com, cbn-alert.net, anything-bank-secure.xyz). Real Nigerian banks use .com.ng, .ng, or their official .com.
- Gmail / Yahoo contact for banks/telcos = always scam.
- BVN + NIN + DOB requested together = identity theft kit.
- Any OTP sharing instruction = account takeover.
- Upfront fee for loan/prize/grant = advance fee fraud (419).
- "Tell no one" / "keep this confidential" + transfer instruction = BEC / deepfake.
- Arrest threat + payment demand = EFCC/Police impersonation extortion.
- Shortened URLs (bit.ly, tinyurl) for "bank verification" = phishing.

LEGITIMACY SIGNALS:
- Masked account numbers (XXXXXX1234, ****4821)
- Official bank helplines in 0700-/0730-/01- format
- USSD codes (*737#, *901#, *131#)
- Transaction reference numbers
- Directing to official mobile app / branch (not embedded links)
- Specific date and merchant name in transaction alerts

# REFERENCE EXAMPLES
{CORE_FEW_SHOT}
{retrieved_examples_block}

# OUTPUT FORMAT (strict JSON, nothing else)
{{"risk_score": <int 0-100>, "threat_level": "<HIGH|MEDIUM|LOW|CLEAN>", "flags": [<strings>], "action": "<BLOCK|REVIEW|ALLOW>", "reasoning": "<2-3 sentence plain-English explanation>", "is_scam": <true|false>}}

THRESHOLDS (must be consistent):
- risk_score 80-100 -> threat_level HIGH -> action BLOCK
- risk_score 50-79  -> threat_level MEDIUM -> action REVIEW
- risk_score 20-49  -> threat_level LOW -> action ALLOW
- risk_score 0-19   -> threat_level CLEAN -> action ALLOW
- is_scam = true if risk_score >= 50, otherwise false
"""


# ─────────────────────────────────────────────────────────────────────────────
# GPT CALL WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

async def _call_gpt(
    content: str,
    message_type: str,
    sender: Optional[str],
    system_prompt: str,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """Single GPT call returning parsed JSON dict."""
    sender_context = f"Sender: {sender}\n" if sender else ""
    user_prompt = (
        f"Analyse this {message_type.upper()} for fraud:\n\n"
        f'{sender_context}Message: "{content}"\n\n'
        f"Walk through your reasoning, then output the JSON verdict only."
    )

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=500,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def analyse_message(
    content: str,
    message_type: str = "sms",
    sender: Optional[str] = None,
) -> dict:
    """
    Hardened fraud analysis: rule pre-flight -> retrieval -> CoT GPT call ->
    self-consistency on borderline -> calibration.
    """
    try:
        # Layer 1: Rule pre-flight
        rule_result = apply_rules(content)

        if rule_result and rule_result.get("skip_gpt"):
            logger.info(f"Rule engine hard verdict: {rule_result.get('flags')}")
            return _shape_result({
                "risk_score": rule_result["risk_score"],
                "threat_level": rule_result["threat_level"],
                "flags": rule_result["flags"],
                "action": rule_result["action"],
                "reasoning": rule_result["reasoning"],
                "is_scam": rule_result["is_scam"],
                "source": "rule_engine",
            })

        rule_priors = rule_result.get("priors") if rule_result else None

        # Layer 2: Dynamic few-shot retrieval
        similar = retrieve_similar_examples(content, k=3)
        retrieved_block = format_examples_for_prompt(similar)
        system_prompt = _build_system_prompt(retrieved_block)

        # Layer 3: First GPT call with chain-of-thought
        first = await _call_gpt(content, message_type, sender, system_prompt, temperature=0.1)
        score = float(first.get("risk_score", 50))

        final = first

        # Layer 4: Self-consistency on borderline cases (40-75)
        if 40 <= score <= 75:
            try:
                second = await _call_gpt(
                    content, message_type, sender, system_prompt, temperature=0.3
                )
                avg = (score + float(second.get("risk_score", score))) / 2
                merged_flags = list(set(
                    list(first.get("flags", [])) + list(second.get("flags", []))
                ))
                reasoning = max(
                    [first.get("reasoning", ""), second.get("reasoning", "")],
                    key=len,
                )
                final = {
                    "risk_score": avg,
                    "threat_level": first.get("threat_level"),
                    "flags": merged_flags,
                    "action": first.get("action"),
                    "reasoning": reasoning,
                    "is_scam": first.get("is_scam"),
                    "self_consistency_applied": True,
                    "scores_observed": [score, float(second.get("risk_score", score))],
                }
                logger.info(f"Self-consistency applied: {final['scores_observed']}")
            except Exception as e:
                logger.warning(f"Self-consistency second call failed: {e}")

        # Layer 5: Calibration
        calibrated = calibrate(final, content, rule_priors=rule_priors)

        return _shape_result({**calibrated, "source": "gpt+calibration"})

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return DEFAULT_MEDIUM_RISK
    except Exception as e:
        print("ERROR:", e)
        raise e


def _shape_result(r: Dict[str, Any]) -> dict:
    """Coerce all fields to expected types and bounds."""
    return {
        "risk_score": max(0.0, min(100.0, float(r.get("risk_score", 50)))),
        "threat_level": r.get("threat_level", "MEDIUM"),
        "flags": list(r.get("flags", [])),
        "action": r.get("action", "REVIEW"),
        "reasoning": r.get("reasoning", "Analysis completed."),
        "is_scam": bool(r.get("is_scam", False)),
        "source": r.get("source", "gpt"),
        "calibration_log": r.get("calibration_log", []),
        "self_consistency_applied": r.get("self_consistency_applied", False),
    }


async def batch_analyse(messages: list) -> list:
    """Analyse multiple messages concurrently."""
    tasks = [
        analyse_message(
            content=msg.get("content", ""),
            message_type=msg.get("message_type", "sms"),
            sender=msg.get("sender"),
        )
        for msg in messages
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        r if not isinstance(r, Exception) else DEFAULT_MEDIUM_RISK
        for r in results
    ]


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION (for dashboard accuracy widget)
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_model_performance() -> dict:
    """Run the labelled dataset and report accuracy / precision / recall."""
    dataset_path = os.path.join(
        os.path.dirname(__file__), "data", "nigerian_scam_dataset.json"
    )
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    samples = dataset.get("samples", [])
    if not samples:
        return {"error": "No samples available"}

    correct = 0
    tp = fp = tn = fn = 0
    score_diffs = []
    results = []

    for item in samples:
        result = await analyse_message(
            content=item["content"],
            message_type=item.get("message_type", "sms"),
        )
        expected_action = item.get("action")
        predicted_action = result["action"]
        is_correct = expected_action == predicted_action
        if is_correct:
            correct += 1

        expected_pos = expected_action == "BLOCK"
        predicted_pos = predicted_action == "BLOCK"
        if expected_pos and predicted_pos:
            tp += 1
        elif (not expected_pos) and (not predicted_pos):
            tn += 1
        elif (not expected_pos) and predicted_pos:
            fp += 1
        else:
            fn += 1

        score_diffs.append(abs(item.get("risk_score", 50) - result["risk_score"]))

        results.append({
            "id": item["id"],
            "category": item.get("category", "unknown"),
            "preview": item["content"][:80] + ("..." if len(item["content"]) > 80 else ""),
            "expected_action": expected_action,
            "predicted_action": predicted_action,
            "expected_score": item.get("risk_score"),
            "predicted_score": result["risk_score"],
            "correct": is_correct,
            "source": result.get("source", "gpt"),
        })

    total = len(samples)
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0

    return {
        "accuracy": round(correct / total * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1 * 100, 2),
        "mean_score_error": round(sum(score_diffs) / len(score_diffs), 2),
        "correct": correct,
        "total": total,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "results": results,
    }


def get_threat_level_from_score(score: float) -> str:
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    return "CLEAN"
