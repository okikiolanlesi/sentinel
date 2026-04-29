"""
SentinelAI — Deterministic Rule Pre-Flight Engine v2
=====================================================
Catches high-confidence fraud signals using regex BEFORE calling GPT.

Covers all major Nigerian scam categories:
  OTP theft, card theft, EFCC extortion, BEC/deepfake CEO, BVN+NIN combo,
  guaranteed investment ROI, advance fee (419), upfront loan fee,
  prize/lottery scams, job scams, phishing domains.
"""

import re
from typing import Optional, Dict, Any, List


CRITICAL_PATTERNS: List[Dict[str, Any]] = [

    # 1. OTP / PIN sharing — two-stage (verb anywhere + OTP noun anywhere)
    {
        "name": "otp_sharing_request",
        "share_verbs": re.compile(
            r"\b(share|send|give|tell|provide|forward|read[\s\-]?out|read[\s\-]?me"
            r"|enter|type|repeat|confirm|verify[\s\-]?with)\b", re.IGNORECASE),
        "otp_nouns": re.compile(
            r"\b(otp|one[\s\-]?time[\s\-]?password|verification[\s\-]?code"
            r"|auth[\s\-]?code|authentication[\s\-]?code|security[\s\-]?code"
            r"|this[\s\-]?code|the[\s\-]?code|pin|transaction[\s\-]?pin"
            r"|6[\s\-]?digit[\s\-]?code|4[\s\-]?digit[\s\-]?code)\b", re.IGNORECASE),
        "score": 99,
        "reason": "Direct request to share OTP/PIN — definitionally account takeover. "
                  "No legitimate bank or service ever asks customers to share OTP codes.",
        "category": "otp_theft",
        "two_stage": True,
    },

    # 2. Card credentials request
    {
        "name": "card_credentials_request",
        "pattern": re.compile(
            r"\b(send|share|give|provide|enter|type|read[\s\-]?out)\b[\s\S]{0,60}"
            r"\b(cvv|cvc|card[\s\-]?number|debit[\s\-]?card[\s\-]?details"
            r"|full[\s\-]?card[\s\-]?info|card[\s\-]?details|expiry[\s\-]?date)\b",
            re.IGNORECASE),
        "score": 99,
        "reason": "Request for card credentials (CVV/number/expiry). No legitimate "
                  "merchant or bank ever asks for these via SMS or voice.",
        "category": "card_theft",
    },

    # 3. EFCC / police extortion — 3 stages any order
    {
        "name": "law_enforcement_extortion",
        "stage_1": re.compile(
            r"\b(efcc|ndlea|police|interpol|icpc|customs|nigeria[\s\-]?police"
            r"|economic[\s\-]?and[\s\-]?financial[\s\-]?crimes)\b", re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(arrest|warrant|detain|prosecute|jail|imprison|charge|investigation)\b",
            re.IGNORECASE),
        "stage_3": re.compile(
            r"\b(pay|transfer|deposit|bond|fine|settlement|₦|ngn|naira|\$|usd|dollar)\b",
            re.IGNORECASE),
        "score": 98,
        "reason": "Law enforcement impersonation + arrest threat + payment demand. "
                  "EFCC/NDLEA/Police NEVER demand bond payments via SMS or phone.",
        "category": "government_impersonation",
        "multi_stage": True,
    },

    # 4. BEC / Deepfake CEO — 3 stages any order
    {
        "name": "bec_executive_secrecy",
        "stage_1": re.compile(
            r"\b(ceo|md|managing[\s\-]?director|chairman|director|boss"
            r"|chief[\s\-]?executive)\b", re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(transfer|wire|send|move|remit|pay)\b", re.IGNORECASE),
        "stage_3": re.compile(
            r"\b(don'?t tell|tell no one|keep (this )?(quiet|secret|confidential)"
            r"|between us|don'?t mention|do not (discuss|tell|share|inform)"
            r"|confidential|in confidence|under wraps)\b", re.IGNORECASE),
        "score": 97,
        "reason": "BEC/deepfake CEO fraud: executive impersonation + transfer + "
                  "secrecy instruction is the highest-risk combo in Nigerian corporate fraud.",
        "category": "bec_deepfake",
        "multi_stage": True,
    },

    # 5. BVN + NIN combo — 2 stages any order
    {
        "name": "bvn_nin_combo_request",
        "stage_1": re.compile(
            r"\b(bvn|bank[\s\-]?verification[\s\-]?number)\b", re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(nin|national[\s\-]?id|national[\s\-]?identification[\s\-]?number?)\b",
            re.IGNORECASE),
        "score": 96,
        "reason": "BVN + NIN together = complete identity theft kit. "
                  "Banks never request both via SMS.",
        "category": "identity_theft",
        "multi_stage": True,
    },

    # 6. Guaranteed investment / crypto ROI — 2 stages
    {
        "name": "guaranteed_investment_scam",
        "stage_1": re.compile(
            r"\b(guarantee[sd]?|doubl[eing]+|triple[sd]?|100%[\s\-]?roi"
            r"|risk[\s\-]?free[\s\-]?(return|profit|investment)"
            r"|guaranteed[\s\-]*(returns?|profits?|income)|no[\s\-]?risk)\b",
            re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(invest|crypto|forex|trading|bitcoin|platform|portfolio"
            r"|wallet|trade|roi|returns?|profit)\b", re.IGNORECASE),
        "score": 92,
        "reason": "Guaranteed investment returns are definitionally fraudulent. "
                  "Classic Nigerian crypto/forex investment scam.",
        "category": "investment_scam",
        "multi_stage": True,
    },

    # 7. Advance fee / unlock fee (419) — 3 stages
    {
        "name": "advance_fee_fraud",
        "stage_1": re.compile(
            r"\b(unlock|release|activate|claim|access|receive|collect|disburse"
            r"|process|clearance|tax[\s\-]?clearance)\b", re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(fee|charge|payment|processing|insurance|stamp[\s\-]?duty"
            r"|administrative|handling)\b", re.IGNORECASE),
        "stage_3": re.compile(
            r"\b(₦|ngn|naira|\$|usd|dollar|pay|transfer|deposit|send)\b",
            re.IGNORECASE),
        "score": 91,
        "reason": "Advance fee fraud (419): payment required to 'unlock' or 'release' "
                  "funds. No legitimate service requires fees to disburse money.",
        "category": "advance_fee_fraud",
        "multi_stage": True,
    },

    # 8. Loan upfront fee — 2 stages
    {
        "name": "loan_upfront_fee",
        "stage_1": re.compile(
            r"\b(loan|credit|borrow|lending|lender|funds?)\b", re.IGNORECASE),
        "stage_2": re.compile(
            r"\b(pay|deposit|transfer|send|remit)\b[\s\S]{0,80}"
            r"\b(fee|insurance|processing|activation|clearance|admin"
            r"|collateral[\s\-]?fee|first[\s\-]?payment)\b", re.IGNORECASE),
        "score": 90,
        "reason": "Loan scam: upfront fee required before disbursement. "
                  "All legitimate Nigerian lenders disburse first — they never "
                  "require payment before sending funds.",
        "category": "loan_scam",
        "multi_stage": True,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SUSPICIOUS DOMAIN / CONTACT PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

SUSPICIOUS_DOMAIN_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(gtb|gtbank)[\s\-]?(secure|verify|update|alert|reactivate|confirm)", re.I),
    re.compile(
        r"\b(access|zenith|firstbank|uba|fcmb|fidelity|sterling|polaris|wema"
        r"|stanbic|kuda|opay|palmpay|moniepoint)[\s\-]?(bank)?[\s\-]?"
        r"(secure|verify|update|alert|reactivate|confirm)", re.I),
    re.compile(r"\b(cbn|efcc|ndlea|nimc|frsc)[\s\-]?(verify|update|alert|portal|confirm)", re.I),
    re.compile(r"https?://[^\s]*\.(tk|ml|ga|cf|gq|xyz|click|link|info|biz)\b", re.I),
    re.compile(r"\bbit\.ly/|tinyurl\.com/|shorturl\.at/|rb\.gy/|cutt\.ly/", re.I),
    re.compile(
        r"\b(mtn|airtel|glo|9mobile|gtb|access|zenith|firstbank|uba|cbn|efcc|ndlea)"
        r"[^\s]*@(gmail|yahoo|hotmail|outlook|protonmail|yandex)\.com", re.I),
]

# PRIZE SCAM PATTERNS (single-stage, high-confidence)
PRIZE_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"\b(won|selected|chosen|winner|awarded|congratulations)\b[\s\S]{0,100}"
        r"\b(mtn|airtel|glo|9mobile|telco|anniversary|promo|lottery|raffle|draw)\b",
        re.I),
    re.compile(
        r"\b(claim|collect|receive)\b[\s\S]{0,60}"
        r"\b(prize|reward|winnings?|cash[\s\-]?prize|award)\b", re.I),
]

# JOB SCAM PATTERNS
JOB_SCAM_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"\b(earn|make|income|salary)\b[\s\S]{0,60}"
        r"\b(per\s+day|daily|per\s+hour|weekly)\b[\s\S]{0,80}"
        r"\b(home|online|remote|part[\s\-]?time|no[\s\-]?experience)\b", re.I),
    re.compile(
        r"(₦|ngn|\$)\s?[\d,]+[\s\S]{0,40}"
        r"\b(per\s+day|daily|per\s+hour)\b[\s\S]{0,60}"
        r"\b(home|online|remote|2\s+hours?|few\s+hours?)\b", re.I),
]

