# AI Job Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI: 0.110+](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js: 14](https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript: 5.6](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL / pgvector](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-161%20Passing-success.svg)]()

> A production-grade, compliance-first, AI-driven job search, resume intelligence, deterministic match scoring, automated application tracking, mailbox integration, and recruiter communication copilot.

---

## Safety & Compliance Rule

> [!IMPORTANT]
> **Strict Non-Circumvention Policy**:
> The application strictly prohibits bypassing CAPTCHA, anti-bot protections, authentication systems, rate limits, or platform restrictions.
> 
> All sources enforce a formal connector capability status:
> - `SUPPORTED_AUTO_APPLY`: Direct authorized API integration (e.g. Greenhouse/Lever partner endpoints, mock provider).
> - `SUPPORTED_JOB_DISCOVERY_ONLY`: Official discovery feeds; applications directed to authorized candidate portal.
> - `EXTERNAL_APPLICATION_REQUIRED`: Manual application submission on employer website required.
> - `NOT_SUPPORTED`: Disallowed or non-compliant source.

---

## 1. System Architecture

```
                               INTERNET (HTTPS)
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
             Frontend (Next.js 14)         Backend (FastAPI)
             [Vercel / Cloudflare]         [Railway / Render / VPS]
                       │                             │
                       │                      ┌──────┴──────────────┐
                       ▼                      ▼                     ▼
             Browser Client         PostgreSQL (Managed)      Worker Daemon
             (User JWT Session)     (pgvector, Pooling)      (Leasing, DLQ)
                                              │
                               ┌──────────────┴──────────────┐
                               ▼                             ▼
                        OmniRoute Gateway            Mailbox OAuth APIs
                        (AI Orchestration)          (Gmail & Outlook)
```

---

## 2. Core Capabilities & Phased Evolution

### 1. Foundation & Security (Phase 1)
- **FastAPI** backend with asynchronous architecture and **SQLAlchemy 2.0** engine.
- Direct **Bcrypt** password hashing and **JWT** session authentication.
- Sliding window in-memory rate limiting middleware with `X-Request-ID` tracing.
- Structured request logging with automated header and secret sanitization.

### 2. Resume Intelligence (Phase 2)
- Multi-format resume parsing for **PDF** and **DOCX** with deep text extraction.
- Automatic categorization across 6 skill dimensions: Languages, Frameworks, Cloud, Databases, Tools, and Methodologies.
- Structured candidate profile synchronization with manual overrides and versioning.

### 3. Job Discovery Engine (Phase 3)
- Unified job ingestion pipeline across 10 platform connectors:
  - **Naukri**, **Indeed**, **Unstop**, **LinkedIn**, **Internshala**, **Wellfound**, **Company Career Pages**, **Greenhouse**, **Lever**, and **Mock ATS**.
- Real-time SHA-256 deduplication and multi-filter criteria (location, remote, experience, salary).

### 4. AI Matching Engine + OmniRoute (Phase 4)
- **6-Dimension Deterministic Scoring**:
  - Skills (35%), Experience (20%), Education (15%), Location (10%), Role (10%), Salary (10%).
- Eligibility evaluation ensuring critical job requirements are met.
- Vector embedding semantic matching powered by **OmniRoute AI Gateway** with deterministic mathematical fallback.

### 5. Context-Aware AI Chatbot (Phase 5)
- Conversational copilot equipped with tool-augmented workflows.
- Queries user resumes, job recommendations, matches, and application statuses in real time.
- Multi-turn context filtering, prompt injection defense, and cross-user isolation.

### 6. Automated Application Engine (Phase 6)
- Finite State Machine tracking application lifecycles from queue to submission.
- Strict policy engine evaluating match scores, daily limits, and per-company thresholds.
- Idempotent submission processing with exponential backoff and transient failure retry.

### 7. Mailbox OAuth Integration (Phase 7)
- **OAuth 2.0** integrations for **Gmail** and **Microsoft Outlook**.
- AES-256 / Fernet token encryption at rest for OAuth credentials.
- AI-powered email classification: Job Offers, Interview Invitations, Technical Assessments, Rejections, and Newsletters.
- HTML sanitization and XSS prevention for incoming message rendering.

### 8. Recruiter AI & Communication Intelligence (Phase 8)
- Human-in-the-loop response drafting across multiple tones (Professional, Enthusiastic, Inquiring).
- Automated interview preparation brief generation with company research and anticipated questions.
- Comprehensive Recruiter CRM with stage tracking and ghosting detection heuristics.

