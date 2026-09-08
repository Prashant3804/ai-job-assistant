import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, EmailStr, model_validator

class ApplicationPolicyBase(BaseModel):
    auto_apply_enabled: bool = False
    minimum_match_score: float = Field(65.0, ge=0.0, le=100.0)
    minimum_salary: Optional[int] = Field(None, ge=0)
    maximum_experience: Optional[float] = Field(None, ge=0.0)

    preferred_roles: List[str] = Field(default_factory=list)
    blocked_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    blocked_locations: List[str] = Field(default_factory=list)
    blocked_companies: List[str] = Field(default_factory=list)
    blocked_keywords: List[str] = Field(default_factory=list)
    allowed_employment_types: List[str] = Field(default_factory=list)

    daily_application_limit: Optional[int] = Field(None, ge=1)
    per_source_daily_limit: Optional[int] = Field(None, ge=1)
    duplicate_protection: bool = True

    allow_entry_level: bool = True
    allow_internships: bool = True
    allow_remote: bool = True
    allow_hybrid: bool = True
    allow_onsite: bool = True

class ApplicationPolicyUpdate(BaseModel):
    auto_apply_enabled: Optional[bool] = None
    minimum_match_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    minimum_salary: Optional[int] = Field(None, ge=0)
    maximum_experience: Optional[float] = Field(None, ge=0.0)

    preferred_roles: Optional[List[str]] = None
    blocked_roles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    blocked_locations: Optional[List[str]] = None
    blocked_companies: Optional[List[str]] = None
    blocked_keywords: Optional[List[str]] = None
    allowed_employment_types: Optional[List[str]] = None

    daily_application_limit: Optional[int] = Field(None, ge=1)
    per_source_daily_limit: Optional[int] = Field(None, ge=1)
    duplicate_protection: Optional[bool] = None

    allow_entry_level: Optional[bool] = None
    allow_internships: Optional[bool] = None
    allow_remote: Optional[bool] = None
    allow_hybrid: Optional[bool] = None
    allow_onsite: Optional[bool] = None

