import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseLLMService(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass

class MockAIProvider(BaseLLMService):
    """Zero-dependency, deterministic & high-fidelity provider for local testing and offline execution."""

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        lower = prompt.lower()
        if "interview" in lower or "prepare" in lower:
            return (
                "Here are key preparation strategies for your upcoming interview:\n\n"
                "1. **System Architecture**: Review distributed systems concepts, microservices patterns, and caching strategies.\n"
                "2. **Core Competencies**: Be ready to discuss FastAPI async concurrency, PostgreSQL indexing, and ORM query optimization.\n"
                "3. **Behavioral**: Prepare STAR-method stories emphasizing cross-functional leadership and deadline management."
            )
        elif "match" in lower or "score" in lower:
            return (
                "Based on the analysis, this role has an 88% overall match. Your backend experience with FastAPI and PostgreSQL "
                "aligns closely with the senior requirements. The primary gap is Kubernetes cluster management."
            )
        elif "cover letter" in lower or "cover_letter" in lower:
            # Extract candidate name if present in prompt
            name_match = re.search(r"-\s*Name:\s*([^\n]+)", prompt)
            cand_name = name_match.group(1).strip() if name_match else "Candidate"
            comp_match = re.search(r"-\s*Company:\s*([^\n]+)", prompt)
            comp_name = comp_match.group(1).strip() if comp_match else "Employer"
            title_match = re.search(r"-\s*Job Title:\s*([^\n]+)", prompt)
            job_title = title_match.group(1).strip() if title_match else "Software Engineer"

            return (
                f"Dear Hiring Team at {comp_name},\n\n"
                f"I am writing to express my strong interest in the {job_title} position. "
                f"With hands-on experience and technical background aligning with your requirements, "
                f"I am eager to contribute to your engineering team's goals.\n\n"
                f"Sincerely,\n{cand_name}"
            )
        elif "email" in lower or "draft" in lower:
            return (
                "Dear Hiring Team,\n\n"
                "Thank you for reaching out regarding the Senior Backend Engineer role. "
                "I am very excited about the opportunity and would be glad to discuss my experience further. "
                "I am available for an introductory call this Tuesday or Thursday between 2:00 PM and 5:00 PM EST.\n\n"
                "Best regards,\nCandidate"
            )
        return (
            "I am your AI Job Assistant. I have analyzed your candidate profile, tracked applications, and matched opportunities. "
            "You have 3 top-matching roles (>85%) ready for review and 1 upcoming technical interview scheduled this week."
        )

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        model_name = response_model.__name__
        lower_prompt = prompt.lower()

        if "EmailClassifyResponse" in model_name:
            if "interview" in lower_prompt or "schedule" in lower_prompt or "call" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="INTERVIEW_INVITATION",
                    confidence_score=0.96,
                    summary="Recruiter invitation for next-round technical interview.",
                    suggested_status_update="INTERVIEW_SCHEDULED",
                    detected_company="Acme Corp"
                )
            elif "regret" in lower_prompt or "unfortunately" in lower_prompt or "other candidates" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="REJECTION",
                    confidence_score=0.98,
                    summary="Standard rejection notice from talent acquisition.",
                    suggested_status_update="REJECTED",
                    detected_company="Global Tech"
                )
            elif "offer" in lower_prompt or "pleased to offer" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="OFFER",
                    confidence_score=0.99,
                    summary="Formal employment offer letter received.",
                    suggested_status_update="OFFER_RECEIVED",
                    detected_company="Innovate Solutions"
                )
            elif "assessment" in lower_prompt or "hackerrank" in lower_prompt or "codesignal" in lower_prompt:
                return response_model(
                    is_recruiter=True,
                    classification="OA_REQUEST",
                    confidence_score=0.94,
                    summary="Online technical coding assessment request.",
                    suggested_status_update="UNDER_REVIEW",
                    detected_company="Tech Pioneers"
                )
            else:
                return response_model(
                    is_recruiter=True,
                    classification="GENERAL_INQUIRY",
                    confidence_score=0.85,
                    summary="Recruiter outreach regarding current availability.",
                    suggested_status_update=None,
                    detected_company="Stellar Labs"
                )
        
        elif "StructuredResumeData" in model_name:
            # Deterministically parse basic fields from prompt for high fidelity
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
            email = email_match.group(0) if email_match else None
            
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', prompt)
            phone = phone_match.group(0) if phone_match else None

            # Detect lines for name
            prompt_lines = [l.strip() for l in prompt.splitlines() if l.strip() and not l.startswith("Extract") and not l.startswith("You are")]
            name = prompt_lines[0] if prompt_lines else "Candidate"
            if len(name) > 50 or "@" in name:
                name = "Candidate"

            from app.modules.resume.schemas import PersonalDetails, CategorizedSkills, EducationItem, ExperienceItem, ProjectItem, CertificationItem
            
            personal = PersonalDetails(
                name=name,
                email=email,
                phone=phone,
                location="San Francisco, CA" if "san francisco" in lower_prompt else None,
                headline="Software Engineer",
                summary="Software engineering professional with extensive technical background.",
                is_uncertain=False if email else True,
                uncertain_fields=[] if email else ["email"]
            )

            # Detect skills
            prog_lang = []
            for lang in ["Python", "TypeScript", "JavaScript", "Go", "Java", "C++", "Rust", "SQL"]:
                if re.search(r'\b' + re.escape(lang.lower()) + r'\b', lower_prompt):
                    prog_lang.append(lang)

            frameworks = []
            for fw in ["FastAPI", "React", "Next.js", "Django", "Node.js", "TailwindCSS"]:
                if re.search(r'\b' + re.escape(fw.lower()) + r'\b', lower_prompt):
                    frameworks.append(fw)

            databases = []
            for db in ["PostgreSQL", "Redis", "MongoDB", "MySQL", "pgvector"]:
                if re.search(r'\b' + re.escape(db.lower()) + r'\b', lower_prompt):
                    databases.append(db)

            skills = CategorizedSkills(
                programming_languages=prog_lang,
                frameworks=frameworks,
                databases=databases,
                cloud=["AWS", "Docker"] if "docker" in lower_prompt or "aws" in lower_prompt else [],
                tools=["Git", "Docker"] if "git" in lower_prompt or "docker" in lower_prompt else [],
                soft_skills=["System Design", "Leadership"] if "system design" in lower_prompt or "leadership" in lower_prompt else []
            )

            # Education if found in prompt
            education = []
            if "bachelor" in lower_prompt or "university" in lower_prompt or "berkeley" in lower_prompt:
                education.append(EducationItem(
                    degree="Bachelor of Science",
                    institution="University of California, Berkeley" if "berkeley" in lower_prompt else "University",
                    field_of_study="Computer Science",
                    graduation_year="2021",
                    cgpa="3.85" if "3.85" in prompt else None
                ))

            # Experience if found in prompt
            experience = []
            if "experience" in lower_prompt or "engineer" in lower_prompt:
                experience.append(ExperienceItem(
                    company="Apex Cloud Systems" if "apex" in lower_prompt else "Technology Corp",
                    role="Senior Backend Engineer",
                    start_date="2022-01",
                    end_date="Present",
                    is_current=True,
                    responsibilities=["Designed distributed backend services and optimized database queries."],
                    technologies=prog_lang + frameworks
                ))

            return response_model(
                personal=personal,
                education=education,
                skills=skills,
                experience=experience,
                projects=[],
                certifications=[],
                total_years_experience=4.0
            )

        # Default empty model instantiation
        try:
            return response_model()
        except Exception:
            return response_model.model_construct()

    async def generate_embedding(self, text: str) -> List[float]:
        import hashlib
        import math
        vec = []
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        for i in range(128):
            val = math.sin(seed + i)
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 4) for x in vec]

