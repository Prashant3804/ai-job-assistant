# Phase 7 — Mailbox OAuth Integration & Recruiter Intelligence

## Architecture Overview

Phase 7 integrates read-only Mailbox OAuth synchronization for **Google Gmail** and **Microsoft Outlook / Office 365**, coupled with deterministic and AI classification pipelines to extract interview requests, offers, assessments, and rejections.

```
+-------------------------------------------------------------------------------+
|                       MAILBOX OAUTH & INGESTION LAYER                         |
|                                                                               |
|  +--------------------+         +--------------------+                        |
|  |    Google Gmail    |         | Microsoft Outlook  |                        |
|  |  (gmail.readonly)  |         |    (Mail.Read)     |                        |
|  +---------+----------+         +---------+----------+                        |
|            |                              |                                   |
|            +--------------+---------------+                                   |
|                           |                                                   |
|             HMAC State + Fernet Encrypted                                     |
|                     OAuth Tokens                                              |
|                           v                                                   |
|             +---------------------------+                                     |
|             |     MailboxNormalizer     | -> NormalizedEmail DTO              |
|             +-------------+-------------+                                     |
|                           v                                                   |
|             +---------------------------+                                     |
|             |      EmailClassifier      | -> Deterministic Rules Engine       |
|             |  (Heuristics + OmniRoute) |    (Known ATS + Intent Parsing)     |
|             +-------------+-------------+                                     |
|                           v                                                   |
|             +---------------------------+                                     |
|             |  ApplicationEmailMatcher  | -> Multi-Strategy Matcher           |
|             | (Company, Title, Domain)  |    (Updates Status & Timeline)      |
|             +-------------+-------------+                                     |
|                           v                                                   |
|       +-------------------+-------------------+                               |
|       |                                       |                               |
|       v                                       v                               |
|  +--------------------+             +--------------------+                    |
|  |  PostgreSQL / DB   |             | 10 Chatbot Tools   |                    |
|  | (Messages, Threads,|             | (Read-Only Inbox & |                    |
|  |  Recruiters, Sync) |             |  Recruiter Query)  |                    |
|  +--------------------+             +--------------------+                    |
+-------------------------------------------------------------------------------+
```

---

## Security & Compliance Guarantees

1. **Strict Read-Only Scopes**: Only `https://www.googleapis.com/auth/gmail.readonly` and `Mail.Read` are requested. Email sending, deletion, or modification is prohibited in Phase 7.
2. **At-Rest Token Encryption**: All access and refresh tokens are encrypted at rest using symmetric Fernet (`MAILBOX_ENCRYPTION_KEY`). Tokens are NEVER sent to the frontend client, NEVER logged, and NEVER passed in AI prompt context.
3. **Anti-CSRF & State Token Verification**: OAuth authorization URLs generate HMAC-SHA256 signed state tokens incorporating `user_id`, provider, and timestamp with 10-minute expiration.
4. **XSS Sanitization**: Email HTML content is stripped of `<script>`, `<iframe>`, `<object>`, `<embed>`, inline event handlers (`onload`, `onerror`, `onclick`), and `javascript:` pseudo-protocols before storage or frontend rendering.
5. **Prompt Injection Protection**: Untrusted text in email subjects and bodies is treated strictly as passive data and validated against rigid Pydantic schemas.

---

## 10 Chatbot Read-Only Mailbox Tools

| Tool Name | Category | Description |
|---|---|---|
| `get_mailbox_connections` | MAILBOX | Lists active connected mailboxes and sync states |
| `get_recent_job_emails` | MAILBOX | Retrieves recent job-related emails with search filter |
| `get_recruiter_messages` | MAILBOX | Lists messages from direct human recruiters |
| `get_application_emails` | MAILBOX | Correlates emails linked to a target application or company |
| `get_interview_emails` | MAILBOX | Retrieves interview invitations and screening requests |
| `get_rejection_emails` | MAILBOX | Retrieves application rejection emails |
| `get_offer_emails` | MAILBOX | Retrieves formal job offers and compensation packages |
| `get_email_details` | MAILBOX | Returns snippet and sanitized content for a specific message |
| `get_email_thread` | MAILBOX | Returns all messages in a conversation thread |
| `get_mailbox_sync_status` | MAILBOX | Returns overall sync status and mailbox metric breakdown |

---

## REST API Endpoints

- `GET /api/v1/mailbox/connect/gmail` — Get OAuth authorization URL for Gmail
- `GET /api/v1/mailbox/connect/outlook` — Get OAuth authorization URL for Microsoft Outlook
- `POST /api/v1/mailbox/callback` — Exchange authorization code for encrypted tokens and create connection
- `GET /api/v1/mailbox/connections` — List user's active mailbox connections
- `DELETE /api/v1/mailbox/connections/{id}` — Disconnect mailbox connection
- `POST /api/v1/mailbox/sync` — Trigger delta / full email synchronization
- `GET /api/v1/mailbox/messages` — List normalized messages with filters (category, search, recruiter_only)
- `GET /api/v1/mailbox/messages/{id}` — Get single message detail with sanitized body
- `POST /api/v1/mailbox/messages/{id}/reclassify` — Manually override email classification category
- `GET /api/v1/mailbox/threads` — List conversation threads
- `GET /api/v1/mailbox/threads/{id}` — Get thread detail and child messages
- `GET /api/v1/mailbox/stats` — Mailbox intelligence aggregated statistics
- `GET /api/v1/mailbox/notifications` — List recruiter and milestone notifications
- `POST /api/v1/mailbox/notifications/{id}/read` — Mark notification as read
- `GET /api/v1/mailbox/recruiters` — List detected recruiters and talent partners
