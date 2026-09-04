# Phase 9: Production Hardening & Real Authorized Job Platform Integrations

## 1. Overview & Architecture

Phase 9 hardens the AI Job Assistant for enterprise production environments and establishes a unified, compliant, authorized integration architecture for job discovery and application processing.

### Production Pipeline Flow
```
Candidate Resume / Profile
            ↓
  Job Discovery Engine (Scheduler)
            ↓
  Connector Capability Registry (10+ Adapters)
            ↓
  Source Priority & Cross-Platform Deduplication
            ↓
  AI Matching Engine (OmniRoute + Embeddings)
            ↓
  Application Policy Engine
            ↓
  Capability & Compliance Check
     ┌──────┴────────────────────────┐
[Authorized Auto-Apply]    [External Application Required]
     ↓                               ↓
Application Queue           Candidate instructed with
(Lease Locking + DLQ)       official employer portal URL
     ↓
Authorized ATS / API
     ↓
Verified External Confirmation
     ↓
Application Tracker → Mailbox Sync → Recruiter AI
```

---

## 2. Platform Compliance & Non-Circumvention Rule

The system operates under a strict non-circumvention compliance policy:
- **Zero Anti-Bot Bypass**: No CAPTCHA solving, fingerprint spoofing, or stealth automation.
- **Zero Unauthorized Scraping**: Only official APIs, authorized partner tokens, and documented endpoints are used.
- **No Fabricated Confirmations**: Applications only transition to `APPLIED` when verified external evidence exists (`external_submission_id`, `confirmation_reference`).
- **External Fallback**: Platforms without authorized direct application APIs strictly return `EXTERNAL_APPLICATION_REQUIRED`.

---

## 3. Provider Capability Matrix

| Provider | Discovery | Auto-Apply | Status Tracking | Auth Type | Terms / Compliance Reference | Execution Mode |
|---|:---:|:---:|:---:|:---:|---|---|
| **Greenhouse** | `SUPPORTED` | `SUPPORTED` | `SUPPORTED` | `API_KEY / HARVEST` | Official Greenhouse Harvest API | Authorized Direct Submission |
| **Lever** | `SUPPORTED` | `SUPPORTED` | `SUPPORTED` | `OAUTH_2` | Official Lever Postings API | Authorized Direct Submission |
| **Naukri** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `PARTNER_API` | Naukri Developer Terms | `EXTERNAL_APPLICATION_REQUIRED` |
| **Indeed** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `OAUTH_2` | Indeed Sponsored Jobs Terms | `EXTERNAL_APPLICATION_REQUIRED` |
| **LinkedIn Jobs** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `OAUTH_2` | LinkedIn Developer Terms | `EXTERNAL_APPLICATION_REQUIRED` |
| **Unstop** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `NO_AUTH` | Unstop Public Discovery | `EXTERNAL_APPLICATION_REQUIRED` |
| **Internshala** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `NO_AUTH` | Internshala Student Feeds | `EXTERNAL_APPLICATION_REQUIRED` |
| **Wellfound** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `API_KEY` | Wellfound Startup API | `EXTERNAL_APPLICATION_REQUIRED` |
| **Career Pages** | `SUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | `NO_AUTH` | Direct Career Sites | `EXTERNAL_APPLICATION_REQUIRED` |
| **Mock ATS** | `SUPPORTED` | `SUPPORTED` | `SUPPORTED` | `API_KEY` | Test Provider | Configurable Mock (All Modes) |

---

## 4. Background Worker Reliability & Dead Letter Queue

1. **Worker Leasing (`ApplicationQueueItem`)**:
   - `locked_by`: Worker identifier.
   - `locked_at`: Timestamp when lease was acquired.
   - `lease_expires_at`: Automatic lease expiration (default 300 seconds).
2. **Crash Recovery (`recover_expired_leases`)**:
   - If a background worker terminates abruptly, any item remaining in `PROCESSING` past `lease_expires_at` is safely reclaimed and rescheduled for re-processing.
3. **Dead Letter Queue (`DeadLetterApplicationQueue`)**:
   - Items exceeding `max_attempts` without transient recovery or encountering unrecoverable submission errors are atomically moved to `DeadLetterApplicationQueue` with `failure_reason` and `last_error`.

---

## 5. Observability & Health Monitoring Endpoints

| Endpoint | Method | Auth Required | Description |
|---|---|:---:|---|
| `/api/v1/health` | `GET` | No | Public health and compliance status summary |
| `/api/v1/health/live` | `GET` | No | Kubernetes liveness probe |
| `/api/v1/health/ready` | `GET` | No | Kubernetes readiness probe (checks DB & queue) |
| `/api/v1/health/detailed` | `GET` | Yes | Deep health check (DB pool, worker metrics, OmniRoute) |
| `/api/v1/system/workers` | `GET` | Yes | Live worker telemetry, queue depths, throughput |
| `/api/v1/system/audit-logs` | `GET` | Yes | Immutable security and lifecycle audit events |
| `/api/v1/system/dead-letter-queue` | `GET` | Yes | Queryable dead-letter queue items |
| `/api/v1/connectors` | `GET` | No | Full capability declarations for all platforms |
| `/api/v1/connectors/{slug}/health` | `GET` | No | Diagnostic latency and error rate for a connector |

---

## 6. Secrets & Environment Configuration

### Environment Modes:
- `ENVIRONMENT=development`: Debugging enabled, mock providers available.
- `ENVIRONMENT=production`: Strict secret validation enforced at startup; `DEBUG=False`; `SECRET_KEY` must be a high-entropy secret; `MAILBOX_ENCRYPTION_KEY` must be a cryptographically secure 32-byte key.
