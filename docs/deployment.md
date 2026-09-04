# AI Job Assistant — Live Production Deployment Guide

## 1. Production Architecture Overview

```
                          INTERNET (HTTPS)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
       Frontend (Next.js)              Backend (FastAPI)
       [Vercel / Cloudflare]          [Railway / Render / VPS]
                 │                             │
                 │                      ┌──────┴──────────────┐
                 ▼                      ▼                     ▼
       Browser Client           PostgreSQL (Managed)    Worker Daemon
       (User JWT Session)       (pgvector, Pooling)    (Leasing, DLQ)
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                  OmniRoute Gateway            Mailbox OAuth APIs
                  (AI Orchestration)          (Gmail & Outlook)
```

The AI Job Assistant is engineered with clean separation of concerns:
- **Frontend**: Next.js 14 App Router, static generation with client hydration, standalone output, security headers.
- **Backend**: FastAPI with async SQLAlchemy, pydantic-settings, structured request logging, sliding window rate limiter, and health probes.
- **Worker Daemon**: Asynchronous background process (`worker.py`) handling application processing, worker crash recovery via 300s leases, and dead-letter queueing.
- **Database**: Managed PostgreSQL with asyncpg connection pooling (`pool_pre_ping=True`), pgvector embeddings, and startup migrations.

---

## 2. Environment Variables Specification

Production secrets must **NEVER** be committed to version control. They should be configured exclusively through your deployment platform's secure environment variable dashboard.

### Public Client Variables (Frontend)
| Variable | Required | Description | Example |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Fully-qualified public API URL for backend | `https://api.yourdomain.com/api/v1` |

### Private Server Variables (Backend & Worker)
| Variable | Required | Description | Constraints / Notes |
|---|---|---|---|
| `ENVIRONMENT` | Yes | Runtime environment | Set to `production` |
| `DEBUG` | Yes | Debug mode | Must be `false` in production |
| `PORT` | Auto | Web service listening port | Set by deployment platform (Render/Railway) |
| `DATABASE_URL` | Yes | Async PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/dbname?ssl=require` |
| `SECRET_KEY` | Yes | Cryptographic JWT signing secret | Min 32 characters high-entropy hex string |
| `MAILBOX_ENCRYPTION_KEY` | Yes | Fernet 32-byte encryption key for tokens | Generate via `cryptography.fernet.Fernet.generate_key()` |
| `BACKEND_CORS_ORIGINS` | Yes | Allowed frontend origins (no wildcard `*`) | `["https://yourdomain.com", "https://app.yourdomain.com"]` |
| `STORAGE_DIR` | No | Local directory for resume uploads | Persistent mount path: `/app/uploads/resumes` |
| `DEFAULT_AI_PROVIDER` | No | Active AI provider | `omniroute` (or `mock` for testing) |
| `OMNIROUTE_BASE_URL` | No | OmniRoute Gateway API base URL | Default: `https://api.omniroute.ai/v1` |
| `OMNIROUTE_API_KEY` | Conditional | OmniRoute Gateway access token | Required if using OmniRoute in production |
| `GOOGLE_CLIENT_ID` | Conditional | Google OAuth 2.0 Client ID | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET`| Conditional | Google OAuth 2.0 Client Secret | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | Conditional | Production Gmail OAuth callback | `https://api.yourdomain.com/api/v1/mailbox/gmail/callback` |
| `MICROSOFT_CLIENT_ID` | Conditional | Microsoft Entra App ID | From Microsoft Entra ID portal |
| `MICROSOFT_CLIENT_SECRET`| Conditional | Microsoft Entra Client Secret | From Microsoft Entra ID portal |
| `MICROSOFT_REDIRECT_URI` | Conditional | Production Outlook OAuth callback | `https://api.yourdomain.com/api/v1/mailbox/outlook/callback` |

---

## 3. Deployment Provider Options

### Option A: Railway (Recommended)
1. **Connect Repository**: Link your GitHub repository in the Railway dashboard.
2. **Add PostgreSQL Service**:
   - Provision a PostgreSQL database (`ai-job-assistant-db`).
   - Railway exposes the connection string as `DATABASE_URL`.
3. **Configure Backend Web Service (`ai-job-assistant-backend`)**:
   - **Root Directory**: `/backend`
   - **Builder**: `Dockerfile` (Ensure "Build Command" is **EMPTY** so Railway builds via Dockerfile instead of Railpack).
   - **Dockerfile Path**: `Dockerfile` (uses `backend/Dockerfile` and `backend/railway.toml`).
   - **Start Command**: `sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'`
   - **Healthcheck Path**: `/api/v1/health/live`
   - **Healthcheck Timeout**: `120`
   - **Environment Variables**: Configure `DATABASE_URL`, `SECRET_KEY`, `MAILBOX_ENCRYPTION_KEY`, etc.
4. **Configure Background Worker Service (`ai-job-assistant-worker`)**:
   - In the same Railway project, click **New** -> **GitHub Repo** -> select the repository.
   - **Root Directory**: `/backend`
   - **Builder**: `Dockerfile` (Ensure "Build Command" is **EMPTY**).
   - **Dockerfile Path**: `Dockerfile.worker` (or set environment variable `RAILWAY_DOCKERFILE_PATH = "Dockerfile.worker"`).
   - **Healthcheck Path**: Leave **EMPTY** (Worker is a background daemon that does not bind an HTTP port).
   - **Start Command**: `python worker.py`
   - **Environment Variables**: Set matching `DATABASE_URL`, `SECRET_KEY`, `MAILBOX_ENCRYPTION_KEY`.