### 9. Production Hardening (Phase 9)
- Secret scanner redacting tokens, keys, and credentials from logs and audit events.
- Dead-letter queue (DLQ) routing for failed items with manual triage capabilities.
- Distributed queue leasing with 300s expiration and automatic crash recovery.
- Strict IDOR prevention across all endpoints.

### 10. Real User Setup (Phase 10)
- Multi-step onboarding wizard for new candidate setup.
- Candidate profile review and editing studio.
- AI provider connection diagnostics and telemetry dashboard.

### 11. Live Production Deployment (Phase 11)
- Dynamic host and `$PORT` binding for containerized cloud environments (Railway, Render, Fly.io).
- Production-hardened Next.js standalone build with enterprise HTTP security headers.
- Multi-service deployment definitions: `railway.toml`, `render.yaml`, `Dockerfile`, `Dockerfile.worker`, and `docker-compose.prod.yml`.
- Standalone background worker daemon (`worker.py`) with OS signal handling.

---

## 3. Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, Pydantic Settings, Uvicorn |
| **Database** | PostgreSQL 16 with pgvector extension, SQLAlchemy 2.0 (Async), aiosqlite (Dev) |
| **AI Gateway** | OmniRoute (OpenAI-compatible), OpenAI GPT-4o, Gemini 1.5 Flash, Anthropic Claude |
| **Auth & Security** | JWT (python-jose), Passlib (Bcrypt), Cryptography (Fernet) |
| **Parsing & Files** | PyMuPDF (PDF), python-docx (DOCX), pypdf |
| **Orchestration** | Docker, Docker Compose, Railway, Render Blueprint |

---

## 4. Repository Structure

```
ai-job-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application with CORS, logging, routes
│   │   ├── core/                       # Config, security, middleware, exceptions
│   │   ├── database/                   # Base models, engine, session management
│   │   ├── modules/
│   │   │   ├── auth/                   # Authentication & user profile endpoints
│   │   │   ├── resume/                 # Document parsing & skill extraction
│   │   │   ├── jobs/                   # Job discovery & aggregation
│   │   │   ├── matching/               # 6-Dimension matching engine
│   │   │   ├── applications/           # Application state machine & queue leasing
│   │   │   ├── mailbox/                # Gmail & Outlook OAuth integration
│   │   │   ├── communication/          # Recruiter CRM & interview prep
│   │   │   ├── chat/                   # AI conversational copilot
│   │   │   ├── connectors/             # 10 Platform connectors & health monitor
│   │   │   └── system/                 # Diagnostics, onboarding, health probes
│   ├── tests/                          # 161 automated test suites (100% pass)
│   ├── scripts/                        # Production audit scripts
│   ├── worker.py                       # Standalone background worker daemon
│   ├── Dockerfile                      # Backend web service container
│   ├── Dockerfile.worker               # Worker daemon container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                        # 23 Next.js pages & dynamic routes
│   │   ├── components/                 # UI components, layout, metrics
│   │   ├── lib/                        # Typed API client
│   │   └── types/                      # TypeScript domain definitions
│   ├── scripts/                        # Frontend production auditor
│   ├── next.config.js                  # Standalone output & security headers
│   ├── Dockerfile                      # Next.js production multi-stage runner
│   └── package.json
├── docs/                               # Architecture and deployment manuals
├── docker-compose.prod.yml             # Self-hosted production stack
├── railway.toml                        # Railway deployment manifest
├── render.yaml                         # Render Blueprint infrastructure-as-code
└── .env.example                        # Production environment configuration template
```

---

## 5. Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Prashant3804/ai-job-assistant.git
cd ai-job-assistant
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation is accessible at `http://localhost:8000/docs`.

### 3. Background Worker Setup (Optional for Auto-Apply / Schedulers)
In a separate terminal:
```bash
cd backend
python worker.py
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend dashboard is accessible at `http://localhost:3000`.

---

## 6. Live Production Deployment

Detailed production deployment instructions are provided in [docs/deployment.md](docs/deployment.md).

### Quick Summary of Options:

- **Railway**: Deploy directly using `railway.toml`.
- **Render**: One-click blueprint setup via `render.yaml` (PostgreSQL + Web Service + Worker + Frontend).
- **Vercel + Railway**: Deploy frontend to Vercel and backend to Railway.
- **Docker Compose**: Single-server self-hosting via:
  ```bash
  docker compose -f docker-compose.prod.yml up -d --build
  ```

---

## 7. Testing & Verification

Run the comprehensive test suite verifying all 11 phases:

```bash
# Backend test suite (161 tests)
cd backend
python -m pytest tests/ -v

# Production environment audit
python scripts/verify_production.py

# Frontend validation
cd ../frontend
npx tsc --noEmit
npm run lint
npm run verify:production
npm run build
```

---

## 8. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
