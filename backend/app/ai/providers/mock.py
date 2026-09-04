import hashlib
import json
import math
import re
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel

from app.ai.interfaces.llm_provider import LLMProvider
from app.ai.interfaces.embedding_provider import EmbeddingProvider
from app.ai.schemas.ai_schemas import AIExplanationResponse

T = TypeVar("T", bound=BaseModel)

class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM Provider for offline execution, fallback, and automated tests."""

    def __init__(
        self,
        should_fail: bool = False,
        failure_type: Optional[str] = None, # "timeout", "401", "429", "500", "malformed", "empty"
    ):
        self.should_fail = should_fail
        self.failure_type = failure_type

    def _trigger_simulated_failure_if_needed(self):
        if not self.should_fail:
            return
        if self.failure_type == "timeout":
            raise TimeoutError("Simulated OmniRoute timeout after 60s")
        elif self.failure_type == "401":
            raise PermissionError("Simulated OmniRoute 401 Unauthorized: Invalid API key")
        elif self.failure_type == "429":
            raise RuntimeError("Simulated OmniRoute 429 Rate Limit Exceeded")
        elif self.failure_type == "500":
            raise RuntimeError("Simulated OmniRoute 500 Internal Server Error")
        elif self.failure_type == "empty":
            return ""
        elif self.failure_type == "malformed":
            return "This is not valid JSON {malformed:..."
        else:
            raise RuntimeError("Simulated OmniRoute generic failure")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> str:
        if self.should_fail:
            res = self._trigger_simulated_failure_if_needed()
            if res is not None:
                return res

        lower = prompt.lower()
        if "match" in lower or "score" in lower or "explain" in lower:
            return (
                "Strong candidate alignment across core technical competencies. "
                "Candidate meets key requirements and role expectations with high compatibility."
            )
        elif "interview" in lower or "prepare" in lower:
            return (
                "1. Focus on core architectural patterns.\n"
                "2. Review async execution and concurrency.\n"
                "3. Prepare concise STAR responses."
            )
        return "AI analysis completed successfully with deterministic high fidelity."

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_model: Type[T],
        temperature: float = 0.1,
        timeout: Optional[float] = None
    ) -> T:
        if self.should_fail:
            res = self._trigger_simulated_failure_if_needed()
            if res is not None:
                if self.failure_type == "malformed":
                    raise ValueError("Simulated malformed JSON response")
                if self.failure_type == "empty":
                    raise ValueError("Simulated empty response")

        model_name = response_model.__name__
        lower_prompt = prompt.lower()

        if model_name == "AIExplanationResponse":
            # Extract basic context from prompt
            is_strong = "strong" in lower_prompt or "9" in lower_prompt
            return response_model(
                summary="Strong match based on technical skills and role compatibility. Requirements and location are well aligned.",
                strengths=["Technical skill overlap", "Relevant experience domain", "Location compatibility"],
                gaps=["Missing optional tool qualifications"] if "missing" in lower_prompt else [],
                recommendation_note="Highly recommended to proceed with application review." if is_strong else "Recommended for standard review."
            )

        if "EmailClassifyResponse" in model_name:
            if "interview" in lower_prompt or "schedule" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="INTERVIEW_INVITATION",
                    confidence_score=0.96,
                    summary="Recruiter invitation for technical interview.",
                    suggested_status_update="INTERVIEW_SCHEDULED",
                    detected_company="Acme Corp"
                )
            elif "regret" in lower_prompt or "unfortunately" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="REJECTION",
                    confidence_score=0.98,
                    summary="Standard rejection notice from talent team.",
                    suggested_status_update="REJECTED",
                    detected_company="Global Tech"
                )
            elif "offer" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="OFFER",
                    confidence_score=0.99,
                    summary="Formal employment offer letter received.",
                    suggested_status_update="OFFER_RECEIVED",
                    detected_company="Innovate Solutions"
                )
            else:
                return response_model(
                    is_recruiter=True,
                    classification="GENERAL_INQUIRY",
                    confidence_score=0.85,
                    summary="General recruiter inquiry.",
                    suggested_status_update=None,
                    detected_company="Stellar Labs"
                )

        if "StructuredResumeData" in model_name:
            from app.modules.resume.schemas import PersonalDetails, CategorizedSkills, EducationItem, ExperienceItem
            
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
            email = email_match.group(0) if email_match else None
            
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', prompt)
            phone = phone_match.group(0) if phone_match else None

            personal = PersonalDetails(
                name="Candidate",
                email=email,
                phone=phone,
                location="San Francisco, CA" if "san francisco" in lower_prompt else None,
                headline="Software Engineer",
                summary="Experienced software developer.",
                is_uncertain=False if email else True,
                uncertain_fields=[] if email else ["email"]
            )

            prog_lang = [l for l in ["Python", "TypeScript", "JavaScript", "Go", "Java", "C++", "Rust", "SQL"] if l.lower() in lower_prompt]
            frameworks = [f for f in ["FastAPI", "React", "Next.js", "Django", "Node.js"] if f.lower() in lower_prompt]
            databases = [d for d in ["PostgreSQL", "Redis", "MongoDB", "MySQL"] if d.lower() in lower_prompt]

            skills = CategorizedSkills(
                programming_languages=prog_lang or ["Python"],
                frameworks=frameworks or ["FastAPI"],
                databases=databases or ["PostgreSQL"],
                cloud=["AWS", "Docker"] if "aws" in lower_prompt or "docker" in lower_prompt else [],
                tools=["Git"] if "git" in lower_prompt else [],
                soft_skills=["System Design"]
            )

            return response_model(
                personal=personal,
                education=[EducationItem(degree="Bachelor of Science", institution="University", field_of_study="Computer Science", graduation_year="2021")],
                skills=skills,
                experience=[ExperienceItem(company="Tech Corp", role="Software Engineer", start_date="2022-01", end_date="Present", is_current=True, responsibilities=["Developed services"], technologies=["Python", "FastAPI"])],
                projects=[],
                certifications=[],
                total_years_experience=3.0
            )

        try:
            return response_model()
        except Exception:
            return response_model.model_construct()

    async def check_health(self) -> Dict[str, Any]:
        return {
            "configured": True,
            "reachable": True,
            "auth_valid": True,
            "status": "MOCK",
            "model": "mock-llm-deterministic",
            "base_url": "mock://internal",
            "message": "Mock LLM provider active"
        }


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic Mock Embedding provider calculating repeatable unit vectors via hashing."""

    def __init__(
        self,
        dimension: int = 128,
        model_name: str = "mock-embedding-v1",
        should_fail: bool = False
    ):
        self.dimension = dimension
        self.model_name = model_name
        self.should_fail = should_fail

    def get_model_name(self) -> str:
        return self.model_name

    async def generate_embedding(self, text: str, timeout: Optional[float] = None) -> List[float]:
        if self.should_fail:
            raise RuntimeError("Simulated Mock Embedding failure")
        
        vec = []
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        for i in range(self.dimension):
            val = math.sin(seed + (i * 1.618))
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 5) for x in vec]

    async def check_health(self) -> Dict[str, Any]:
        return {
            "configured": True,
            "reachable": True,
            "embedding_available": not self.should_fail,
            "dimension": self.dimension,
            "model": self.model_name,
            "message": "Mock embedding provider active"
        }