# LEGITIMATE BANK/TELCO TRANSACTION PATTERNS
LEGIT_TRANSACTION_PATTERNS: List[re.Pattern] = [
    # Masked account + balance
    re.compile(
        r"(acct|a/?c|account)[\s:]*[xX*]{2,}\d{3,4}[\s\S]{0,150}"
        r"(bal|balance)[\s:]*(₦|ngn|n)[\s]?[\d,]+\.?\d*", re.IGNORECASE),
    # Masked card/acct inline with debit/credit
    re.compile(
        r"[xX*]{2,}\d{3,4}[\s\S]{0,100}"
        r"(debit|credit|trf|transfer)[\s\S]{0,50}"
        r"(₦|ngn|n)[\s]?[\d,]+\.?\d*", re.IGNORECASE),
    # Standard debit/credit alert with date
    re.compile(
        r"(debit|credit|trf|transfer)[\s\S]{0,50}"
        r"(₦|ngn|n)[\s]?[\d,]+\.?\d*[\s\S]{0,100}"
        r"\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        re.IGNORECASE),
    # USSD codes
    re.compile(r"\*\d{2,4}#", re.IGNORECASE),
    # Airtime/data recharge confirmation
    re.compile(
        r"\b(recharge|recharged|airtime|data)\b[\s\S]{0,60}"
        r"\b(successful|confirmed|activated|added)\b", re.IGNORECASE),
]


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def apply_rules(content: str) -> Optional[Dict[str, Any]]:
    """
    Run rule engine. Returns:
      - Dict with skip_gpt=True  → hard verdict
      - Dict with skip_gpt=False → partial priors for GPT
      - None                     → proceed to GPT normally
    """
    text = content.strip()
    if not text:
        return None

    matched_flags: List[str] = []
    matched_reasons: List[str] = []
    max_score = 0
    category = "unknown"

    # Step 1: Critical patterns
    for rule in CRITICAL_PATTERNS:
        matched = False
        if rule.get("two_stage"):
            if rule["share_verbs"].search(text) and rule["otp_nouns"].search(text):
                matched = True
        elif rule.get("multi_stage"):
            stages = [v for k, v in sorted(rule.items()) if k.startswith("stage_")]
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

    # Step 2: Suspicious domain/contact blacklist
    domain_hits = sum(1 for p in SUSPICIOUS_DOMAIN_PATTERNS if p.search(text))
    if domain_hits > 0:
        domain_score = min(95, 60 + 15 * domain_hits)
        max_score = max(max_score, domain_score)
        if "suspicious_domain" not in matched_flags:
            matched_flags.append("suspicious_domain")
        if not matched_reasons:
            matched_reasons.append(
                f"{domain_hits} suspicious domain/contact pattern(s) matching "
                "known Nigerian phishing templates."
            )
        if category == "unknown":
            category = "phishing"

    # Step 3: Prize scam patterns
    prize_hits = sum(1 for p in PRIZE_PATTERNS if p.search(text))
    if prize_hits > 0:
        prize_score = min(95, 80 + prize_hits * 10)
        max_score = max(max_score, prize_score)
        matched_flags.append("prize_scam")
        matched_reasons.append(
            "Prize/lottery scam: unsolicited winnings from telco/promo. "
            "Legitimate telcos do not send SMS prize claims."
        )
        if category == "unknown":
            category = "prize_scam"

    # Step 4: Job scam patterns
    job_hits = sum(1 for p in JOB_SCAM_PATTERNS if p.search(text))
    if job_hits > 0:
        max_score = max(max_score, 90)
        matched_flags.append("job_scam")
        matched_reasons.append(
            "Job scam: unrealistic daily earnings with minimal hours/no experience. "
            "Consistent with money mule recruitment."
        )
        if category == "unknown":
            category = "job_scam"

    # Step 5: Hard verdict
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

    # Step 6: Legit whitelist (only if NO suspicious signals)
    if not matched_flags:
        for pat in LEGIT_TRANSACTION_PATTERNS:
            if pat.search(text):
                return {
                    "rule_matched": True,
                    "risk_score": 5.0,
                    "threat_level": "CLEAN",
                    "flags": [],
                    "action": "ALLOW",
                    "reasoning": "Matches standard Nigerian bank/telco transaction "
                                 "alert format. No fraud signals detected.",
                    "is_scam": False,
                    "scam_category": "none",
                    "source": "rule_engine",
                    "skip_gpt": True,
                }

    # Step 7: Partial match — pass priors to GPT
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
