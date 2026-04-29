"""
SentinelAI — Calibration Guardrails
====================================
Post-processes GPT output to prevent obvious mistakes.

WHY: Even with great prompts, GPT occasionally:
  - Under-scores OTP-sharing requests (must always be ≥ 95)
  - Over-scores standard bank alerts (must always be ≤ 15 if format matches)
  - Gives inconsistent threat_level for the score (e.g. score=92, level="MEDIUM")

This module applies hard, deterministic rules AFTER GPT to enforce floors,
ceilings, and consistency. Every override is logged so we have a transparent
audit trail.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Hard floors: signals that MUST result in at least this score
SCORE_FLOORS: List[Dict[str, Any]] = [
    {
        "trigger_flags": ["otp_sharing_request", "otp_theft", "credential_theft"],
        "min_score": 95,
        "reason": "OTP sharing request → forced minimum 95",
    },
    {
        "trigger_flags": ["bec_pattern", "executive_impersonation", "deepfake_likely"],
        "min_score": 90,
        "reason": "BEC / executive impersonation → forced minimum 90",
    },
    {
        "trigger_flags": ["law_enforcement_impersonation", "extortion", "arrest_threat"],
        "min_score": 92,
        "reason": "Law enforcement extortion → forced minimum 92",
    },
    {
        "trigger_flags": ["fake_domain", "bank_impersonation"],
        "min_score": 85,
        "reason": "Fake domain + bank impersonation → forced minimum 85",
    },
]


# Threat level thresholds (must be consistent with risk_score)
def _threat_level_for_score(score: float) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    if score >= 20:
        return "LOW"
    return "CLEAN"


def _action_for_score(score: float) -> str:
    if score >= 80:
        return "BLOCK"
    if score >= 50:
        return "REVIEW"
    return "ALLOW"


# Pattern: legitimate Nigerian bank alert format (masked acct + amount + balance)
LEGIT_BANK_FORMAT = re.compile(
    r"(acct|a/?c|account)[\s:]*[xX*]{2,}\d{3,4}[\s\S]{0,150}"
    r"(bal|balance)[\s:]*(₦|ngn|n)[\s]?[\d,]+\.?\d*",
    re.IGNORECASE,
)


def calibrate(
    ai_result: Dict[str, Any],
    original_message: str,
    rule_priors: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Apply post-processing guardrails to GPT output.

    Args:
        ai_result: Raw output from GPT analysis
        original_message: The message that was analysed (for whitelist checks)
        rule_priors: Optional priors from the rule engine (min_score, flags)

    Returns:
        Calibrated result with all overrides logged in `calibration_log`
    """
    result = dict(ai_result)  # don't mutate input
    score = float(result.get("risk_score", 50))
    flags = list(result.get("flags", []))
    log: List[str] = []

    # ── Step 1: Apply rule-engine priors (floors from regex layer) ──
    if rule_priors:
        prior_min = float(rule_priors.get("min_score", 0))
        prior_flags = rule_priors.get("flags", [])
        if prior_min > score:
            log.append(
                f"Floor applied: rule engine detected {prior_flags}, "
                f"raised score {score:.0f} → {prior_min:.0f}"
            )
            score = prior_min
        for f in prior_flags:
            if f not in flags:
                flags.append(f)

    # ── Step 2: Flag-based score floors ──
    flags_lower = [str(f).lower() for f in flags]
    for floor in SCORE_FLOORS:
        if any(t.lower() in flags_lower for t in floor["trigger_flags"]):
            if score < floor["min_score"]:
                log.append(
                    f"{floor['reason']} (was {score:.0f}, now {floor['min_score']})"
                )
                score = floor["min_score"]

    # ── Step 3: Whitelist override for legitimate bank alerts ──
    # Only kicks in if no scam-indicating flags are present
    danger_flags = {
        "otp_sharing_request", "fake_domain", "bank_impersonation",
        "executive_impersonation", "law_enforcement_impersonation",
        "credential_theft", "bec_pattern", "phishing", "card_theft",
    }
    has_danger_flag = any(f.lower() in danger_flags for f in flags_lower)

    if not has_danger_flag and LEGIT_BANK_FORMAT.search(original_message):
        if score > 20:
            log.append(
                f"Whitelist applied: legitimate bank alert format detected, "
                f"capped score {score:.0f} → 10"
            )
            score = 10
            flags = []

    # ── Step 4: Hard bounds ──
    score = max(0.0, min(100.0, score))

    # ── Step 5: Enforce threat_level / action consistency with score ──
    expected_level = _threat_level_for_score(score)
    expected_action = _action_for_score(score)

    if result.get("threat_level") != expected_level:
        log.append(
            f"Threat level corrected: {result.get('threat_level')} → {expected_level} "
            f"(score={score:.0f})"
        )
        result["threat_level"] = expected_level

    if result.get("action") != expected_action:
        log.append(
            f"Action corrected: {result.get('action')} → {expected_action} "
            f"(score={score:.0f})"
        )
        result["action"] = expected_action

    # ── Step 6: is_scam consistency ──
    is_scam = score >= 50
    if bool(result.get("is_scam", False)) != is_scam:
        log.append(f"is_scam corrected: {result.get('is_scam')} → {is_scam}")
        result["is_scam"] = is_scam

    result["risk_score"] = score
    result["flags"] = flags
    if log:
        result["calibration_log"] = log
        logger.info(f"Calibration applied: {log}")

    return result
