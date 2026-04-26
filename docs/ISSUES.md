# SentinelAI — Issue Tracker

## Module Ownership

| Issue | Module | Owner | Status |
|-------|--------|-------|--------|
| #1 | Database Models (User, ScanResult, VoiceAnalysis, AuditLog) | Ekeh Ndubuisi | ✅ Complete |
| #2 | JWT Authentication & bcrypt password hashing | Ekeh Ndubuisi | ✅ Complete |
| #3 | API Key generation & constant-time validation | Ekeh Ndubuisi | ✅ Complete |
| #4 | Scam Message Detection Engine (GPT-5.4-nano) | Ekeh Ndubuisi | ✅ Complete |
| #5 | Nigerian Fraud Pattern System Prompt | Ekeh Ndubuisi | ✅ Complete |
| #6 | Contextual Risk Scorer (sender history, campaign detection) | Ekeh Ndubuisi | ✅ Complete |
| #7 | Voice/Deepfake Analysis with Azure Whisper | Ekeh Ndubuisi | ✅ Complete |
| #8 | Semantic Kernel Orchestration | Ekeh Ndubuisi | ✅ Complete |
| #9 | Admin Dashboard UI | Olusegun Adelowo | ✅ Complete |
| #10 | Authentication Frontend | Adedapo Adeniran | ✅ Complete |
| #11 | Data Layer | Okikiola Osunronbi | ✅ Complete |
| #12 | Deepfake Module Support | Abdul Samad Zen-Abdeen | ✅ Complete |
| #13 | User Management | Gbolahan Kolawole | ✅ Complete |
| #14 | UI/UX & Frontend Polish | Ifunanya Ugwoke | ✅ Complete |

---

## Setup & Installation

```bash
# Clone repository
git clone https://github.com/okikiolanlesi/sentinel.git
cd sentinel/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Run server
uvicorn main:app --reload

# API documentation available at:
# http://localhost:8000/docs
```

---

## Default Admin Credentials

On first run, a default admin account is created automatically:
- **Email:** admin@sentinelai.io
- **Password:** SentinelAdmin2026!

---

## External API Integration Example

```python
import requests

response = requests.post(
    "https://api.sentinelai.io/api/scan/api",
    headers={"X-API-Key": "sk-sentinel-your-key-here"},
    json={
        "content": "URGENT: Your GTBank account is suspended. Click gtb-verify.com",
        "message_type": "sms",
        "sender": "+2348030001234"
    }
)

print(response.json())
# {
#   "risk_score": 94,
#   "threat_level": "HIGH",
#   "action": "BLOCK",
#   "flags": ["urgency_tactics", "fake_domain", "bank_impersonation"]
# }
```

---

## Team

| Name | Role |
|------|------|
| Ekeh Ndubuisi | AI Core, Backend Architecture, Semantic Kernel, Auth, Scan Engine, Voice Analysis |
| Olusegun Adelowo | Admin Dashboard UI |
| Adedapo Adeniran | Authentication Frontend |
| Okikiola Osunronbi | Data Layer |
| Abdul Samad Zen-Abdeen | Deepfake Module Support |
| Gbolahan Kolawole | User Management |
| Ifunanya Ugwoke | UI/UX & Frontend Polish |

---

## Built With

- Microsoft Azure OpenAI (GPT-5.4-nano, Whisper)
- Microsoft Semantic Kernel
- Microsoft AI Foundry
- FastAPI
- SQLAlchemy
