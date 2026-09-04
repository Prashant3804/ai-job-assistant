from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class OmniRouteHealthStatus(BaseModel):
    configured: bool
    reachable: bool
    status: str  # "CONNECTED" | "DEGRADED" | "OFFLINE" | "MOCK"
    chat_model: str
    embedding_model: str
    base_url: str
    auth_valid: bool
    message: str

class AIExplanationRequest(BaseModel):
    job_title: str
    company_name: str
    overall_score: float
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    eligibility_status: str
    recommendation: str
    experience_summary: Optional[str] = None
    location_summary: Optional[str] = None

class AIExplanationResponse(BaseModel):
    summary: str = Field(description="2-3 sentence clear rationale of the match")
    strengths: List[str] = Field(default_factory=list, description="Key candidate strengths for the role")
    gaps: List[str] = Field(default_factory=list, description="Skill or qualification gaps")
    recommendation_note: str = Field(description="Actionable advice for the candidate")

class EmbeddingCacheEntry(BaseModel):
    source_hash: str
    embedding: List[float]
    embedding_model: str
    embedding_version: str = "v1"
    generated_timestamp: datetime = Field(default_factory=datetime.utcnow)
