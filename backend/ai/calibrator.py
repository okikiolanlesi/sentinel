"""
SentinelAI — Calibration Guardrails v2
=======================================
Post-processes GPT output to prevent mistakes.

Key fix in v2: trigger flags now match ACTUAL GPT output flag names,
not just the ideal ones. GPT often outputs "impersonation" not
"executive_impersonation" — both now trigger the same floor.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Score floors — ANY matching flag triggers the floor
SCORE_FLOORS: List[Dict[str, Any]] = [
    {
        "trigger_flags": [
            "otp_sharing_request", "otp_theft", "credential_theft",
            "otp_request", "otp_sharing", "otp",
        ],
        "min_score": 95,
        "reason": "OTP sharing/theft → forced minimum 95",
    },
    {
        "trigger_flags": [
            "bec_pattern", "executive_impersonation", "deepfake_likely",
            "bec_executive_secrecy", "bec_deepfake", "ceo_fraud",
            "executive_fraud", "impersonation_transfer", "transfer_secrecy",
        ],
        "min_score": 90,
        "reason": "BEC / executive impersonation → forced minimum 90",
    },
    {
        "trigger_flags": [
            "law_enforcement_impersonation", "extortion", "arrest_threat",
            "law_enforcement_extortion", "government_impersonation",
            "efcc_impersonation", "police_impersonation", "false_authority",
            "payment_demand", "arrest",
        ],
        "min_score": 92,
        "reason": "Law enforcement extortion → forced minimum 92",
    },
    {
        "trigger_flags": [
            "fake_domain", "bank_impersonation", "phishing_domain",
            "suspicious_domain", "phishing",
        ],
        "min_score": 82,
        "reason": "Fake domain + bank impersonation → forced minimum 82",
    },
    {
        "trigger_flags": [
            "guaranteed_investment_scam", "guaranteed_returns",
            "investment_scam", "crypto_scam", "forex_scam",
            "guaranteed_roi", "ponzi",
        ],
        "min_score": 85,
        "reason": "Guaranteed investment scam → forced minimum 85",
    },
    {
        "trigger_flags": [
            "advance_fee_fraud", "advance_fee", "419", "upfront_fee",
            "unlock_fee", "release_fee",
        ],
        "min_score": 85,
        "reason": "Advance fee (419) fraud → forced minimum 85",
    },
    {
        "trigger_flags": [
            "loan_upfront_fee", "loan_scam", "upfront_fee_request",
            "unsolicited_loan", "fake_loan",
        ],
        "min_score": 80,
        "reason": "Loan upfront fee scam → forced minimum 80",
    },
    {
        "trigger_flags": [
            "prize_scam", "lottery_fraud", "telco_impersonation",
            "prize_fraud", "lottery_scam", "fake_prize",
        ],
        "min_score": 80,
        "reason": "Prize/lottery scam → forced minimum 80",
    },
    {
        "trigger_flags": [
            "job_scam", "money_mule", "recruitment_scam",
            "unrealistic_income_promise",
        ],
        "min_score": 80,
        "reason": "Job/money mule scam → forced minimum 80",
    },
]


def _threat_level_for_score(score: float) -> str:
    if score >= 80: return "HIGH"
    if score >= 50: return "MEDIUM"
    if score >= 20: return "LOW"
    return "CLEAN"


def _action_for_score(score: float) -> str:
    if score >= 80: return "BLOCK"
    if score >= 50: return "REVIEW"
    return "ALLOW"


# Legit bank format patterns for whitelist
LEGIT_BANK_FORMATS: List[re.Pattern] = [
    re.compile(
        r"(acct|a/?c|account)[\s:]*[xX*]{2,}\d{3,4}[\s\S]{0,150}"
        r"(bal|balance)[\s:]*(₦|ngn|n)[\s]?[\d,]+\.?\d*", re.IGNORECASE),
    re.compile(
        r"[xX*]{2,}\d{3,4}[\s\S]{0,100}"
        r"(debit|credit)[\s\S]{0,50}(₦|ngn|n)[\s]?[\d,]+\.?\d*", re.IGNORECASE),
]

DANGER_FLAGS = {
    "otp_sharing_request", "otp_theft", "otp_request", "otp",
    "fake_domain", "bank_impersonation", "phishing", "phishing_domain",
    "executive_impersonation", "law_enforcement_impersonation",
    "credential_theft", "bec_pattern", "card_theft", "bec_executive_secrecy",
    "suspicious_domain", "law_enforcement_extortion",
}


def calibrate(
    ai_result: Dict[str, Any],
    original_message: str,
    rule_priors: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Apply post-processing guardrails to GPT output."""
    result = dict(ai_result)
    score = float(result.get("risk_score", 50))
    flags = list(result.get("flags", []))
    log: List[str] = []

    # Step 1: Apply rule-engine priors
    if rule_priors:
        prior_min = float(rule_priors.get("min_score", 0))
        prior_flags = rule_priors.get("flags", [])
        if prior_min > score:
            log.append(f"Rule prior raised score {score:.0f} → {prior_min:.0f} "
                       f"(flags: {prior_flags})")
            score = prior_min
        for f in prior_flags:
            if f not in flags:
                flags.append(f)

    # Step 2: Flag-based score floors
    flags_lower = {str(f).lower() for f in flags}
    for floor in SCORE_FLOORS:
        if any(t.lower() in flags_lower for t in floor["trigger_flags"]):
            if score < floor["min_score"]:
                log.append(f"{floor['reason']} (was {score:.0f} → {floor['min_score']})")
                score = floor["min_score"]

    # Step 3: Whitelist for legitimate bank alerts (only if no danger flags)
    has_danger = bool(flags_lower & {f.lower() for f in DANGER_FLAGS})
    if not has_danger:
        for pat in LEGIT_BANK_FORMATS:
            if pat.search(original_message):
                if score > 20:
                    log.append(f"Whitelist: legit bank alert, capped {score:.0f} → 8")
                    score = 8
                    flags = []
                break

    # Step 4: Hard bounds
    score = max(0.0, min(100.0, score))

    # Step 5: Enforce threat_level / action consistency
    expected_level = _threat_level_for_score(score)
    expected_action = _action_for_score(score)

    if result.get("threat_level") != expected_level:
        log.append(f"threat_level corrected: {result.get('threat_level')} → {expected_level}")
        result["threat_level"] = expected_level

    if result.get("action") != expected_action:
        log.append(f"action corrected: {result.get('action')} → {expected_action}")
        result["action"] = expected_action

    # Step 6: is_scam consistency
    is_scam = score >= 50
    if bool(result.get("is_scam", False)) != is_scam:
        log.append(f"is_scam corrected: {result.get('is_scam')} → {is_scam}")
        result["is_scam"] = is_scam

    result["risk_score"] = score
    result["flags"] = flags
    if log:
        result["calibration_log"] = log
        logger.info(f"Calibration: {log}")

    return result
