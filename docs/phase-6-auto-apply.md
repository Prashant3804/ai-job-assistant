# Phase 6: Automated Application Engine

## 1. Overview

Phase 6 introduces a production-ready, platform-independent **Automated Application Engine** for the AI Job Assistant. The engine autonomously discovers matching job opportunities, evaluates them against personalized candidate **Auto-Apply Policies**, matches the most relevant tailored resume version, maps verified profile data into ATS questions without hallucination, and executes submissions through authorized partner connectors.

---

## 2. Safety & Compliance Non-Circumvention Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Discovered & Matched Job                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │       Policy Evaluation Engine       │
                 │ (Score, Salary, Exp, Blocklist, Limit│
                 └──────────────────┬───────────────────┘
                                    │ Approved
                                    ▼
                 ┌──────────────────────────────────────┐
                 │      Duplicate & Idempotency Guard   │
                 │ (External ID, URL, Hash, Unique Key) │
                 └──────────────────┬───────────────────┘
                                    │ Verified Unique
                                    ▼
                 ┌──────────────────────────────────────┐
                 │    Platform Capability Validator     │
                 │ (SUPPORTED_AUTO_APPLY vs EXTERNAL)   │
                 └──────────────────┬───────────────────┘
                                    │ Authorized
                                    ▼
                 ┌──────────────────────────────────────┐
                 │       Resume Selection Service       │
                 │  (Best Tailored Version vs Master)   │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │      Verified Profile Data Mapper    │
                 │ (Strict mapping, Zero Hallucination) │
                 └──────────────────┬───────────────────┘
                                    │ Complete & Valid
                                    ▼
                 ┌──────────────────────────────────────┐
                 │      Application State Machine       │
                 │  (Enforces Valid Status Transitions) │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │     Authorized Partner Connector     │
                 │  (Direct API, Idempotent Submission) │
                 └──────────────────┬───────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            │ Success                                       │ Failure
            ▼                                               ▼
┌───────────────────────┐                       ┌───────────────────────┐
│     APPLIED / 200     │                       │  Retry Manager (429)  │
│ External Confirmation │                       │  or Permanent Failed  │
└───────────────────────┘                       └───────────────────────┘
```

### Safety & Compliance Core Rules:
1. **No Bot Bypass / CAPTCHA Circumvention**: Direct browser scraping or CAPTCHA bypass is strictly prohibited. If a source requires candidate browser action, the engine marks the job as `EXTERNAL_APPLICATION_REQUIRED` and pauses.
2. **Zero Hallucination / Fabrication**: Only verified candidate master profile data is mapped. If a required application field is missing, the application enters `MISSING_INFORMATION` for candidate review.
3. **Idempotency Protection**: Every queued submission generates an SHA-256 idempotency key ensuring network retries never submit duplicate applications.
4. **Immutable Audit Trail**: Every status transition, submission attempt, and policy decision creates a timestamped, append-only `ApplicationEvent` and `ApplicationAuditLog`.

---

## 3. Database Schema Models

The module is supported by 7 dedicated relational models:

1. `Application`: Primary lifecycle record tracking `user_id`, `job_id`, `resume_version_id`, `status`, `match_score`, `eligibility_status`, `policy_decision`, `submission_method`, `external_application_id`, `applied_date`.
2. `ApplicationPolicy`: Configurable candidate rules (`auto_apply_enabled`, `minimum_match_score`, `minimum_salary`, `maximum_experience`, `preferred_roles`, `blocked_companies`, `blocked_keywords`, `daily_application_limit`, `per_source_daily_limit`, `allow_remote`, `allow_hybrid`, `allow_onsite`).
3. `ApplicationQueueItem`: Priority execution queue supporting retry counts, idempotency keys, and scheduled timestamps.
4. `ApplicationAttempt`: Detailed log of every HTTP submission attempt (`attempt_number`, `response_code`, `status`, `error_code`, `error_message`, `started_at`, `completed_at`).
5. `ApplicationAnswer`: Exact questions and answers mapped from verified profile (`question_key`, `question_text`, `answer_text`, `is_sensitive`, `confidence_source`).
6. `ApplicationDocument`: Uploaded resumes and cover letters attached to the submission.
7. `ApplicationEvent` & `ApplicationAuditLog`: Immutable chronological audit logs recording all state transitions.

---

## 4. State Machine Transition Matrix

The `ApplicationStateMachine` guarantees valid forward progression:

| Current Status | Allowed Target Statuses |
|---|---|
| `DISCOVERED` | `POLICY_PENDING`, `QUEUED`, `DRAFT`, `BLOCKED`, `DUPLICATE`, `AUTO_APPLY_UNSUPPORTED` |
| `POLICY_PENDING`| `QUEUED`, `BLOCKED`, `DRAFT` |
| `QUEUED` | `PREPARING`, `CANCELLED`, `FAILED` |
| `PREPARING` | `VALIDATING`, `FAILED`, `CANCELLED` |
| `VALIDATING` | `SUBMITTING`, `MISSING_INFORMATION`, `FAILED` |
| `SUBMITTING` | `APPLIED`, `SUBMITTED`, `RETRYING`, `FAILED`, `AUTO_APPLY_UNSUPPORTED` |
| `RETRYING` | `SUBMITTING`, `FAILED`, `CANCELLED` |
| `APPLIED` / `SUBMITTED` | `UNDER_REVIEW`, `OA_RECEIVED`, `INTERVIEW_SCHEDULED`, `REJECTED`, `WITHDRAWN`, `ARCHIVED` |
| `UNDER_REVIEW` | `OA_RECEIVED`, `INTERVIEW_SCHEDULED`, `OFFER_RECEIVED`, `REJECTED`, `WITHDRAWN`, `ARCHIVED` |
| `INTERVIEW_SCHEDULED` | `INTERVIEW_SCHEDULED`, `OFFER_RECEIVED`, `REJECTED`, `WITHDRAWN`, `ARCHIVED` |
| `OFFER_RECEIVED`| `OFFER_RECEIVED`, `REJECTED`, `WITHDRAWN`, `ARCHIVED` |
| `FAILED` | `QUEUED`, `DRAFT`, `ARCHIVED` |

---

## 5. Automated Retry & Backoff Strategy

Transient errors (e.g. HTTP 429 Rate Limits, Gateway Timeouts 504, Connection Drops) are automatically identified and scheduled for exponential backoff:

$$\text{Delay} = \text{Initial Delay} \times 2^{\text{attempt} - 1} + \text{Jitter}$$

Permanent failures (e.g. HTTP 401 Unauthorized, HTTP 400 Malformed Payload, Missing Mandatory Credentials) immediately terminate retries to conserve system resources and platform quotas.

---

## 6. Chatbot Integration Tools

Three new read-only tools have been added to the conversational assistant:
- `get_auto_apply_status`: Reports whether the engine is active, remaining daily quota, and pending queue size.
- `get_auto_apply_policy`: Fetches the user's active match thresholds, salary requirements, and blocklists.
- `get_application_details`: Inspects a specific application's lifecycle status, submission confirmation ID, and timeline events.

---

## 7. Frontend User Experience

1. **Auto-Apply Dashboard (`/auto-apply`)**:
   - Master Enable/Disable switch with real-time status banner.
   - Daily application quota progress bar.
   - Interactive policy rule configuration (threshold sliders, tag inputs, checkboxes).
   - Real-time application queue monitor with manual batch processing trigger.
2. **Applications Tracker (`/applications`)**:
   - Live metrics banner with aggregated status counts.
   - Dynamic multi-status filtering and instant text search.
   - Application cards with match score badges, connector indicators, and direct detail links.
3. **Application Detail & Audit Trail (`/applications/[id]`)**:
   - Chronological event timeline displaying all status changes.
   - API submission attempt history with HTTP response codes.
   - Verified form answers preview.
   - Manual status transition selector.
