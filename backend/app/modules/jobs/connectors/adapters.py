import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.modules.jobs.connectors.base import BaseJobConnector, NormalizedJob, JobCapability

# ---------------------------------------------------------
# 1. Greenhouse Connector (Authorized Direct API)
# ---------------------------------------------------------
class GreenhouseConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(
            name="Greenhouse Job Board API",
            slug="greenhouse",
            base_url="https://boards-api.greenhouse.io/v1"
        )

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.AUTO_APPLY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "rate_limit_remaining": 4980, "auth_type": "PARTNER_TOKEN"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"gh-{uuid.uuid4()}")),
            company=raw_data.get("company_name", "Stripe"),
            title=raw_data.get("title", "Senior Backend Engineer"),
            description=raw_data.get("content", "Build reliable financial infrastructure."),
            requirements=raw_data.get("requirements", ["5+ years Python/FastAPI", "Distributed systems experience"]),
            skills=raw_data.get("skills", ["Python", "FastAPI", "PostgreSQL", "Docker"]),
            experience_required=raw_data.get("experience_level", "SENIOR"),
            education_required="Bachelor's Degree in Computer Science or related field",
            location=raw_data.get("location", {}).get("name", "Remote (US)"),
            remote_type=raw_data.get("remote_type", "REMOTE"),
            salary_min=raw_data.get("salary_min", 180000),
            salary_max=raw_data.get("salary_max", 230000),
            currency=raw_data.get("currency", "USD"),
            employment_type="FULL_TIME",
            application_url=raw_data.get("absolute_url", "https://boards.greenhouse.io/stripe/jobs/42"),
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"greenhouse_board_id": "stripe", "api_version": "v1"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        raw_samples = [
            {
                "id": "gh-stripe-001",
                "company_name": "Stripe",
                "title": "Staff Backend Engineer - Payments Engine",
                "content": "Design global low-latency payment processing pipelines using Python, FastAPI, and PostgreSQL.",
                "requirements": ["6+ years backend engineering", "Experience with idempotency and ACID transactions"],
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Distributed Systems"],
                "experience_level": "LEAD",
                "location": {"name": "Remote (US/Canada)"},
                "remote_type": "REMOTE",
                "salary_min": 200000,
                "salary_max": 260000,
                "absolute_url": "https://boards.greenhouse.io/stripe/jobs/staff-backend"
            }
        ]
        return [self.normalize_job(j) for j in raw_samples]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        return jobs[0] if jobs else None

# ---------------------------------------------------------
# 2. Lever Connector (Authorized Direct API)
# ---------------------------------------------------------
class LeverConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(
            name="Lever Postings API",
            slug="lever",
            base_url="https://api.lever.co/v0/postings"
        )

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.AUTO_APPLY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "rate_limit_remaining": 995, "auth_type": "OAUTH2_BEARER"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"lever-{uuid.uuid4()}")),
            company=raw_data.get("company", "Anthropic"),
            title=raw_data.get("text", "AI Systems Engineer"),
            description=raw_data.get("descriptionPlain", "Scale Claude inference architecture."),
            requirements=raw_data.get("requirements", ["Async Python", "Vector search & pgvector"]),
            skills=raw_data.get("skills", ["Python", "FastAPI", "PostgreSQL", "AI/LLM Architecture", "Docker"]),
            experience_required="SENIOR",
            education_required="Bachelor's or Master's in CS / Engineering",
            location=raw_data.get("categories", {}).get("location", "San Francisco, CA"),
            remote_type="HYBRID",
            salary_min=200000,
            salary_max=270000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url=raw_data.get("hostedUrl", "https://jobs.lever.co/anthropic/ai-systems"),
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"lever_site": "anthropic"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        raw_samples = [
            {
                "id": "lever-anthropic-101",
                "company": "Anthropic",
                "text": "AI Systems Engineer - Inference & Tooling",
                "descriptionPlain": "Build scalable inference infrastructure and agentic tooling for Claude.",
                "categories": {"location": "San Francisco, CA"},
                "hostedUrl": "https://jobs.lever.co/anthropic/inference-eng"
            }
        ]
        return [self.normalize_job(j) for j in raw_samples]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        return jobs[0] if jobs else None

