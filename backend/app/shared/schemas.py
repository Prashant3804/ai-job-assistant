from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from app.shared.constants import (
    ApplicationStatus,
    SubmissionMethod,
    EmailProvider,
    EmailClassification,
    RemoteType,
    EmploymentType,
    SkillCategory,
    ConnectorCapabilityStatus,
    ChatSenderType,
    ChatContextType,
    NotificationType,
)

# ----------------- Base Generic Schemas -----------------
class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None

# ----------------- Auth & User Schemas -----------------
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"

class SkillSchema(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    category: str = SkillCategory.TECHNICAL.value
    proficiency_level: str = "ADVANCED"
    years_experience: float = 1.0
    is_verified: bool = True

class EducationSchema(BaseModel):
    id: Optional[uuid.UUID] = None
    institution: str
    degree: str
    field_of_study: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    description: Optional[str] = None

class ExperienceSchema(BaseModel):
    id: Optional[uuid.UUID] = None
    company_name: str
    title: str
    location: Optional[str] = None
    employment_type: str = EmploymentType.FULL_TIME.value
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    bullet_points: Optional[List[str]] = []
    technologies: Optional[List[str]] = []

class ProjectSchema(BaseModel):
    id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    github_url: Optional[str] = None
    technologies: Optional[List[str]] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    remote_preference: Optional[str] = RemoteType.REMOTE.value
    target_roles: Optional[List[str]] = []
    preferred_roles: Optional[List[str]] = []
    preferred_locations: Optional[List[str]] = []
    preferred_work_arrangement: Optional[str] = "REMOTE"
    years_of_experience: Optional[float] = 0.0
    work_authorization: Optional[str] = None
    notice_period: Optional[str] = None
    salary_expectation: Optional[int] = None
    source: Optional[str] = "USER_CONFIRMED"
    onboarding_step: Optional[int] = 1
    onboarding_completed: Optional[bool] = False
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[SkillSchema]] = []
    educations: Optional[List[EducationSchema]] = []
    experiences: Optional[List[ExperienceSchema]] = []
    projects: Optional[List[ProjectSchema]] = []

class UserProfileRead(BaseModel):
    id: uuid.UUID
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    remote_preference: str = "REMOTE"
    target_roles: Optional[List[str]] = []
    preferred_roles: Optional[List[str]] = []
    preferred_locations: Optional[List[str]] = []
    preferred_work_arrangement: Optional[str] = "REMOTE"
    years_of_experience: float = 0.0
    work_authorization: Optional[str] = None
    notice_period: Optional[str] = None
    salary_expectation: Optional[int] = None
    source: str = "USER_CONFIRMED"
    onboarding_step: int = 1
    onboarding_completed: bool = False
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[SkillSchema]] = []
    educations: Optional[List[EducationSchema]] = []
    experiences: Optional[List[ExperienceSchema]] = []
    projects: Optional[List[ProjectSchema]] = []


class JobPreferenceUpdate(BaseModel):
    desired_titles: List[str] = []
    desired_locations: List[str] = []
    remote_types: List[str] = ["REMOTE", "HYBRID"]
    min_base_salary: Optional[int] = None
    max_base_salary: Optional[int] = None
    currency: str = "USD"
    employment_types: List[str] = ["FULL_TIME"]
    preferred_industries: List[str] = []
    excluded_industries: List[str] = []
    preferred_companies: List[str] = []
    blocked_companies: List[str] = []
    blocked_keywords: List[str] = []
    experience_min_years: Optional[float] = 0.0
    experience_max_years: Optional[float] = None
    job_freshness_days: int = 30
    minimum_match_score: float = 70.0
    target_industries: List[str] = []
    sponsorship_required: bool = False

class JobPreferenceRead(JobPreferenceUpdate):
    id: uuid.UUID
    user_id: uuid.UUID

class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    profile: Optional[UserProfileRead] = None
    job_preferences: Optional[JobPreferenceRead] = None

# ----------------- Resume Schemas -----------------
class ResumeRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_primary: bool
    file_url: Optional[str] = None
    file_format: str
    parsed_data: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

class ResumeUploadResponse(BaseModel):
    resume: ResumeRead
    extracted_profile: UserProfileRead

