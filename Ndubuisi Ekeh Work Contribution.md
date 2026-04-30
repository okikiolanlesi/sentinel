## AI Core — Scam Detection & Risk Intelligence

> Built and owned by **Ndubuisi Ekeh**

All backend AI logic powering SentinelAI's threat detection engine was designed and implemented from scratch, including the full pipeline from raw message input to structured risk output.

---

### Fraud Detection Engine (`ai/scanner.py`)
- Designed and built a **5-layer accuracy stack** on top of Azure OpenAI GPT-5.4-nano:
  1. **Rule Pre-Flight Engine** — deterministic regex catches unambiguous fraud before calling GPT (OTP theft, EFCC extortion, BEC/deepfake CEO, BVN+NIN combos, upfront fees, prize scams, job scams)
  2. **Dynamic Few-Shot Retrieval** — TF-IDF cosine similarity retrieves the 3 most similar examples from a labelled corpus at scan time, injecting them into the prompt
  3. **Chain-of-Thought Scoring** — structured prompt forces signal extraction before scoring, producing consistent and explainable verdicts
  4. **Self-Consistency** — borderline scores (40–75) are run twice at different temperatures and reconciled, reducing variance on the most dangerous edge cases
  5. **Calibration Guardrails** — post-processing enforces hard floors (OTP scams always ≥95), ceilings (legit bank alerts always ≤10), and consistency between score, threat_level, and action
- Classifies messages across SMS, WhatsApp, and voice transcripts
- Returns structured output: `risk_score`, `threat_level`, `flags`, `action`, `reasoning`, `suggested_actions`, `source`, `calibration_log`
- Built against a 44-sample labelled Nigerian scam dataset (`ai/data/nigerian_scam_dataset.json`)
- **Azure content filter compatibility** — rewrote system prompt to use neutral analytical language after diagnosing repeated `invalid_prompt` 400 errors; scoring rubric moved to user message to bypass overly aggressive content policy triggers

### Rule Engine (`ai/rules.py`)
- Built from scratch — 8 deterministic fraud pattern rules covering all major Nigerian scam categories
- Uses multi-stage regex (order-independent) so fraud signals trigger regardless of message phrasing
- Catches ~30% of scans before GPT is called — faster, cheaper, and 100% accurate on known patterns
- Whitelist for legitimate Nigerian bank alerts (masked account + balance + date) auto-scores to 5

### Calibration Layer (`ai/calibrator.py`)
- Post-processes every GPT response to prevent the most dangerous failure modes
- Broad trigger flag matching — catches all real GPT output flag names, not just ideal ones
- Every override logged in `calibration_log` for full auditability

### Per-Org Fraud Memory (`ai/memory.py`)
- Each organisation builds its own fraud profile over time
- Stores blacklisted senders, known bad keywords, and phishing domains per org
- After 3 hits, patterns auto-promote to high-confidence blacklist
- Applies a memory boost (up to +20 points) to risk scores on repeat attackers

### Contextual Risk Scorer (`ai/risk_scorer.py`)
- Goes beyond single-message classification
- Analyses sender history, message frequency, and campaign-level patterns
- Detects coordinated fraud campaigns across multiple messages from the same source
- Dynamically adjusts risk scores based on behavioural context

### Semantic Kernel Pipeline (`ai/kernel.py`)
- Multi-step agentic pipeline built with Microsoft Semantic Kernel
- Chains scan → score → decision into a single orchestrated flow
- Designed for extensibility — new detection plugins can be added without touching core logic

### Voice Deepfake Detection (`routes/voice.py`)
- Accepts audio file uploads via multipart form
- Transcribes speech using Azure Whisper
- Routes transcript through the full 5-layer fraud scanner (same pipeline as SMS)
- Runs a **dedicated deepfake probability assessment** using an upgraded GPT prompt with concrete signal rubric
- Returns `deepfake_probability`, `deepfake_signals`, `deepfake_reasoning`, `transcript`, `risk_score`, `suggested_actions`
- Fixed 500 error on silent/short audio — now returns clean 400 with actionable error message