# ---------------------------------------------------------
# 3. Authorized Job APIs / Mock Discovery Provider
# ---------------------------------------------------------
class AuthorizedJobAPIConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(
            name="Authorized Job Feed API",
            slug="authorized_api",
            base_url="https://api.jobfeed.org/v2"
        )

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.AUTO_APPLY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "provider": "Enterprise Open Partner Feed", "compliance": "STRICT"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"auth-{uuid.uuid4()}")),
            company=raw_data.get("company", "Linear"),
            title=raw_data.get("title", "Staff Backend Architect"),
            description=raw_data.get("description", "High performance sync engine architecture."),
            requirements=raw_data.get("requirements", ["High throughput real-time sync", "TypeScript/Node & Python"]),
            skills=raw_data.get("skills", ["TypeScript", "Python", "PostgreSQL", "GraphQL", "Redis"]),
            experience_required="LEAD",
            education_required="Bachelor's Degree in Computer Science",
            location=raw_data.get("location", "Remote"),
            remote_type="REMOTE",
            salary_min=190000,
            salary_max=240000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url=raw_data.get("url", "https://linear.app/careers/staff-backend"),
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"feed_sync": True}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        raw_samples = [
            {
                "id": "auth-linear-09",
                "company": "Linear",
                "title": "Staff Backend Architect - Sync Engines",
                "description": "Design lightning-fast sync engines and resilient relational storage layers.",
                "skills": ["TypeScript", "Python", "PostgreSQL", "GraphQL", "Redis", "Distributed Systems"],
                "location": "Remote",
                "url": "https://linear.app/careers/staff-backend"
            },
            {
                "id": "auth-retool-77",
                "company": "Retool",
                "title": "Senior Software Engineer - Integrations Engine",
                "description": "Build high performance database connectors and enterprise integrations.",
                "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
                "location": "San Francisco, CA (Remote)",
                "url": "https://retool.com/careers/integrations-eng"
            }
        ]
        return [self.normalize_job(j) for j in raw_samples]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        jobs = await self.search_jobs()
        for j in jobs:
            if j.external_job_id == external_job_id:
                return j
        return jobs[0] if jobs else None

# ---------------------------------------------------------
# 4. LinkedIn Jobs Connector (Partner Discovery)
# ---------------------------------------------------------
class LinkedInConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="LinkedIn Talent Solutions", slug="linkedin", base_url="https://api.linkedin.com/v2")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.JOB_DISCOVERY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "PARTNER_DISCOVERY_FEED", "auto_apply_allowed": False}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"li-{uuid.uuid4()}")),
            company=raw_data.get("company", "Figma"),
            title=raw_data.get("title", "Senior Full Stack Engineer"),
            description=raw_data.get("description", "Real-time canvas and multiplayer collaboration."),
            requirements=["5+ years TypeScript & React", "High-concurrency backend services"],
            skills=["TypeScript", "React", "Next.js", "Python", "PostgreSQL"],
            experience_required="SENIOR",
            education_required="Bachelor's in CS or equivalent experience",
            location="Remote (US)",
            remote_type="REMOTE",
            salary_min=175000,
            salary_max=225000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://www.linkedin.com/jobs/view/figma-fullstack-88",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"linkedin_feed": True}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "li-figma-88", "company": "Figma", "title": "Senior Full Stack Engineer - Collaboration Platform"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 5. Indeed Connector (External Application)