# ----------------- Job & Source Schemas -----------------
class JobSourceRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    base_url: Optional[str] = None
    connector_type: str
    capability_status: str
    is_active: bool

class JobRead(BaseModel):
    id: uuid.UUID
    job_source_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    title: str
    company_name: str
    location: Optional[str] = None
    remote_type: str
    employment_type: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str
    description: str
    requirements_summary: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    experience_level: str
    apply_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    job_source: Optional[JobSourceRead] = None

class JobFilterParams(BaseModel):
    query: Optional[str] = None
    remote_type: Optional[str] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    min_salary: Optional[int] = None
    limit: int = 20
    offset: int = 0

# ----------------- Matching Schemas -----------------
class MatchScoreBreakdown(BaseModel):
    overall_score: float
    semantic_score: float
    skills_score: float
    experience_score: float
    preference_score: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    match_reasons: List[str] = []
    risk_factors: List[str] = []

class JobMatchRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    overall_score: float
    skill_score: float = 0.0
    skills_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    location_score: float = 0.0
    role_score: float = 0.0
    salary_score: float = 0.0
    semantic_score: float = 0.0
    preference_score: float = 0.0
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    eligibility_status: str = "ELIGIBLE"
    recommendation: str = "POSSIBLE_MATCH"
    explanation: Optional[str] = None
    confidence: float = 1.0
    scoring_version: str = "v4.0.0"
    embedding_model: Optional[str] = None
    score_breakdown: Optional[Dict[str, Any]] = {}
    match_reasons: Optional[List[str]] = []
    is_bookmarked: bool = False
    is_dismissed: bool = False
    created_at: datetime
    job: JobRead

# ----------------- Application Schemas -----------------
class ApplicationEventRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    title: str
    description: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = {}
    created_at: datetime

class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    submission_method: str = SubmissionMethod.MANUAL.value
    notes: Optional[str] = None

class ApplicationUpdateStatus(BaseModel):
    status: str
    notes: Optional[str] = None

class ApplicationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    status: str
    applied_date: Optional[datetime] = None
    submission_method: str
    external_application_id: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    job: JobRead
    events: List[ApplicationEventRead] = []

# ----------------- Email & Recruiter Schemas -----------------
class EmailMessageRead(BaseModel):
    id: uuid.UUID
    email_account_id: uuid.UUID
    sender_email: str
    sender_name: Optional[str] = None
    recipient_email: str
    subject: str
    body_text: Optional[str] = None
    received_at: datetime
    is_recruiter: bool
    classification: str
    confidence_score: float
    application_id: Optional[uuid.UUID] = None

class EmailClassifyRequest(BaseModel):
    sender_email: str
    sender_name: Optional[str] = None
    subject: str
    body_text: str

class EmailClassifyResponse(BaseModel):
    is_recruiter: bool
    classification: str
    confidence_score: float
    summary: str
    suggested_status_update: Optional[str] = None
    detected_company: Optional[str] = None

class RecruiterRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    company_name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

# ----------------- Chat Schemas -----------------
class ChatMessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    content: str
    structured_payload: Optional[Dict[str, Any]] = None
    created_at: datetime

class ChatSendMessageRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    message: str
    context_type: str = ChatContextType.GENERAL.value
    reference_id: Optional[uuid.UUID] = None

class ChatConversationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    context_type: str
    created_at: datetime
    messages: List[ChatMessageRead] = []

# ----------------- Analytics & Dashboard Schemas -----------------
class DashboardSummaryMetrics(BaseModel):
    jobs_found: int = 0
    recommended_jobs: int = 0
    applications_total: int = 0
    interviews: int = 0
    offers: int = 0
    pending_applications: int = 0

class DashboardAnalytics(BaseModel):
    metrics: DashboardSummaryMetrics
    funnel: Dict[str, int]
    top_skills_in_demand: List[Dict[str, Any]]
    recent_activities: List[Dict[str, Any]]
    top_recommendations: List[JobMatchRead]
    auto_apply_routine: Optional[Dict[str, Any]] = None
    recent_auto_apply_applications: List[Dict[str, Any]] = []

# ----------------- Phase 10: Production Schemas -----------------