class ApplicationPolicyRead(ApplicationPolicyBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AutoApplyStatusRead(BaseModel):
    auto_apply_enabled: bool
    minimum_match_score: float
    daily_application_limit: Optional[int] = None
    daily_limit_enabled: bool = False
    daily_limit_label: str = "Unlimited"
    applications_submitted_today: int
    remaining_daily_quota: Optional[int] = None
    queued_applications_count: int
    successful_applications_count: int
    failed_applications_count: int
    skipped_applications_count: int
    unsupported_sources_count: int

class ApplicationEventRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    title: str
    description: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApplicationAttemptRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    attempt_number: int
    status: str
    submission_method: str
    response_code: Optional[int] = None
    external_application_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobSummaryRead(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    location: Optional[str] = None
    remote_type: Optional[str] = None
    employment_type: Optional[str] = None
    apply_url: Optional[str] = None

    class Config:
        from_attributes = True

class ApplicationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    external_job_id: Optional[str] = None
    status: str
    match_score: Optional[float] = None
    eligibility_status: Optional[str] = None
    policy_decision: Optional[str] = None
    submission_method: str
    applied_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    external_application_id: Optional[str] = None
    failure_reason: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    job: Optional[Union[JobSummaryRead, Dict[str, Any]]] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    applied_at_display: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_display_fields(cls, data: Any):
        if isinstance(data, dict):
            return data

        job_obj = getattr(data, "job", None)
        comp = getattr(data, "company_name", None)
        title = getattr(data, "job_title", None)
        if job_obj:
            if not comp:
                comp = getattr(job_obj, "company_name", None)
            if not title:
                title = getattr(job_obj, "title", None)

        kolkata_tz = ZoneInfo("Asia/Kolkata")
        ts = getattr(data, "applied_date", None) or getattr(data, "submitted_at", None) or getattr(data, "created_at", None)
        display_ts = ts.astimezone(kolkata_tz).strftime("%d %b %Y, %I:%M %p IST") if ts else "Recent"

        job_dict = None
        if job_obj:
            job_dict = {
                "id": job_obj.id,
                "title": job_obj.title,
                "company_name": job_obj.company_name,
                "location": getattr(job_obj, "location", None),
                "remote_type": getattr(job_obj, "remote_type", None),
                "employment_type": getattr(job_obj, "employment_type", None),
                "apply_url": getattr(job_obj, "apply_url", None),
            }

        res = {
            "id": data.id,
            "user_id": data.user_id,
            "job_id": data.job_id,
            "resume_id": data.resume_id,
            "resume_version_id": data.resume_version_id,
            "source": data.source,
            "external_job_id": data.external_job_id,
            "status": data.status,
            "match_score": data.match_score,
            "eligibility_status": data.eligibility_status,
            "policy_decision": data.policy_decision,
            "submission_method": data.submission_method,
            "applied_date": data.applied_date,
            "submitted_at": data.submitted_at,
            "last_attempt_at": data.last_attempt_at,
            "external_application_id": data.external_application_id,
            "failure_reason": data.failure_reason,
            "notes": data.notes,
            "follow_up_date": data.follow_up_date,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
            "job": job_dict,
            "company_name": comp,
            "job_title": title,
            "applied_at_display": display_ts
        }
        if hasattr(data, "events"):
            res["events"] = getattr(data, "events", [])
        if hasattr(data, "attempts"):
            res["attempts"] = getattr(data, "attempts", [])
        return res

    class Config:
        from_attributes = True

class ApplicationDetailRead(ApplicationRead):
    events: List[ApplicationEventRead] = []
    attempts: List[ApplicationAttemptRead] = []

class ApplicationQueueItemRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    application_id: uuid.UUID
    job_id: uuid.UUID
    priority: int
    status: str
    attempt_count: int
    max_attempts: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    idempotency_key: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApplicationStatisticsRead(BaseModel):
    total_applications: int
    applied: int
    queued: int
    in_progress: int
    failed: int
    interviews: int
    offers: int
    rejected: int
    skipped_policy: int
    unsupported_platform: int
    missing_information: int

class ProcessQueueRequest(BaseModel):
    limit: int = Field(10, ge=1, le=50)

class ProcessQueueResponse(BaseModel):
    processed_count: int
    successful_count: int
    failed_count: int
    retried_count: int
    skipped_count: int
    details: List[Dict[str, Any]] = []

class AutoApplyDailyRunRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    scheduled_for: datetime
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    jobs_found: int
    matching_jobs: int
    applied_count: int
    already_applied_count: int
    manual_required_count: int
    failed_count: int
    skipped_count: int
    error_message: Optional[str] = None
    run_summary_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PlatformStatItem(BaseModel):
    name: str
    slug: str
    jobs_discovered: int
    matching_jobs: int
    applied: int
    manual_required: int
    failed: int
    daily_limit: int = 30
    applied_today: int
    current_daily_count: int
    progress_pct: float
    last_activity_utc: Optional[datetime] = None
    last_activity_ist: str = "Never run"
    status: str
    automation_type: str

class PlatformsDashboardResponse(BaseModel):
    date: str
    schedule_time: str = "10:00 AM IST"
    total_applied_today: int
    total_daily_limit: int = 210
    total_manual_required_today: int = 0
    total_failed_today: int = 0
    platforms: Dict[str, PlatformStatItem]

class AutoApplyDailyRoutineInfo(BaseModel):
    schedule_time_display: str = "10:00 AM IST"
    schedule_timezone: str = "Asia/Kolkata"
    auto_apply_enabled: bool
    status: str # "Active" | "Disabled"
    next_run_at: datetime
    next_run_display: str
    last_run: Optional[AutoApplyDailyRunRead] = None
    total_runs_count: int = 0
    daily_total_applied: int = 0
    daily_max_capacity: int = 210
    source_counters: Dict[str, int] = Field(default_factory=dict)
    source_limits: Dict[str, int] = Field(default_factory=dict)
    platforms: Optional[Dict[str, PlatformStatItem]] = None
    ai_provider_status: Optional[Dict[str, Any]] = None

