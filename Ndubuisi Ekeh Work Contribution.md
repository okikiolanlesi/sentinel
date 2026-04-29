## AI Core — Scam Detection & Risk Intelligence

> Built and owned by **Ndubuisi Ekeh**

All backend AI logic powering SentinelAI's threat detection engine was designed and implemented from scratch, including the full pipeline from raw message input to structured risk output.

### Fraud Detection Engine (`ai/scanner.py`)
- Few-shot GPT-4 nano prompt pipeline fine-tuned on Nigerian scam patterns
- Classifies messages across SMS, WhatsApp, and voice transcripts
- Returns structured output: `risk_score`, `threat_level`, `flags`, `action`, `explanation`
- Trained against a 120-sample Nigerian scam dataset (`ai/data/nigerian_scam_dataset.json`)

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
- Runs transcript through GPT fraud analysis to detect deepfake indicators and social engineering patterns
- Returns `deepfake_probability`, `transcript`, `risk_assessment`

### External API Endpoint (`routes/scan.py → /api/scan/api`)
- Headless scan endpoint authenticated via API key (`X-API-Key` header)
- Allows banks, fintechs, and telcos to integrate SentinelAI directly into their own systems
- Returns `risk_score`, `threat_level`, `action`, and `flags` in a single response

### Batch Scan (`routes/scan.py → /api/scan/batch`)
- Admin-level endpoint for scanning multiple messages in one request
- Built for high-volume telco and fintech use cases
- Processes each message through the full detection pipeline and returns aggregated results

### DeployMent ###

- Also Handled the deployment of both frontend and backend