# Phase 5: AI Chatbot & Conversational Job Assistant

## 1. Overview

Phase 5 introduces a production-ready **AI Chatbot & Conversational Assistant** that empowers candidates to interact with their job search pipeline using natural language. The chatbot leverages a strictly controlled, schema-validated **Tool-Calling Architecture** integrated with the **OmniRoute AI Gateway** (`v1`).

---

## 2. Architecture & Safety Guarantees

```
┌────────────────────────────────────────────────────────┐
│                   User Message                         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
          ┌──────────────────────────────────┐
          │  Prompt Injection Sanitizer      │
          │  & Context Boundary Enforcer     │
          └────────────────┬─────────────────┘
                           │
                           ▼
          ┌──────────────────────────────────┐
          │   Conversational Orchestrator    │
          │  (Bounded History: 10 messages)  │
          └────────────────┬─────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
  ┌──────────────────┐           ┌──────────────────┐
  │ Controlled Tool  │           │   OmniRoute AI   │
  │  Execution Loop  │           │     Gateway      │
  │  (Max 4 calls,   │           │   (Synthesis)    │
  │  Strict Schemas) │           └────────┬─────────┘
  └─────────┬────────┘                    │
            │                             │
            ▼                             │
  ┌──────────────────┐                    │
  │ Isolated Database│                    │
  │    Layer (ORM)   │                    │
  └─────────┬────────┘                    │
            │                             │
            └──────────────┬──────────────┘
                           ▼
         ┌──────────────────────────────────┐
         │ Structured UI Payload & Natural  │
         │         Language Reply           │
         └──────────────────────────────────┘
```

### Safety & Isolation Rules
1. **No Direct DB Access**: The LLM never writes or executes arbitrary SQL. All database access occurs through strongly-typed Pydantic tools with user-level isolation (`user_id` enforced in Python backend).
2. **Loop Protection**: Tool orchestration is capped at a maximum of 4 executions per user message to prevent runaway recursions or denial-of-service loops.
3. **Execution Timeouts**: Every tool execution is wrapped in a 5.0s timeout.
4. **Deterministic Fallback**: If the OmniRoute AI gateway times out or encounters network degradation, the system automatically falls back to deterministic template syntheses without failing the request.
5. **Prompt Injection Defense**: Untrusted user inputs and job descriptions are stripped of system prompt overrides, instructions, and delimiters prior to LLM reasoning.

---

## 3. Controlled Tool Registry (17 Tools)

### Resume & Profile Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_candidate_profile` | `include_skills: bool` | Returns headline, target roles, experience years, and indexed skills. |
| `get_resume_versions` | `resume_id?: UUID` | Lists versions and tailoring history for candidate resumes. |
| `get_active_resume` | — | Retrieves primary active resume and metadata. |
| `get_candidate_skills` | `category?: SkillCategory` | Returns candidate skills grouped by category or filtered. |
| `get_candidate_experience` | — | Lists work history, companies, dates, and responsibilities. |
| `get_candidate_education` | — | Lists degrees, institutions, graduation dates, and fields of study. |
| `get_candidate_projects` | — | Lists candidate projects, repositories, and tech stacks. |

### Job Discovery Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `search_jobs` | `query, location, remote_type, min_salary, experience_level, source, limit` | Multi-criteria search across normalized job index. |
| `get_job_details` | `job_id?: UUID, company_name?: str, job_title?: str` | Retrieves full job description, salary, and requirements. |
| `get_jobs_by_source` | `source_slug: str, limit?: int` | Filters jobs by specific platform connector. |
| `get_jobs_by_location` | `location: str, limit?: int` | Filters jobs by geographic location. |
| `get_jobs_by_role` | `role_title: str, limit?: int` | Filters jobs matching target job role. |
| `get_jobs_by_salary` | `min_salary: int, currency?: str, limit?: int` | Queries jobs meeting or exceeding minimum compensation. |

### Matching & Insights Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_job_match` | `job_id: UUID` | Computes 6-dimension explainable match score. |
| `get_recommended_jobs` | `minimum_score?: float, limit?: int` | Returns top recommended job matches for candidate. |
| `get_match_history` | `limit?: int` | Retrieves historical match scores calculated for candidate. |
| `get_missing_skills` | `job_id: UUID` | Computes required and preferred skills gaps with upskilling recommendations. |
| `explain_job_match` | `job_id: UUID` | Generates dimension breakdown, strengths, and risks. |

### Application Tools (Read-Only)
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_application_history` | `status?: ApplicationStatus, limit?: int` | Retrieves candidate application log. |
| `get_application_status` | `application_id?: UUID, company_name?: str` | Look up status of specific submitted job application. |
| `get_application_statistics` | — | Aggregates application metrics (applied, review, interview, offer). |
| `get_analytics_overview` | — | Overall job search pipeline conversion metrics. |

---

## 4. Multi-Turn Conversational Memory & Context Tracking

The orchestrator maintains multi-turn conversation state within `ChatConversation.metadata_json`:
- `active_filters`: Retains location, salary, remote type across turns (e.g. Turn 1: "Find Python jobs in Bangalore" -> Turn 2: "Only remote").
- `last_job_ids`: Retains list of job IDs from the previous search results to enable ordinal references (e.g. Turn 3: "Tell me more about the first one").
- `active_job_id`: Tracks the currently discussed job for seamless follow-up questions ("What skills am I missing for this?").

---

## 5. Frontend Chat UI Features

- **Multi-Session Sidebar**: Create new conversations, switch between sessions, and delete obsolete threads.
- **Interactive Job Cards**: Embedded job discovery results with remote badges, salary pills, match percentages, and modal detail views.
- **Explainable Match Scorecards**: 6-dimension visual progress bars (Skills, Experience, Role Fit, Location, Salary, Education) with strengths and risk highlights.
- **Missing Skills Analysis Box**: Distinct required vs preferred skills gap indicators with actionable upskilling advice.
- **Suggestion Pills**: Dynamically generated one-click starter suggestions.
- **Tool Execution Badges**: Subtle transparency pills showing which controlled tools were executed.