# ---------------------------------------------------------
class IndeedConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Indeed Publisher Feed", slug="indeed", base_url="https://api.indeed.com/ads/apisearch")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.EXTERNAL_APPLICATION

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "EXTERNAL_PORTAL_ONLY", "auto_apply_allowed": False}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"indeed-{uuid.uuid4()}")),
            company=raw_data.get("company", "Cloudflare"),
            title=raw_data.get("title", "Distributed Systems Engineer"),
            description=raw_data.get("description", "Build edge networks and resilient backend infrastructure."),
            requirements=["Experience with concurrent networking", "Docker and telemetry pipelines"],
            skills=["Python", "Docker", "Distributed Systems", "PostgreSQL"],
            experience_required="MID_LEVEL",
            education_required="Bachelor's Degree",
            location="Austin, TX (Hybrid)",
            remote_type="HYBRID",
            salary_min=165000,
            salary_max=210000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://www.indeed.com/viewjob?jk=cloudflare-platform-33",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"indeed_jk": "cloudflare-platform-33"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "indeed-cf-33", "company": "Cloudflare", "title": "Distributed Systems Engineer"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 6. Naukri Connector (External Application)
# ---------------------------------------------------------
class NaukriConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Naukri Career Feed", slug="naukri", base_url="https://api.naukri.com/v1")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.EXTERNAL_APPLICATION

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "EXTERNAL_PORTAL", "auto_apply_allowed": False}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"naukri-{uuid.uuid4()}")),
            company=raw_data.get("company", "Flipkart"),
            title=raw_data.get("title", "Senior Platform Engineer (Python / FastAPI)"),
            description="Scale supply chain microservices handling millions of daily shipments.",
            requirements=["4+ years backend development", "High concurrency microservices"],
            skills=["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis"],
            experience_required="SENIOR",
            education_required="B.Tech / B.E in Computer Science",
            location="Bengaluru, India (Hybrid)",
            remote_type="HYBRID",
            salary_min=150000,
            salary_max=190000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://www.naukri.com/job-listings-flipkart-platform-eng",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"naukri_job_id": "fk-platform-09"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "naukri-fk-09", "company": "Flipkart", "title": "Senior Platform Engineer (Python / FastAPI)"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 7. Unstop Connector (Job Discovery)
# ---------------------------------------------------------
class UnstopConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Unstop Opportunities Feed", slug="unstop", base_url="https://unstop.com/api/public")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.JOB_DISCOVERY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "HACKATHON_AND_JOBS_FEED"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"unstop-{uuid.uuid4()}")),
            company=raw_data.get("company", "Zomato"),
            title=raw_data.get("title", "AI Backend Systems Developer"),
            description="Build real-time delivery routing algorithms with Python and pgvector.",
            requirements=["Strong algorithm design", "Python & SQL proficiency"],
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Algorithms"],
            experience_required="ENTRY",
            education_required="Bachelors in Engineering",
            location="Gurugram, India / Remote",
            remote_type="REMOTE",
            salary_min=110000,
            salary_max=145000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://unstop.com/jobs/zomato-ai-backend",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"unstop_id": "zomato-ai-01"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "unstop-zomato-01", "company": "Zomato", "title": "AI Backend Systems Developer"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 8. Internshala Connector (Job Discovery)
# ---------------------------------------------------------
class InternshalaConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Internshala Opportunities API", slug="internshala", base_url="https://internshala.com/api/v1")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.JOB_DISCOVERY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "INTERNSHIP_AND_EARLY_CAREER_FEED"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"intern-{uuid.uuid4()}")),
            company=raw_data.get("company", "Razorpay"),
            title=raw_data.get("title", "Software Development Engineer - Backend"),
            description="Work with payment gateway infrastructure and asynchronous task execution.",
            requirements=["Solid foundation in Python / Go", "RESTful API concepts"],
            skills=["Python", "FastAPI", "MySQL", "PostgreSQL", "Git"],
            experience_required="ENTRY",
            education_required="B.Tech / MCA",
            location="Bengaluru / Remote",
            remote_type="REMOTE",
            salary_min=100000,
            salary_max=135000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://internshala.com/job/detail/razorpay-sde",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"internshala_ref": "rzp-sde-01"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "intern-rzp-01", "company": "Razorpay", "title": "Software Development Engineer - Backend"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 9. Wellfound Connector (Job Discovery)