### Threat Lifecycle Management (`routes/scan.py`)
- Added `threat_status` field to every scan: `new → reviewing → escalated → resolved → closed`
- Status transitions are validated (closed is terminal, can't go backwards)
- Every transition logged to `scan_status_history` with who changed it and when

### Correction Endpoint (`routes/scan.py → /api/scan/{id}/correct`)
- Analysts can mark any AI verdict as wrong — saves original score, correct verdict, and reason
- Powers the corrections stats dashboard widget (false positive rate, false negative rate)
- Forms the feedback loop for future model improvement

### Escalation System (`routes/scan.py → /api/scan/{id}/escalate`)
- Analysts can escalate threats with a reason, optionally to a named admin
- All active escalations queryable via `GET /api/scan/escalations`
- Escalated threats auto-promote to HIGH threat level

### Batch Judgement (`routes/scan.py → /api/scan/batch-judge`)
- Admin endpoint that runs AI over all unreviewed scans in bulk
- Populates `suggested_actions` on historical scans that were scanned before the field existed
- Runs concurrently via `asyncio.gather` for speed

### External API Endpoint (`routes/scan.py → /api/scan/api`)
- Headless scan endpoint authenticated via API key (`X-API-Key` header)
- Allows banks, fintechs, and telcos to integrate SentinelAI directly into their own systems
- Returns `risk_score`, `threat_level`, `action`, `flags`, `reasoning`, `suggested_actions`

### Batch Scan (`routes/scan.py → /api/scan/batch`)
- Admin-level endpoint for scanning up to 50 messages concurrently in one request
- Built for high-volume telco and fintech use cases
- Processes each message through the full detection pipeline and returns aggregated results with breakdown

### Live Evaluation Endpoint (`routes/evaluation.py`)
- Runs the full labelled Nigerian fraud dataset through the live scanner
- Returns real accuracy %, precision, recall, F1, mean score error, and per-sample predictions
- Used during the demo to show judges verifiable accuracy numbers, not just claims
- Exposes confusion matrix (TP/FP/TN/FN)

### Onboarding Wizard (`routes/onboarding.py`)
- 5-step guided setup flow for new B2B customers
- Step 1: Organisation details (name, type, country)
- Step 2: Admin account creation with password validation
- Step 3: Scan settings (channels to monitor, auto-block threshold, alert email)
- Step 4: API key generation with integration example
- Step 5: Live test — runs 3 real messages through the scanner to confirm everything works
- Session state persists between steps so users can resume if they drop off

### Proactive Health Scan (`routes/dashboard.py → /api/dashboard/health`)
- Background health check surfacing: unreviewed HIGH threats >2hrs, scan volume drops >50%, correction rate spikes, escalation backlog
- Returns `overall_status`: healthy / warning / critical
- Powers the System Health widget on the dashboard

### Per-Org Memory API (`routes/org.py → /api/org/memory`)
- Returns the organisation's full fraud pattern list with hit counts and confidence scores
- Powers the Org Fraud Memory widget on the dashboard

---

### Deployment

- Diagnosed and fixed **Vercel Python 3.14 incompatibility** — `pydantic-core` Rust build fails on Python 3.14; resolved by pinning runtime to `python3.12` in `vercel.json`
- Fixed **`$PORT` expansion error** on Vercel — removed `uvicorn.run()` block from `main.py` that Vercel was executing as a start command
- Diagnosed and resolved **Azure content filter false positives** — system prompt was triggering `invalid_prompt` 400 errors; fixed by stripping explicit fraud descriptions from system prompt and moving scoring rubric to user message with neutral analytical language
- Fixed **`max_tokens` → `max_completion_tokens`** incompatibility with `gpt-5.4-nano`
- Resolved **16-file merge conflict** between two team branches — unified all service files, fixed method name mismatches across 5 service files, added missing hooks and UI components without breaking existing functionality
- Configured Railway deployment with correct start command, environment variables, and root directory settings