class ApplicationPolicyUpdate(BaseModel):
    auto_apply_enabled: bool = False
    minimum_match_score: float = 85.0
    minimum_salary: Optional[int] = None
    maximum_experience: Optional[float] = None
    preferred_roles: List[str] = []
    blocked_roles: List[str] = []
    preferred_locations: List[str] = []
    blocked_locations: List[str] = []
    blocked_companies: List[str] = []
    blocked_keywords: List[str] = []
    allowed_employment_types: List[str] = ["FULL_TIME"]
    daily_application_limit: Optional[int] = None
    per_source_daily_limit: Optional[int] = None
    per_company_limit: int = 3
    duplicate_protection: bool = True
    require_complete_profile: bool = True
    allow_entry_level: bool = True
    allow_internships: bool = True
    allow_remote: bool = True
    allow_hybrid: bool = True
    allow_onsite: bool = True

class ApplicationPolicyRead(ApplicationPolicyUpdate):
    id: uuid.UUID
    user_id: uuid.UUID

class AIConfigRead(BaseModel):
    provider: str
    model: str
    is_configured: bool
    api_key_masked: Optional[str] = None
    timeout_seconds: float = 30.0
    max_retries: int = 3
    fallback_provider: str = "omniroute"
    supports_structured: bool = True
    # Canonical Dual-Provider Architecture
    primary_provider: str = "gemini"
    primary_status: str = "AVAILABLE"
    primary_model: str = "gemini-1.5-flash"
    primary_configured: bool = False
    fallback_status: str = "READY"
    fallback_model: str = "gpt-4o"
    fallback_configured: bool = False
    omniroute_base_url: str = "http://localhost:20128/v1"
    automatic_fallback_enabled: bool = True
    active_provider: str = "gemini"
    active_display: str = "Gemini (Primary)"
    routing: str = "Gemini -> OmniRoute"
    gemini_api_key_masked: Optional[str] = None
    omniroute_api_key_masked: Optional[str] = None

class AIConfigUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_seconds: Optional[float] = None
    max_retries: Optional[int] = None
    gemini_api_key: Optional[str] = None
    omniroute_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    omniroute_model: Optional[str] = None
    omniroute_base_url: Optional[str] = None

class AIConnectionTestResponse(BaseModel):
    status: str # CONNECTED, AUTH_FAILED, RATE_LIMITED, TIMEOUT, UNAVAILABLE, NOT_CONFIGURED
    provider: str
    latency_ms: Optional[float] = None
    model: Optional[str] = None
    message: str
    # Dual provider diagnostics
    gemini_status: Optional[str] = None
    gemini_latency_ms: Optional[float] = None
    gemini_message: Optional[str] = None
    omniroute_status: Optional[str] = None
    omniroute_latency_ms: Optional[float] = None
    omniroute_message: Optional[str] = None

class OnboardingStateResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    current_step: int
    is_completed: bool
    profile_configured: bool
    resume_uploaded: bool
    preferences_configured: bool
    policy_configured: bool
    mailbox_connected: bool
    ai_configured: bool

class OnboardingStepRequest(BaseModel):
    step: int
    data: Optional[Dict[str, Any]] = None

class SystemComponentStatus(BaseModel):
    name: str
    slug: str
    status: str # HEALTHY, DEGRADED, NOT_CONFIGURED, AUTH_REQUIRED, DOWN
    details: Optional[str] = None
    last_checked: datetime

class SystemStatusResponse(BaseModel):
    overall_status: str # HEALTHY, DEGRADED, DOWN
    environment: str
    version: str
    database: SystemComponentStatus
    omniroute: SystemComponentStatus
    gmail: SystemComponentStatus
    outlook: SystemComponentStatus
    job_connectors: SystemComponentStatus
    application_queue: SystemComponentStatus
    workers: SystemComponentStatus
    ai_service: SystemComponentStatus

class ConnectorTestResponse(BaseModel):
    slug: str
    name: str
    status: str # PASS, AUTH_REQUIRED, UNSUPPORTED, RATE_LIMITED, ERROR
    capability: str # AUTO_APPLY_SUPPORTED, EXTERNAL_APPLICATION_REQUIRED, JOB_DISCOVERY_ONLY
    discovery_tested: bool
    submission_tested: bool
    message: str