class OpenAIProvider(BaseLLMService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.model = settings.OPENAI_MODEL

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.3}
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        schema = response_model.model_json_schema()
        system = (system_prompt or "") + f"\nYou must respond strictly in JSON matching this JSON Schema:\n{json.dumps(schema)}"
        raw_json = await self.generate_text(prompt, system_prompt=system)
        clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_json.strip())
        parsed = json.loads(clean_json)
        return response_model.model_validate(parsed)

    async def generate_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": settings.EMBEDDING_MODEL, "input": text}
            )
            res.raise_for_status()
            data = res.json()
            return data["data"][0]["embedding"]

class GeminiProvider(BaseLLMService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = settings.GEMINI_MODEL
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.2}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(self.base_url, json=payload)
            res.raise_for_status()
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        schema = response_model.model_json_schema()
        system = (system_prompt or "") + f"\nRespond strictly in valid JSON matching schema:\n{json.dumps(schema)}"
        raw_text = await self.generate_text(prompt, system_prompt=system)
        clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
        parsed = json.loads(clean_json)
        return response_model.model_validate(parsed)

    async def generate_embedding(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2000]}]}
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    values = data.get("embedding", {}).get("values", [])
                    if values:
                        return values
        except Exception as e:
            logger.warning(f"Gemini embedding API call failed: {e}. Using deterministic fallback.")
        return [float(ord(c) % 10) / 10.0 for c in (text[:1536] + "x" * 1536)[:1536]]

