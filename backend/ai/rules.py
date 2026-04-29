"""
SentinelAI — Deterministic Rule Pre-Flight Engine
==================================================
Catches high-confidence fraud signals using regex patterns BEFORE calling GPT.

WHY: GPT can hallucinate. Regex cannot. Some Nigerian fraud patterns are so
unambiguous (OTP sharing requests, known scam domains, EFCC impersonation +
payment demand) that we should never delegate them to a probabilistic model.

This layer:
  - Returns HARD VERDICTS (≥95 risk) for unambiguous fraud → skip GPT entirely
  - Returns HARD ALLOWS (≤10 risk) for clearly legitimate bank formats
  - Returns NONE for ambiguous cases → proceed to GPT analysis

Result: faster scans, lower cost, higher accuracy on known patterns.
"""

import re
from typing import Optional, Dict, Any, List


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL RULES — match = automatic SCAM (risk 95-99)
# ─────────────────────────────────────────────────────────────────────────────

CRITICAL_PATTERNS: List[Dict[str, Any]] = [
    {
        "name": "otp_sharing_request",
        # We use a 2-stage check (handled in _check_critical below) instead of a
        # single regex because Nigerian scams phrase OTP requests in many orders:
        #   "share your OTP"
        #   "your OTP is X. Share this code with us"
        #   "read out the verification code"
        #   "enter the PIN sent to you"
        # Single regexes miss many of these. We instead require BOTH a
        # share-verb AND an OTP/code-noun anywhere within the message.
        "share_verbs": re.compile(
            r"\b(share|send|give|tell|provide|forward|read[\s\-]?out|read[\s\-]?me|enter|type|repeat|confirm|verify[\s\-]?with)\b",
            re.IGNORECASE,
        ),
        "otp_nouns": re.compile(
            r"\b(otp|one[\s\-]?time[\s\-]?password|verification[\s\-]?code|"
            r"auth[\s\-]?code|authentication[\s\-]?code|security[\s\-]?code|"
            r"this[\s\-]?code|the[\s\-]?code|pin|transaction[\s\-]?pin|"
            r"6[\s\-]?digit[\s\-]?code|4[\s\-]?digit[\s\-]?code)\b",
            re.IGNORECASE,
        ),
        "score": 99,
        "reason": "Direct request to share OTP/PIN/verification code — definitionally "
                  "account takeover. No legitimate bank, telco, or service ever asks "
                  "customers to share OTP codes via SMS, voice, or chat.",
        "category": "otp_theft",
        "two_stage": True,
    },
    {
        "name": "card_credentials_request",
        "pattern": re.compile(
            r"\b(send|share|give|provide|enter|type|read[\s\-]?out)\b[\s\S]{0,60}"
            r"\b(cvv|cvc|card[\s\-]?number|debit[\s\-]?card[\s\-]?details|"
            r"full[\s\-]?card[\s\-]?info|card[\s\-]?details|expiry[\s\-]?date)\b",
            re.IGNORECASE,
        ),
        "score": 99,
        "reason": "Request for full card credentials (CVV/card number). No legitimate "
                  "merchant or bank ever asks for these via SMS or voice.",
        "category": "card_theft",
    },
    {
        "name": "law_enforcement_extortion",
        # 3-stage: agency name + arrest/warrant + payment demand (any order)
        "stage_1": re.compile(
            r"\b(efcc|ndlea|police|interpol|icpc|customs|nigeria[\s\-]?police|"
            r"economic[\s\-]?and[\s\-]?financial[\s\-]?crimes)\b",
            re.IGNORECASE,
        ),
        "stage_2": re.compile(
            r"\b(arrest|warrant|detain|prosecute|jail|imprison|charge|investigation)\b",
            re.IGNORECASE,
        ),
        "stage_3": re.compile(
            r"\b(pay|transfer|deposit|bond|fine|settlement|"
            r"₦|ngn|naira|\$|usd|dollar)\b",
            re.IGNORECASE,
        ),
        "score": 98,
        "reason": "Law enforcement impersonation combined with arrest threat and "
                  "payment demand. Nigerian agencies (EFCC, NDLEA, Police) NEVER "
                  "demand bond payments via SMS or phone.",
        "category": "government_impersonation",
        "multi_stage": True,
    },
    {
        "name": "bec_executive_secrecy",
        # 3-stage: executive title + transfer + secrecy
        "stage_1": re.compile(
            r"\b(ceo|md|managing[\s\-]?director|chairman|director|boss|"
            r"chief[\s\-]?executive)\b",
            re.IGNORECASE,
        ),
        "stage_2": re.compile(
            r"\b(transfer|wire|send|move|remit|pay)\b",
            re.IGNORECASE,
        ),
        "stage_3": re.compile(
            r"\b(don'?t tell|tell no one|keep (this )?(quiet|secret|confidential)|"
            r"between us|don'?t mention|do not (discuss|tell|share|inform)|"
            r"confidential|in confidence|under wraps)\b",
            re.IGNORECASE,
        ),
        "score": 97,
        "reason": "Business Email Compromise / deepfake CEO fraud pattern. "
                  "Executive impersonation + transfer request + secrecy instruction "
                  "is the highest-risk signature in Nigerian corporate fraud.",
        "category": "bec_deepfake",
        "multi_stage": True,
    },
    {
        "name": "bvn_nin_combo_request",
        # Asking for BVN + NIN together = identity theft kit (order-independent)
        "stage_1": re.compile(
            r"\b(bvn|bank[\s\-]?verification[\s\-]?number)\b",
            re.IGNORECASE,
        ),
        "stage_2": re.compile(
            r"\b(nin|national[\s\-]?id|national[\s\-]?identification[\s\-]?number?)\b",
            re.IGNORECASE,
        ),
        "score": 96,
        "reason": "Request for BVN and NIN together. This combination enables full "
                  "identity theft and unauthorised account opening. Banks never "
                  "request both via SMS.",
        "category": "identity_theft",
        "multi_stage": True,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-RISK DOMAIN BLACKLIST
# ─────────────────────────────────────────────────────────────────────────────
# Patterns commonly used by Nigerian phishing campaigns. Real banks use
# .com.ng, .ng, or their own brand domains — never look-alike subdomains.

SUSPICIOUS_DOMAIN_PATTERNS: List[re.Pattern] = [
    # Bank-impersonating domains
    re.compile(r"\b(gtb|gtbank)[\s\-]?(secure|verify|update|alert|reactivate)", re.I),
    re.compile(r"\b(access|zenith|firstbank|uba|fcmb|fidelity|sterling|polaris|wema|stanbic|kuda|opay|palmpay|moniepoint)[\s\-]?(bank)?[\s\-]?(secure|verify|update|alert|reactivate|confirm)", re.I),
    # Government-impersonating domains
    re.compile(r"\b(cbn|efcc|ndlea|nimc|frsc)[\s\-]?(verify|update|alert|portal|confirm)", re.I),
    # Generic credential-harvesting patterns
    re.compile(r"https?://[^\s]*\.(tk|ml|ga|cf|gq|xyz|click|link)\b", re.I),
    re.compile(r"\bbit\.ly/|tinyurl\.com/|t\.co/|shorturl\.at/", re.I),
    # Free email impersonating institutions
    re.compile(r"\b(mtn|airtel|glo|9mobile|gtb|access|zenith|firstbank|uba|cbn|efcc)[^\s]*@(gmail|yahoo|hotmail|outlook|protonmail)\.com", re.I),
]


# ─────────────────────────────────────────────────────────────────────────────
# LEGITIMATE BANK ALERT WHITELIST
# ─────────────────────────────────────────────────────────────────────────────
# These patterns indicate a real Nigerian bank transaction alert.
# When matched and no scam signals are present → CLEAN.

LEGIT_TRANSACTION_PATTERNS: List[re.Pattern] = [
    # Masked account + amount + balance
    re.compile(
        r"(acct|a/?c|account)[\s:]*[xX*]{2,}\d{3,4}[\s\S]{0,100}"
        r"(bal|balance)[\s:]*(₦|ngn|n)[\s]?[\d,]+\.?\d*",
        re.IGNORECASE,
    ),
    # Standard debit/credit alert format
    re.compile(
        r"(debit|credit|trf|transfer)[\s\S]{0,50}"
        r"(₦|ngn|n)[\s]?[\d,]+\.?\d*[\s\S]{0,100}"
        r"\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        re.IGNORECASE,
    ),
    # USSD-style notification (always legitimate channel)
    re.compile(r"\*\d{2,4}#", re.IGNORECASE),
]


# ─────────────────────────────────────────────────────────────────────────────
# RULE ENGINE ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def apply_rules(content: str) -> Optional[Dict[str, Any]]:
    """
    Run the rule engine against a message.

    Returns:
        - Dict with verdict if a hard rule matched (skip GPT)
        - None if message is ambiguous (proceed to GPT)
    """
    text = content.strip()
    if not text:
        return None

    matched_flags: List[str] = []
    matched_reasons: List[str] = []
    max_score = 0
    category = "unknown"

    # 1. Critical patterns — these are unambiguous fraud
    for rule in CRITICAL_PATTERNS:
        matched = False
        if rule.get("two_stage"):
            # Both share-verb AND otp-noun must be present anywhere in the text
            if rule["share_verbs"].search(text) and rule["otp_nouns"].search(text):
                matched = True
        elif rule.get("multi_stage"):
            # All defined stage_N patterns must each appear (order-independent)
            stages = [v for k, v in rule.items() if k.startswith("stage_")]
            if all(p.search(text) for p in stages):
                matched = True
        elif "pattern" in rule:
            if rule["pattern"].search(text):
                matched = True

        if matched:
            matched_flags.append(rule["name"])
            matched_reasons.append(rule["reason"])
            if rule["score"] > max_score:
                max_score = rule["score"]
                category = rule["category"]

    # 2. Suspicious domain blacklist
    domain_hits = 0
    for pat in SUSPICIOUS_DOMAIN_PATTERNS:
        if pat.search(text):
            domain_hits += 1
            matched_flags.append("suspicious_domain")
    if domain_hits > 0:
        # Each suspicious domain adds 30 to the floor score
        max_score = max(max_score, min(95, 60 + 15 * domain_hits))
        if not matched_reasons:
            matched_reasons.append(
                f"{domain_hits} suspicious domain(s) detected matching known "
                f"phishing patterns (look-alike bank/government domains)."
            )
        if category == "unknown":
            category = "phishing"

    # If we matched anything critical, return a hard verdict
    if max_score >= 90:
        return {
            "rule_matched": True,
            "risk_score": float(max_score),
            "threat_level": "HIGH",
            "flags": list(set(matched_flags)),
            "action": "BLOCK",
            "reasoning": " | ".join(matched_reasons),
            "is_scam": True,
            "scam_category": category,
            "source": "rule_engine",
            "skip_gpt": True,
        }

    # 3. Legitimate transaction whitelist — only apply if NO suspicious signals
    # were detected at all
    if not matched_flags:
        for pat in LEGIT_TRANSACTION_PATTERNS:
            if pat.search(text):
                return {
                    "rule_matched": True,
                    "risk_score": 5.0,
                    "threat_level": "CLEAN",
                    "flags": [],
                    "action": "ALLOW",
                    "reasoning": "Matches standard Nigerian bank transaction "
                                 "alert format (masked account + amount + balance "
                                 "or USSD code). No scam signals detected.",
                    "is_scam": False,
                    "scam_category": "none",
                    "source": "rule_engine",
                    "skip_gpt": True,
                }

    # If suspicious signals were found but didn't reach hard-verdict threshold,
    # return them as PRIORS to inform GPT — don't skip.
    if matched_flags:
        return {
            "rule_matched": True,
            "risk_score": float(max_score),
            "flags": list(set(matched_flags)),
            "reasoning": " | ".join(matched_reasons),
            "source": "rule_engine_partial",
            "skip_gpt": False,
            "priors": {
                "min_score": float(max_score),
                "flags": list(set(matched_flags)),
            },
        }

    return None