5. **Frontend Deployment**:
   - Deploy the `frontend/` directory to **Vercel** (preferred production architecture).
   - Set `NEXT_PUBLIC_API_URL` to your Railway backend's public domain (e.g., `https://backend-production.up.railway.app/api/v1`).
   - If Railway created an `ai-job-assistant-frontend` service, you can safely remove or disable it on Railway since Vercel handles the Next.js frontend.

### Option B: Render Blueprint
Use the included `render.yaml` infrastructure-as-code file:
1. In Render Dashboard, click **New +** -> **Blueprint**.
2. Connect your repository. Render parses `render.yaml` and provisions:
   - PostgreSQL 16 database (`ai-job-assistant-db`)
   - FastAPI Web Service (`ai-job-assistant-backend`)
   - Background Worker (`ai-job-assistant-worker`)
   - Next.js Web Service (`ai-job-assistant-frontend`)
3. Populate the secret variables prompted by the Blueprint sync: `OMNIROUTE_API_KEY`, OAuth secrets.

### Option C: Vercel (Frontend) + Railway (Backend)
- Deploy frontend to Vercel with Root Directory set to `frontend`.
- Set `NEXT_PUBLIC_API_URL` to your Railway/Render backend domain.
- Configure custom domain on Vercel (`app.yourdomain.com`) and add it to `BACKEND_CORS_ORIGINS`.

### Option D: Self-Hosted Docker Compose (VPS / Single Server)
```bash
# 1. Clone repository on server
git clone <repo-url> /opt/ai-job-assistant
cd /opt/ai-job-assistant

# 2. Copy and populate production environment
cp .env.example .env
nano .env

# 3. Start full production stack
docker compose -f docker-compose.prod.yml up -d --build

# 4. Verify running containers
docker compose -f docker-compose.prod.yml ps
```

---

## 4. Database Setup & Migrations

### Startup Schema Creation
The backend uses SQLAlchemy async engine with DeclarativeBase models. On startup, `init_db()` runs:
```python
await conn.run_sync(Base.metadata.create_all)
```
- Non-destructive: creates missing tables, relationships, and indices.
- Preserves existing data across restarts and upgrades.

### PostgreSQL Connection Pooling & Dialect Handling
Managed databases provide URLs with `postgres://` or `postgresql://`. The backend's `settings.get_db_url()` automatically normalizes these to `postgresql+asyncpg://`.
The database session is configured with:
- `pool_pre_ping=True`: prevents stale connection disconnects.
- `pool_size=10`, `max_overflow=20`: handles concurrent burst traffic.

---

## 5. Background Worker Daemon (`worker.py`)

Run as a distinct long-running process:
```bash
cd backend
python worker.py
```
- **Crash Recovery**: Automatically scans for applications in `PROCESSING` status whose 300s lease has expired and re-queues them.
- **Dead-Letter Queue**: Applications exceeding retry limits are transitioned to `DEAD_LETTER` status without blocking the queue.
- **Graceful Termination**: Responds to `SIGINT` and `SIGTERM` signals by finishing the in-flight cycle before exiting.

---

## 6. OAuth & Third-Party Integration Setup

### Google / Gmail OAuth Setup
1. In Google Cloud Console -> APIs & Services -> Credentials.
2. Configure Authorized JavaScript Origins:
   - `https://app.yourdomain.com`
3. Configure Authorized Redirect URIs:
   - `https://api.yourdomain.com/api/v1/mailbox/gmail/callback`
4. Copy Client ID and Client Secret into `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### Microsoft / Outlook OAuth Setup
1. In Microsoft Entra ID (Azure Portal) -> App registrations.
2. Add Web Platform redirect URI:
   - `https://api.yourdomain.com/api/v1/mailbox/outlook/callback`
3. Generate client secret and copy to `MICROSOFT_CLIENT_SECRET`.

---

## 7. Health Checks & Observability

The application provides 3 health check tiers:
- **Liveness Probe**: `GET /api/v1/health/live`
  - Returns `{"status": "ALIVE"}`. Used by orchestrators (Kubernetes, Render, Railway) to verify process responsiveness.
- **Readiness Probe**: `GET /api/v1/health/ready`
  - Verifies live database connectivity and core service health before routing traffic. Returns `503` if DB is unreachable.
- **Detailed Diagnostics**: `GET /api/v1/health/detailed` (Authenticated)
  - Detailed telemetry covering database ping latency, worker pool status, queue depths, AI gateway reachability, and platform connectors.

---

## 8. Rollback & Troubleshooting Procedures

### Instant Rollback
- **Vercel / Railway / Render**: Use the "Instant Rollback" button in the deployment history tab to revert to the previous container/deployment artifact.
- **Docker Compose**: Roll back image tags or revert git commit and run `docker compose -f docker-compose.prod.yml up -d --build`.

### Common Issues
1. **`RuntimeError: Production configuration failed validation`**:
   - Occurs when `ENVIRONMENT=production` and `DEBUG=True`, default weak keys are present, or CORS is set to `*`. Fix the environment variables.
2. **`429 RATE_LIMITED`**:
   - Indicates client exceeded the 120 req/min sliding window rate limit.
3. **CORS Errors**:
   - Verify that your frontend's exact scheme and domain are present in `BACKEND_CORS_ORIGINS`.
