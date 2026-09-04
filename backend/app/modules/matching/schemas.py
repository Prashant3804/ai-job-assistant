from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.modules.matching.constants import EligibilityStatus, RecommendationStatus
from app.shared.schemas import JobRead

class DimensionScore(BaseModel):
    score: float
    weight: float
    contribution: float
    status: str  # "MATCH" | "PARTIAL" | "MISMATCH" | "UNAVAILABLE"
    details: Dict[str, Any] = Field(default_factory=dict)
    rationale: str

class MatchScoreBreakdown(BaseModel):
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    location_score: float
    role_score: float
    salary_score: float
    semantic_score: float
    
    # Granular dimensions
    dimensions: Dict[str, DimensionScore] = Field(default_factory=dict)
    
    matched_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    
    eligibility_status: EligibilityStatus
    recommendation: RecommendationStatus
    
    explanation: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    
    confidence: float = 1.0
    scoring_version: str = "v4.0.0"
    embedding_model: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchJobRequest(BaseModel):
    resume_version_id: Optional[uuid.UUID] = None

class BatchMatchRequest(BaseModel):
    job_ids: Optional[List[uuid.UUID]] = None
    limit: int = 50
    resume_version_id: Optional[uuid.UUID] = None

class BatchMatchItemResult(BaseModel):
    job_id: uuid.UUID
    overall_score: float
    eligibility_status: str
    recommendation: str
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []

class BatchMatchResponse(BaseModel):
    total_processed: int
    matches: List[BatchMatchItemResult]

class MatchFilterParams(BaseModel):
    minimum_score: Optional[float] = None
    eligibility: Optional[str] = None
    recommendation: Optional[str] = None
    source: Optional[str] = None
    location: Optional[str] = None
    role: Optional[str] = None
    limit: int = 20
    offset: int = 0

class JobMatchResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    location_score: float
    role_score: float
    salary_score: float
    semantic_score: float
    
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    
    eligibility_status: str
    recommendation: str
    
    explanation: Optional[str] = None
    confidence: float
    scoring_version: str
    embedding_model: Optional[str] = None
    
    score_breakdown: Optional[Dict[str, Any]] = None
    is_bookmarked: bool = False
    is_dismissed: bool = False
    
    created_at: datetime
    updated_at: datetime
    job: Optional[JobRead] = None

class MatchingEngineHealthResponse(BaseModel):
    engine_status: str  # "READY" | "DEGRADED"
    omniroute_configured: bool
    omniroute_reachable: bool
    omniroute_status: str
    chat_model: str
    embedding_model: str
    deterministic_matching_available: bool = True
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    scoring_version: str
