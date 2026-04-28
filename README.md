# SentinelAI — Telecom Fraud Intelligence SaaS

> **TeKnowledge × Microsoft 2026 Agentic AI Hackathon**  
> Theme: *Trust, Safety & Fraud Intelligence in Telecom Networks*

AI-powered B2B platform that detects scams, fraud, and deepfake voices in real-time across SMS, WhatsApp, and phone calls. Built for banks, fintechs, telcos, and call centers.

---

## Demo credentials (default admin, auto-created on first run)

| Field | Value |
|---|---|
| Email | `admin@sentinelai.io` |
| Password | `SentinelAdmin2026!` |

---

## Quick start

### Backend

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your Azure credentials
cp .env.example .env
# Open .env and set AZURE_API_KEY (the only field you must fill in)

# 3. Run
uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

The default admin account (`admin@sentinelai.io`) is created automatically on first startup.

### Frontend

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Configure backend URL (optional for local dev — defaults to localhost:8000)
cp .env.example .env

# 3. Run
npm run dev
# → http://localhost:5173
```

---

## Architecture

```
sentinelai/
├── backend/
│   ├── main.py              ← FastAPI app, lifespan, CORS
│   ├── database.py          ← SQLAlchemy models (User, ScanResult, VoiceAnalysis, AuditLog)
│   ├── auth_utils.py        ← bcrypt, JWT, RBAC dependency factory
│   ├── requirements.txt
│   ├── .env.example
│   └── routes/
│   │   ├── auth.py          ← /api/auth/* (register, login, me, generate-key)
│   │   ├── scan.py          ← /api/scan/* (message, batch, history, evaluate, api)
│   │   ├── voice.py         ← /api/voice/* (analyse, history)
│   │   ├── dashboard.py     ← /api/dashboard/* (stats, threat-feed, trends, audit-log)
│   │   └── users.py         ← /api/users/* (list, invite, role, activate, me)
│   └── ai/
│       ├── scanner.py       ← GPT-5.4-nano few-shot fraud detection engine
│       ├── risk_scorer.py   ← Contextual risk scoring (sender history, campaign detection)
│       ├── kernel.py        ← Semantic Kernel multi-step pipeline
│       └── data/
│           └── nigerian_scam_dataset.json  ← 120-sample evaluation dataset
│
└── frontend/
    └── src/
        ├── services/        ← API layer (auth, scan, voice, dashboard, users)
        ├── store/           ← Zustand auth store (persisted JWT)
        ├── components/      ← ProtectedRoute, RiskBadge, ScoreBar
        ├── lib/             ← axios client, error helper, formatters
        └── features/
            ├── auth/        ← SignIn, SignUp pages + hooks
            ├── marketing/   ← Landing page
            └── dashboard/
                ├── DashboardLayout.tsx        ← Sidebar, role-aware nav
                └── pages/
                    ├── DashboardPage.tsx      ← KPIs + live threat feed
                    ├── ThreatsPage.tsx        ← Live scanner + scan history
                    ├── DeepfakePage.tsx       ← Audio upload + voice analysis history
                    ├── UserManagementPage.tsx ← Admin-only user CRUD + invite modal
                    ├── ProfilePage.tsx        ← Update name/org, synced to auth store
                    └── ApiKeysPage.tsx        ← Generate/rotate API key + curl example
```

---

## Tech stack

| Layer | Technology |
|---|---|
| AI model | Azure OpenAI GPT-5.4-nano (via Microsoft AI Foundry) |
| Voice | Azure Whisper (transcription) |
| AI orchestration | Microsoft Semantic Kernel |
| Backend | FastAPI + Python 3.12+ |
| Database | SQLite → Azure SQL (prod) |
| Auth | JWT + bcrypt + RBAC |
| Frontend | React 19, TypeScript, Vite |
| State | Zustand (persisted auth) |
| Data fetching | TanStack Query v5 |
| Forms | React Hook Form + Zod |
| UI | Tailwind CSS v4, shadcn-style components |
| HTTP | Axios with auto JWT injection |

---

## Role permissions

| Permission | Admin | Analyst | Viewer |
|---|---|---|---|
| View dashboard | ✓ | ✓ | ✓ |
| Run scans | ✓ | ✓ | ✗ |
| View scan history | ✓ | ✓ | ✗ |
| Voice analysis | ✓ | ✓ | ✗ |
| View user list | ✓ | ✗ | ✗ |
| Invite / manage users | ✓ | ✗ | ✗ |
| View audit log | ✓ | ✗ | ✗ |
| Generate API keys | ✓ | ✓ | ✓ |
| Batch scan | ✓ | ✗ | ✗ |

---

## Key API endpoints

### Auth
```
POST /api/auth/register  { email, password, full_name, organisation }
POST /api/auth/login     { email, password } → access_token
GET  /api/auth/me        → current user
POST /api/auth/generate-key → new API key
```

### Scan
```
POST /api/scan/message  { content, message_type, sender? }  [analyst+]
POST /api/scan/batch    { messages: [...] }                 [admin]
GET  /api/scan/history  ?threat_level&message_type&page     [analyst+]
GET  /api/scan/evaluate                                     [admin]
POST /api/scan/api      X-API-Key header (external endpoint)
```

### Voice
```
POST /api/voice/analyse   multipart/form-data (file)        [analyst+]
GET  /api/voice/history                                     [any auth]
```

### Dashboard
```
GET /api/dashboard/stats
GET /api/dashboard/threat-feed?limit
GET /api/dashboard/trends?days
GET /api/dashboard/audit-log                               [admin]
```

### Users
```
GET    /api/users                              [admin]
POST   /api/users/invite                       [admin]
PUT    /api/users/{id}/role?new_role=          [admin]
PUT    /api/users/{id}/deactivate              [admin]
PUT    /api/users/{id}/activate                [admin]
GET    /api/users/me
PUT    /api/users/me
```

---

## External API integration (for banks / telcos)

```bash
curl -X POST https://your-backend/api/scan/api \
  -H "X-API-Key: sk-sentinel-<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "URGENT: Verify your BVN at gtb-secure-verify.com",
    "message_type": "sms",
    "sender": "+2348030001234"
  }'

# → { "risk_score": 97, "threat_level": "HIGH", "action": "BLOCK", "flags": [...] }
```

---

## Team & module ownership

| Member | Module | Issues |
|---|---|---|
| Ndubuisi Ekeh | AI core — scam detection, risk scoring, Semantic Kernel | #1 #2 #3 #4 #7 |
| Olusegun Adelowo | Admin dashboard + KPI analytics UI | #14 #15 |
| Adedapo Adeniran | Auth system — login, RBAC, JWT | #5 #6 #7 |
| Okikiola Osunronbi | Database schema, logging, audit trail | #8 #9 |
| Abdul Samad Zen-Abdeen | Deepfake voice detection module | #10 #11 |
| Gbolahan Kolawole | User management module | #12 #13 |
| Ifunanya Ugwoke | Landing page, UI/UX, presentation | #16 #17 |

---

## Deployment (Railway — demo)

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
cd backend
railway init
railway up
# Copy the live URL → update VITE_API_URL in frontend/.env
```

Production backend URL goes in `frontend/.env`:
```
VITE_API_URL=https://your-backend.up.railway.app
```

Then build and deploy frontend:
```bash
cd frontend
npm run build
# Deploy dist/ to Vercel, Netlify, or Railway static
```