class AIServiceException(Exception):
    """Raised when all configured resilient AI providers fail."""
    pass

class OmniRouteProvider(BaseLLMService):
    """OmniRoute OpenAI-compatible model gateway provider."""
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OMNIROUTE_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.OMNIROUTE_API_KEY
        self.model = model or settings.OMNIROUTE_CHAT_MODEL
        self.timeout = timeout or float(settings.OMNIROUTE_TIMEOUT_SECONDS)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/chat/completions", headers=self._get_headers(), json=payload)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        schema = response_model.model_json_schema()
        system = (system_prompt or "") + f"\nRespond strictly in valid JSON matching this schema:\n{json.dumps(schema)}"
        raw_text = await self.generate_text(prompt, system_prompt=system)
        clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
        parsed = json.loads(clean_json)
        return response_model.model_validate(parsed)

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self._get_headers(),
                    json={"model": settings.OMNIROUTE_EMBEDDING_MODEL, "input": text}
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["data"][0]["embedding"]
        except Exception:
            pass
        return await MockAIProvider().generate_embedding(text)

# Backwards compatibility alias
OpenRouterProvider = OmniRouteProvider


class ResilientAIService(BaseLLMService):
    """Centralized resilient AI service: Google Gemini (Primary) -> OmniRoute (Automatic Fallback)."""

    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.omniroute_key = getattr(settings, "OPENROUTER_API_KEY", None) or getattr(settings, "OMNIROUTE_API_KEY", None)
        self.gemini = GeminiProvider(self.gemini_key) if self.gemini_key else None
        fallback_base = getattr(settings, "OPENROUTER_BASE_URL", None) if getattr(settings, "OPENROUTER_API_KEY", None) else getattr(settings, "OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
        fallback_model = getattr(settings, "OPENROUTER_MODEL", None) if getattr(settings, "OPENROUTER_API_KEY", None) else getattr(settings, "OMNIROUTE_CHAT_MODEL", "gpt-4o")
        self.omniroute = OmniRouteProvider(fallback_base, self.omniroute_key, fallback_model) if self.omniroute_key else None
        self.mock = MockAIProvider()
        self.last_provider_used = "mock" if (not self.gemini_key and not self.omniroute_key) else ("gemini" if self.gemini_key else "omniroute")
        self.last_fallback_occurred = False
        self.last_fallback_reason: Optional[str] = None

    def get_provider_status(self) -> Dict[str, Any]:
        gemini_configured = bool(self.gemini_key)
        omniroute_configured = bool(self.omniroute_key)
        is_fallback_active = self.last_fallback_occurred and self.last_provider_used != "gemini"
        active_provider = "gemini" if not is_fallback_active else "omniroute"
        fallback_label = "OpenRouter" if getattr(settings, "OPENROUTER_API_KEY", None) else "OmniRoute"
        active_display = "Gemini (Primary)" if not is_fallback_active else f"{fallback_label} (Fallback Active)"

        return {
            "primary_provider": "gemini",
            "primary_status": "AVAILABLE" if gemini_configured else "UNAVAILABLE",
            "primary_configured": gemini_configured,
            "fallback_provider": "omniroute",
            "fallback_status": "AVAILABLE" if omniroute_configured else "UNAVAILABLE",
            "fallback_configured": omniroute_configured,
            "active_provider": active_provider,
            "active_display": active_display,
            "last_provider_used": self.last_provider_used,
            "last_fallback_occurred": is_fallback_active,
            "last_fallback_reason": self.last_fallback_reason if is_fallback_active else None,
            "automatic_fallback_enabled": True,
            "routing": "Gemini -> OmniRoute"
        }

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.last_fallback_occurred = False
        self.last_fallback_reason = None
        errors = []

        # 1. Primary: Gemini
        if self.gemini:
            try:
                res = await self.gemini.generate_text(prompt, system_prompt)
                self.last_provider_used = "gemini"
                self.last_fallback_occurred = False
                self.last_fallback_reason = None
                return res
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                    reason = "Gemini rate limit (429)"
                elif "timeout" in err_str or "timed out" in err_str:
                    reason = "Gemini request timeout"
                elif any(c in err_str for c in ["500", "502", "503", "504"]):
                    reason = "Gemini upstream 5xx error"
                else:
                    reason = f"Gemini upstream error ({type(e).__name__})"
                logger.warning(f"[AI FALLBACK] Gemini failed ({reason}). Falling back to OmniRoute...")
                self.last_fallback_occurred = True
                self.last_fallback_reason = reason
                errors.append(f"Gemini: {e}")

        # 2. Fallback: OmniRoute
        if self.omniroute:
            try:
                res = await self.omniroute.generate_text(prompt, system_prompt)
                self.last_provider_used = "omniroute"
                return res
            except Exception as oe:
                logger.error(f"[AI ERROR] OmniRoute fallback failed: {oe}")
                errors.append(f"OmniRoute: {oe}")

        # 3. If any real provider was attempted and failed, raise AIServiceException
        if errors:
            raise AIServiceException(f"All resilient AI providers failed. Errors: {'; '.join(errors)}")

        # 4. Test / offline fallback ONLY when neither provider is configured in dev/test
        if settings.ENVIRONMENT in ["test", "testing", "development"] and not self.gemini and not self.omniroute:
            self.last_provider_used = "mock"
            return await self.mock.generate_text(prompt, system_prompt)

        raise AIServiceException("No AI providers are configured.")

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        self.last_fallback_occurred = False
        self.last_fallback_reason = None
        errors = []

        # 1. Primary: Gemini
        if self.gemini:
            try:
                res = await self.gemini.generate_structured(prompt, system_prompt, response_model)
                self.last_provider_used = "gemini"
                self.last_fallback_occurred = False
                self.last_fallback_reason = None
                return res
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                    reason = "Gemini rate limit (429)"
                elif "timeout" in err_str or "timed out" in err_str:
                    reason = "Gemini request timeout"
                elif any(c in err_str for c in ["500", "502", "503", "504"]):
                    reason = "Gemini upstream 5xx error"
                else:
                    reason = f"Gemini upstream error ({type(e).__name__})"
                logger.warning(f"[AI FALLBACK] Gemini structured failed ({reason}). Falling back to OmniRoute...")
                self.last_fallback_occurred = True
                self.last_fallback_reason = reason
                errors.append(f"Gemini: {e}")

        # 2. Fallback: OmniRoute
        if self.omniroute:
            try:
                res = await self.omniroute.generate_structured(prompt, system_prompt, response_model)
                self.last_provider_used = "omniroute"
                return res
            except Exception as oe:
                logger.error(f"[AI ERROR] OmniRoute structured fallback failed: {oe}")
                errors.append(f"OmniRoute: {oe}")

        # 3. If any real provider was attempted and failed, raise AIServiceException
        if errors:
            raise AIServiceException(f"All resilient AI providers failed for structured output. Errors: {'; '.join(errors)}")

        # 4. Test / offline fallback ONLY when neither provider is configured in dev/test
        if settings.ENVIRONMENT in ["test", "testing", "development"] and not self.gemini and not self.omniroute:
            self.last_provider_used = "mock"
            return await self.mock.generate_structured(prompt, system_prompt, response_model)

        raise AIServiceException("No AI providers are configured.")

    async def generate_embedding(self, text: str) -> List[float]:
        if settings.ENVIRONMENT not in ["test", "testing"]:
            if self.gemini:
                try:
                    return await self.gemini.generate_embedding(text)
                except Exception:
                    pass
            if self.omniroute:
                try:
                    return await self.omniroute.generate_embedding(text)
                except Exception:
                    pass
        return await self.mock.generate_embedding(text)


class OmniRouteServiceAdapter(BaseLLMService):
    """Adapter bridging BaseLLMService to app.ai OmniRoute implementation."""
    def __init__(self):
        from app.ai.services.ai_service import AIService
        from app.ai.services.embedding_service import EmbeddingService
        from app.ai.providers.omniroute import OmniRouteLLMProvider, OmniRouteEmbeddingProvider
        self.ai = AIService(provider=OmniRouteLLMProvider())
        self.emb = EmbeddingService(provider=OmniRouteEmbeddingProvider())

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return await self.ai.generate_text(prompt, system_prompt=system_prompt)

    async def generate_structured(self, prompt: str, system_prompt: Optional[str], response_model: Type[T]) -> T:
        return await self.ai.generate_structured(prompt, system_prompt=system_prompt, response_model=response_model)

    async def generate_embedding(self, text: str) -> List[float]:
        return await self.emb.generate_embedding(text)


# Global singleton resilient service
_resilient_ai_service: Optional[ResilientAIService] = None

def get_ai_service() -> BaseLLMService:
    global _resilient_ai_service
    provider = settings.DEFAULT_AI_PROVIDER.lower()
    if provider in ["gemini", "omniroute", "openrouter", "resilient"]:
        if _resilient_ai_service is None:
            _resilient_ai_service = ResilientAIService()
        return _resilient_ai_service
    elif provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider(settings.OPENAI_API_KEY)
    return MockAIProvider()
