from typing import Optional, List
import uuid
from pydantic import BaseModel, Field

# ==================== RESUME SCHEMAS ====================
class GetCandidateProfileInput(BaseModel):
    include_skills: bool = Field(default=True, description="Whether to include detailed skills in profile summary")
    include_experiences: bool = Field(default=True, description="Whether to include work experience history")
    include_educations: bool = Field(default=True, description="Whether to include degrees and education")

class GetResumeVersionsInput(BaseModel):
    resume_id: Optional[str] = Field(default=None, description="Optional specific resume ID to list versions for")

class GetActiveResumeInput(BaseModel):
    pass

class GetCandidateSkillsInput(BaseModel):
    category: Optional[str] = Field(default=None, description="Optional skill category filter (e.g. TECHNICAL, SOFT, TOOL, CLOUD)")

class GetCandidateExperienceInput(BaseModel):
    pass

class GetCandidateEducationInput(BaseModel):
    pass

class GetCandidateProjectsInput(BaseModel):
    pass

# ==================== JOB SCHEMAS ====================
class SearchJobsInput(BaseModel):
    query: Optional[str] = Field(default=None, max_length=200, description="Job title, keywords, or technology to search for")
    location: Optional[str] = Field(default=None, max_length=100, description="City, country, or region")
    remote_type: Optional[str] = Field(default=None, description="REMOTE, HYBRID, or ONSITE")
    min_salary: Optional[int] = Field(default=None, ge=0, description="Minimum base salary filter (e.g. 600000 for 6 LPA, or 100000 for USD)")
    experience_level: Optional[str] = Field(default=None, description="ENTRY, MID, SENIOR, LEAD, or ALL")
    source: Optional[str] = Field(default=None, description="Platform source: greenhouse, lever, linkedin, indeed, naukri, unstop, etc.")
    limit: int = Field(default=10, ge=1, le=20, description="Maximum number of job results to return (max 20)")

class GetJobDetailsInput(BaseModel):
    job_id: Optional[str] = Field(default=None, description="UUID of the specific job in database")
    company_name: Optional[str] = Field(default=None, description="Company name if searching by company")
    job_title: Optional[str] = Field(default=None, description="Job title to look up")

class GetJobsBySourceInput(BaseModel):
    source: str = Field(..., description="Target source connector name: greenhouse, lever, linkedin, indeed, naukri, unstop, etc.")
    limit: int = Field(default=10, ge=1, le=20, description="Max jobs to return")

class GetJobsByLocationInput(BaseModel):
    location: str = Field(..., description="Location to filter by (e.g. Bangalore, San Francisco, London)")
    remote_type: Optional[str] = Field(default=None, description="REMOTE, HYBRID, or ONSITE")
    limit: int = Field(default=10, ge=1, le=20, description="Max jobs to return")

class GetJobsByRoleInput(BaseModel):
    role: str = Field(..., description="Target role name (e.g. Frontend Developer, Python Engineer, Data Analyst)")
    limit: int = Field(default=10, ge=1, le=20, description="Max jobs to return")

class GetJobsBySalaryInput(BaseModel):
    min_salary: int = Field(..., ge=0, description="Minimum salary amount")
    currency: str = Field(default="USD", description="Currency symbol/code: USD, INR, EUR, GBP")
    limit: int = Field(default=10, ge=1, le=20, description="Max jobs to return")

# ==================== MATCHING SCHEMAS ====================
class GetJobMatchInput(BaseModel):
    job_id: Optional[str] = Field(default=None, description="UUID of the job to evaluate/retrieve match for")
    job_title: Optional[str] = Field(default=None, description="Job title if matching by title")
    company_name: Optional[str] = Field(default=None, description="Company name if matching by company")

class GetRecommendedJobsInput(BaseModel):
    minimum_score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Minimum match score threshold (e.g. 80.0)")
    recommendation: Optional[str] = Field(default=None, description="Filter by tier: STRONG_MATCH, GOOD_MATCH, POSSIBLE_MATCH")
    limit: int = Field(default=10, ge=1, le=20, description="Max recommended jobs to return")

class GetMatchHistoryInput(BaseModel):
    limit: int = Field(default=10, ge=1, le=20, description="Max match records to return")

class GetMissingSkillsInput(BaseModel):
    job_id: Optional[str] = Field(default=None, description="Specific job UUID to analyze missing skills for (optional)")
    top_n: int = Field(default=10, ge=1, le=20, description="Number of most critical missing skills to return across matches")

class ExplainJobMatchInput(BaseModel):
    job_id: str = Field(..., description="Job UUID to produce an explainable match breakdown for")

# ==================== APPLICATION SCHEMAS ====================
class GetApplicationHistoryInput(BaseModel):
    status: Optional[str] = Field(default=None, description="Filter applications by status: APPLIED, INTERVIEWING, OFFER, REJECTED")
    limit: int = Field(default=10, ge=1, le=20, description="Max application history records to return")

class GetApplicationStatusInput(BaseModel):
    application_id: Optional[str] = Field(default=None, description="Specific application UUID")
    company_name: Optional[str] = Field(default=None, description="Company name to look up application for")
    job_title: Optional[str] = Field(default=None, description="Job title to look up application for")

class GetApplicationStatisticsInput(BaseModel):
    pass

class GetAnalyticsOverviewInput(BaseModel):
    pass

class GetAutoApplyStatusInput(BaseModel):
    pass

class GetAutoApplyPolicyInput(BaseModel):
    pass

class GetApplicationDetailsInput(BaseModel):
    application_id: Optional[str] = Field(default=None, description="Application UUID to inspect")
    job_id: Optional[str] = Field(default=None, description="Job UUID to find corresponding application details for")

