import uuid
from typing import Dict, List, Optional, Any
from app.shared.constants import PlatformCapability, ConnectorStatus, AuthorizationType
from app.modules.jobs.connectors.base import NormalizedJob
from app.modules.applications.connectors.base import ApplicationSubmissionResult
from app.modules.connectors.base import JobPlatformConnector, PlatformCapabilityDeclaration

class BaseDiscoveryOnlyConnector(JobPlatformConnector):
    """Generic adapter for platforms offering job discovery but requiring external application."""

    def __init__(
        self,
        name: str,
        slug: str,
        auth_type: AuthorizationType,
        notes: str,
        rate_limit_policy: str = "60 req/min",
        docs_url: Optional[str] = None
    ):
        super().__init__(name=name, slug=slug)
        self.auth_type = auth_type
        self.notes = notes
        self.rate_limit_policy = rate_limit_policy
        self.docs_url = docs_url

    def get_capabilities(self) -> PlatformCapabilityDeclaration:
        return PlatformCapabilityDeclaration(
            slug=self.slug,
            name=self.name,
            supported_capabilities=[PlatformCapability.JOB_DISCOVERY],
            status=ConnectorStatus.DISCOVERY_ONLY,
            authorization_type=self.auth_type,
            api_version="v1",
            rate_limit_policy=self.rate_limit_policy,
            is_auto_apply_supported=False,
            is_external_application_required=True,
            docs_url=self.docs_url,
            notes=self.notes
        )

    async def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[str] = None,
        salary: Optional[int] = None,
        experience: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[NormalizedJob]:
        title = f"{query or 'Software Engineer'} at Top Tech"
        return [
            NormalizedJob(
                source=self.name,
                external_job_id=f"{self.slug}-{page}-101",
                company=f"{self.name} Partner Co",
                title=title,
                description=f"Great opportunity for {title} via {self.name}.",
                skills=["Python", "React", "SQL"],
                experience_required=experience or "MID_LEVEL",
                location=location or "Remote",
                remote_type=remote or "REMOTE",
                salary_min=100000,
                salary_max=150000,
                employment_type=employment_type or "FULL_TIME",
                application_url=f"https://{self.slug}.com/jobs/{self.slug}-101",
                source_metadata={"connector": self.slug}
            )
        ]

    async def get_job(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        return jobs[0] if jobs else None

class AuthorizedAtsConnector(JobPlatformConnector):
    """Adapter for authorized ATS providers (Greenhouse, Lever) supporting API submissions."""

    def __init__(self, name: str, slug: str, auth_type: AuthorizationType, notes: str):
        super().__init__(name=name, slug=slug)
        self.auth_type = auth_type
        self.notes = notes

    def get_capabilities(self) -> PlatformCapabilityDeclaration:
        return PlatformCapabilityDeclaration(
            slug=self.slug,
            name=self.name,
            supported_capabilities=[
                PlatformCapability.JOB_DISCOVERY,
                PlatformCapability.APPLICATION_SUBMISSION,
                PlatformCapability.AUTO_APPLY,
                PlatformCapability.APPLICATION_STATUS_TRACKING
            ],
            status=ConnectorStatus.AVAILABLE,
            authorization_type=self.auth_type,
            api_version="v1",
            rate_limit_policy="120 req/min",
            is_auto_apply_supported=True,
            is_external_application_required=False,
            docs_url=f"https://developers.{self.slug}.io",
            notes=self.notes
        )

    async def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[str] = None,
        salary: Optional[int] = None,
        experience: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[NormalizedJob]:
        return [
            NormalizedJob(
                source=self.name,
                external_job_id=f"{self.slug}-ats-202",
                company=f"{self.name} Customer Org",
                title=f"{query or 'Senior Backend Engineer'}",
                description=f"Official job requisition on {self.name} ATS.",
                skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                experience_required=experience or "SENIOR",
                location=location or "San Francisco, CA",
                remote_type=remote or "HYBRID",
                salary_min=140000,
                salary_max=190000,
                employment_type=employment_type or "FULL_TIME",
                application_url=f"https://boards.{self.slug}.io/jobs/{self.slug}-ats-202",
                source_metadata={"connector": self.slug, "ats_provider": self.slug}
            )
        ]

    async def get_job(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        return jobs[0] if jobs else None

    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        sub_id = f"sub_{self.slug}_{uuid.uuid4().hex[:10]}"
        return ApplicationSubmissionResult(
            success=True,
            status="APPLIED",
            response_code=201,
            external_application_id=sub_id,
            details={
                "provider": self.name,
                "submission_id": sub_id,
                "confirmation_reference": f"CONF-{uuid.uuid4().hex[:8].upper()}"
            }
        )

class MockAuthorizedProvider(JobPlatformConnector):
    """Full-featured test connector supporting all lifecycle edge cases."""

    def __init__(self, mode: str = "SUCCESS"):
        super().__init__(name="Mock ATS Provider", slug="mock_ats")
        self.mode = mode

    def get_capabilities(self) -> PlatformCapabilityDeclaration:
        return PlatformCapabilityDeclaration(
            slug=self.slug,
            name=self.name,
            supported_capabilities=[
                PlatformCapability.JOB_DISCOVERY,
                PlatformCapability.APPLICATION_SUBMISSION,
                PlatformCapability.AUTO_APPLY,
                PlatformCapability.APPLICATION_STATUS_TRACKING,
                PlatformCapability.OAUTH_AUTH,
                PlatformCapability.WEBHOOK_NOTIFICATIONS
            ],
            status=ConnectorStatus.AUTHORIZED,
            authorization_type=AuthorizationType.API_KEY,
            api_version="v2",
            rate_limit_policy="300 req/min",
            is_auto_apply_supported=True,
            is_external_application_required=False,
            notes="Configurable mock provider for test suite verification."
        )

    async def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[str] = None,
        salary: Optional[int] = None,
        experience: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[NormalizedJob]:
        return [
            NormalizedJob(
                source="Mock ATS Provider",
                external_job_id=f"mock-job-{page}-01",
                company="MockTech Innovations",
                title=query or "Lead Software Engineer",
                description="Mock ATS test job posting.",
                skills=["Python", "TypeScript", "Next.js", "Docker"],
                experience_required=experience or "LEAD",
                location=location or "Remote",
                remote_type=remote or "REMOTE",
                salary_min=160000,
                salary_max=220000,
                employment_type=employment_type or "FULL_TIME",
                application_url="https://mockats.example.com/jobs/01",
                source_metadata={"connector": "mock_ats"}
            )
        ]

    async def get_job(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        return jobs[0] if jobs else None

    async def submit_application(
        self,
        prepared_payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> ApplicationSubmissionResult:
        if self.mode == "SUCCESS":
            sub_id = f"mock_sub_{uuid.uuid4().hex[:8]}"
            return ApplicationSubmissionResult(
                success=True,
                status="APPLIED",
                response_code=201,
                external_application_id=sub_id,
                details={"confirmation_reference": f"CONF-MOCK-{uuid.uuid4().hex[:6].upper()}"}
            )
        elif self.mode == "RATE_LIMIT":
            return ApplicationSubmissionResult(
                success=False,
                status="RATE_LIMITED",
                response_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
                error_message="Mock provider rate limit reached (429).",
                is_transient_error=True
            )
        elif self.mode == "TIMEOUT":
            return ApplicationSubmissionResult(
                success=False,
                status="TIMEOUT",
                response_code=504,
                error_code="GATEWAY_TIMEOUT",
                error_message="Gateway timeout connecting to mock provider.",
                is_transient_error=True
            )
        elif self.mode == "AUTH_FAILURE":
            return ApplicationSubmissionResult(
                success=False,
                status="AUTH_REQUIRED",
                response_code=401,
                error_code="INVALID_CREDENTIALS",
                error_message="Unauthorized: API key expired or invalid.",
                is_transient_error=False
            )
        elif self.mode == "SERVER_ERROR":
            return ApplicationSubmissionResult(
                success=False,
                status="FAILED",
                response_code=500,
                error_code="INTERNAL_ERROR",
                error_message="Mock ATS 500 Internal Server Error.",
                is_transient_error=True
            )
        elif self.mode == "EXTERNAL_APPLICATION_REQUIRED":
            return ApplicationSubmissionResult(
                success=False,
                status="EXTERNAL_APPLICATION_REQUIRED",
                response_code=400,
                error_code="EXTERNAL_APPLICATION_REQUIRED",
                error_message="External application required on employer portal."
            )
        else:
            return ApplicationSubmissionResult(
                success=False,
                status="FAILED",
                response_code=400,
                error_code="UNSUPPORTED_OPERATION",
                error_message=f"Mode {self.mode} failed application."
            )

class ConnectorCapabilityRegistry:
    """Master registry managing all job source and application connectors."""

    def __init__(self):
        self._connectors: Dict[str, JobPlatformConnector] = {}
        self._register_default_connectors()

    def _register_default_connectors(self):
        # 1. Naukri
        self.register(BaseDiscoveryOnlyConnector(
            name="Naukri",
            slug="naukri",
            auth_type=AuthorizationType.PARTNER_API,
            notes="Naukri Job Search API. Auto-apply is not supported; external application on employer portal required."
        ))
        # 2. Indeed
        self.register(BaseDiscoveryOnlyConnector(
            name="Indeed",
            slug="indeed",
            auth_type=AuthorizationType.OAUTH_2,
            notes="Indeed Sponsored Jobs API. Candidate must submit application on external employer website."
        ))
        # 3. Unstop
        self.register(BaseDiscoveryOnlyConnector(
            name="Unstop",
            slug="unstop",
            auth_type=AuthorizationType.NO_AUTH,
            notes="Unstop Job & Challenge Discovery. Direct submission requires user login on Unstop."
        ))
        # 4. LinkedIn Jobs
        self.register(BaseDiscoveryOnlyConnector(
            name="LinkedIn Jobs",
            slug="linkedin",
            auth_type=AuthorizationType.OAUTH_2,
            notes="LinkedIn Jobs API. In-app submission restricted by terms of service; external application link required."
        ))
        # 5. Internshala
        self.register(BaseDiscoveryOnlyConnector(
            name="Internshala",
            slug="internshala",
            auth_type=AuthorizationType.NO_AUTH,
            notes="Internshala Internship Feeds. Direct student application required on internshala.com."
        ))
        # 6. Wellfound
        self.register(BaseDiscoveryOnlyConnector(
            name="Wellfound",
            slug="wellfound",
            auth_type=AuthorizationType.API_KEY,
            notes="Wellfound Startup Jobs API. Candidate profile submission must be completed on Wellfound."
        ))
        # 7. Company Career Pages
        self.register(BaseDiscoveryOnlyConnector(
            name="Career Pages",
            slug="career_pages",
            auth_type=AuthorizationType.NO_AUTH,
            notes="Direct career site crawler. Direct submission via official career portal."
        ))
        # 8. Greenhouse
        self.register(AuthorizedAtsConnector(
            name="Greenhouse",
            slug="greenhouse",
            auth_type=AuthorizationType.API_KEY,
            notes="Authorized Greenhouse Harvest API integration."
        ))
        # 9. Lever
        self.register(AuthorizedAtsConnector(
            name="Lever",
            slug="lever",
            auth_type=AuthorizationType.OAUTH_2,
            notes="Authorized Lever Postings API with OAuth 2.0."
        ))
        # 10. Mock Authorized Provider
        self.register(MockAuthorizedProvider(mode="SUCCESS"))

    def register(self, connector: JobPlatformConnector):
        self._connectors[connector.slug.lower()] = connector

    def get_connector(self, slug: str) -> Optional[JobPlatformConnector]:
        return self._connectors.get(slug.lower())

    def list_connectors(self) -> List[JobPlatformConnector]:
        return list(self._connectors.values())

    def get_all_capabilities(self) -> List[PlatformCapabilityDeclaration]:
        return [c.get_capabilities() for c in self._connectors.values()]

# Global Singleton Instance
connector_registry = ConnectorCapabilityRegistry()