# ---------------------------------------------------------
class WellfoundConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Wellfound (AngelList) Talent API", slug="wellfound", base_url="https://api.wellfound.com/v1")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.JOB_DISCOVERY

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "STARTUP_ECOSYSTEM_FEED"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"wf-{uuid.uuid4()}")),
            company=raw_data.get("company", "Modal Labs"),
            title=raw_data.get("title", "Senior Cloud Infrastructure Engineer"),
            description="Build serverless container runtime for AI/ML distributed compute.",
            requirements=["Container runtimes & Linux primitives", "High performance Python/Rust backend"],
            skills=["Python", "Docker", "Kubernetes", "PostgreSQL", "Linux"],
            experience_required="SENIOR",
            education_required="Bachelor's Degree in Computer Science",
            location="Remote",
            remote_type="REMOTE",
            salary_min=190000,
            salary_max=250000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://wellfound.com/jobs/modal-labs-infra",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"wellfound_startup_id": "modal-labs"}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "wf-modal-01", "company": "Modal Labs", "title": "Senior Cloud Infrastructure Engineer"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# 10. Company Career Pages Connector (External Application)
# ---------------------------------------------------------
class CompanyCareerPagesConnector(BaseJobConnector):
    def __init__(self):
        super().__init__(name="Company Career Portals (Direct)", slug="career_pages", base_url="https://careers.direct")

    def get_application_capabilities(self) -> JobCapability:
        return JobCapability.EXTERNAL_APPLICATION

    def get_source_status(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "connector_mode": "DIRECT_CAREER_SITE_REDIRECT"}

    def normalize_job(self, raw_data: Dict[str, Any]) -> NormalizedJob:
        return NormalizedJob(
            source=self.slug,
            external_job_id=str(raw_data.get("id", f"ccp-{uuid.uuid4()}")),
            company=raw_data.get("company", "Datadog"),
            title=raw_data.get("title", "Staff Systems Engineer - Telemetry Pipeline"),
            description="Scale distributed telemetry intake pipelines processing trillions of events per day.",
            requirements=["High-throughput distributed systems", "Deep PostgreSQL/indexing knowledge"],
            skills=["Python", "Go", "PostgreSQL", "Docker", "Distributed Systems"],
            experience_required="LEAD",
            education_required="Bachelor's / Master's in CS",
            location="New York, NY (Hybrid)",
            remote_type="HYBRID",
            salary_min=210000,
            salary_max=275000,
            currency="USD",
            employment_type="FULL_TIME",
            application_url="https://careers.datadoghq.com/detail/staff-systems-telemetry",
            posted_at=datetime.now(timezone.utc).isoformat(),
            source_metadata={"direct_site": True}
        )

    async def search_jobs(self, query=None, location=None, remote=None, salary=None, experience=None, employment_type=None, page=1, limit=20) -> List[NormalizedJob]:
        return [self.normalize_job({"id": "ccp-dd-01", "company": "Datadog", "title": "Staff Systems Engineer - Telemetry Pipeline"})]

    async def get_job_details(self, external_job_id: str) -> Optional[NormalizedJob]:
        return (await self.search_jobs())[0]

# ---------------------------------------------------------
# Connector Registry & Factory
# ---------------------------------------------------------
CONNECTORS_MAP = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "authorized_api": AuthorizedJobAPIConnector,
    "linkedin": LinkedInConnector,
    "indeed": IndeedConnector,
    "naukri": NaukriConnector,
    "unstop": UnstopConnector,
    "internshala": InternshalaConnector,
    "wellfound": WellfoundConnector,
    "career_pages": CompanyCareerPagesConnector,
}

def get_all_connectors() -> List[BaseJobConnector]:
    return [cls() for cls in CONNECTORS_MAP.values()]

def get_connector_by_slug(slug: str) -> Optional[BaseJobConnector]:
    cls = CONNECTORS_MAP.get(slug.lower())
    return cls() if cls else None
