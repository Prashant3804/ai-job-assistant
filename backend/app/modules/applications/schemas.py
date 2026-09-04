import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr

class ApplicationPolicyBase(BaseModel):
    auto_apply_enabled: bool = False
    minimum_match_score: float = Field(85.0, ge=0.0, le=100.0)
    minimum_salary: Optional[int] = Field(None, ge=0)
    maximum_experience: Optional[float] = Field(None, ge=0.0)

    preferred_roles: List[str] = Field(default_factory=list)
    blocked_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    blocked_locations: List[str] = Field(default_factory=list)
    blocked_companies: List[str] = Field(default_factory=list)
    blocked_keywords: List[str] = Field(default_factory=list)
    allowed_employment_types: List[str] = Field(default_factory=list)

    daily_application_limit: int = Field(30, ge=1, le=200)
    per_source_daily_limit: int = Field(10, ge=1, le=100)
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

    daily_application_limit: Optional[int] = Field(None, ge=1, le=200)
    per_source_daily_limit: Optional[int] = Field(None, ge=1, le=100)
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
    daily_application_limit: int
    applications_submitted_today: int
    remaining_daily_quota: int
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
    job: Optional[Dict[str, Any]] = None

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
