from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class PersonalDetails(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    is_uncertain: bool = False
    uncertain_fields: List[str] = []

class EducationItem(BaseModel):
    id: Optional[str] = None
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None
    description: Optional[str] = None
    is_uncertain: bool = False

class CategorizedSkills(BaseModel):
    programming_languages: List[str] = []
    frameworks: List[str] = []
    databases: List[str] = []
    cloud: List[str] = []
    tools: List[str] = []
    soft_skills: List[str] = []

class ExperienceItem(BaseModel):
    id: Optional[str] = None
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    responsibilities: List[str] = []
    technologies: List[str] = []
    is_uncertain: bool = False

class ProjectItem(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    technologies: List[str] = []
    links: List[str] = []
    is_uncertain: bool = False

class CertificationItem(BaseModel):
    id: Optional[str] = None
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    is_uncertain: bool = False

class StructuredResumeData(BaseModel):
    personal: PersonalDetails = Field(default_factory=PersonalDetails)
    education: List[EducationItem] = []
    skills: CategorizedSkills = Field(default_factory=CategorizedSkills)
    experience: List[ExperienceItem] = []
    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []
    raw_text: Optional[str] = None
    extraction_timestamp: Optional[str] = None
    total_years_experience: float = 0.0

class SaveProfileRequest(BaseModel):
    resume_id: Optional[uuid.UUID] = None
    personal: PersonalDetails
    education: List[EducationItem] = []
    skills: CategorizedSkills
    experience: List[ExperienceItem] = []
    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []

class CreateResumeVersionRequest(BaseModel):
    resume_id: uuid.UUID
    version_title: Optional[str] = None
    tailored_for_job_id: Optional[uuid.UUID] = None
    structured_data: StructuredResumeData

class ResumeVersionResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    tailored_for_job_id: Optional[uuid.UUID] = None
    tailored_content: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    created_at: datetime
