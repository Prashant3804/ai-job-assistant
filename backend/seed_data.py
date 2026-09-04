import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.database.session import AsyncSessionLocal, init_db
from app.database.models import (
    User, UserProfile, CandidateSkill, Education, Experience, Project, JobPreference,
    JobSource, Job, JobMatch, Application, ApplicationEvent,
    EmailAccount, EmailMessage, Recruiter, ChatConversation, ChatMessage,
    Notification, SystemSetting
)
from app.core.security import get_password_hash
from app.shared.constants import (
    ConnectorCapabilityStatus, ApplicationStatus, ApplicationEventType,
    EmailProvider, EmailClassification, ChatSenderType, ChatContextType, NotificationType
)
from app.modules.jobs.service import JobService
from app.modules.matching.service import MatchingService
from app.modules.ai.service import MockAIProvider

async def seed():
    print("Initializing schema...")
    await init_db()

    async with AsyncSessionLocal() as db:
        print("Seeding database with realistic data...")

        # 1. Check if user already exists
        from sqlalchemy import select
        res = await db.execute(select(User).where(User.email == "alex.dev@example.com"))
        if res.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # 2. Seed User
        user = User(
            id=uuid.uuid4(),
            email="alex.dev@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Alex Mercer",
            is_active=True,
            is_verified=True,
            role="CANDIDATE"
        )
        db.add(user)
        await db.flush()

        # 3. User Profile
        profile = UserProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            headline="Senior Full Stack & AI Systems Engineer",
            summary="Senior Engineer with 5+ years of experience designing high-throughput distributed backends, REST/GraphQL APIs, and modern React/Next.js interfaces. Proficient with FastAPI, PostgreSQL, and LLM orchestration.",
            location="San Francisco, CA (Remote)",
            remote_preference="REMOTE",
            years_of_experience=5.0,
            target_roles=["Senior Backend Engineer", "AI Systems Engineer", "Full Stack Architect"],
            linkedin_url="https://linkedin.com/in/alexmercer-dev",
            github_url="https://github.com/alexmercer-dev",
            portfolio_url="https://alexmercer.dev"
        )
        db.add(profile)
        await db.flush()

        # 4. Candidate Skills
        skills = [
            ("Python", "TECHNICAL", "EXPERT", 5.0),
            ("FastAPI", "TECHNICAL", "EXPERT", 4.0),
            ("PostgreSQL", "TECHNICAL", "ADVANCED", 5.0),
            ("TypeScript", "TECHNICAL", "ADVANCED", 4.0),
            ("React / Next.js", "TECHNICAL", "ADVANCED", 4.0),
            ("Docker", "TOOL", "ADVANCED", 4.0),
            ("pgvector & Embeddings", "DOMAIN", "ADVANCED", 2.0),
            ("Distributed Systems", "DOMAIN", "ADVANCED", 4.0),
            ("Redis", "TOOL", "ADVANCED", 3.0),
            ("GraphQL", "TECHNICAL", "INTERMEDIATE", 2.0),
        ]
        for name, cat, prof_level, yrs in skills:
            db.add(CandidateSkill(
                user_profile_id=profile.id,
                name=name,
                category=cat,
                proficiency_level=prof_level,
                years_experience=yrs,
                is_verified=True
            ))

        # 5. Experience
        db.add(Experience(
            user_profile_id=profile.id,
            company_name="Apex Cloud Systems",
            title="Senior Backend Engineer",
            location="San Francisco, CA",
            employment_type="FULL_TIME",
            start_date="2023-01",
            end_date="Present",
            is_current=True,
            description="Leading backend infrastructure and AI pipeline architecture.",
            bullet_points=[
                "Architected asynchronous microservices with FastAPI and PostgreSQL pgvector, cutting p99 latency by 42%.",
                "Engineered vector retrieval pipelines for search across 10M+ documents with sub-50ms latency.",
                "Mentored 6 junior engineers and established automated CI/CD workflows."
            ],
            technologies=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]
        ))
        db.add(Experience(
            user_profile_id=profile.id,
            company_name="Nexus Tech Labs",
            title="Full Stack Software Engineer",
            location="Austin, TX",
            employment_type="FULL_TIME",
            start_date="2021-03",
            end_date="2022-12",
            is_current=False,
            description="Built scalable customer-facing web applications and analytics dashboards.",
            bullet_points=[
                "Developed high-performance Next.js web application used by 120k monthly active users.",
                "Optimized relational database queries reducing database CPU load by 35%."
            ],
            technologies=["React", "TypeScript", "Node.js", "PostgreSQL", "TailwindCSS"]
        ))

        # 6. Education
        db.add(Education(
            user_profile_id=profile.id,
            institution="University of California, Berkeley",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date="2017",
            end_date="2021",
            gpa="3.85",
            description="Dean's Honor List, coursework in Distributed Systems, Algorithms, and Database Management."
        ))

        # 7. Projects
        db.add(Project(
            user_profile_id=profile.id,
            title="AI Vector Search & Ranking Engine",
            description="Open-source hybrid keyword + semantic similarity search engine built with FastAPI and PostgreSQL pgvector.",
            url="https://github.com/alexmercer-dev/ai-search-engine",
            github_url="https://github.com/alexmercer-dev/ai-search-engine",
            technologies=["Python", "FastAPI", "PostgreSQL", "pgvector", "Docker"],
            start_date="2024-01",
            end_date="2024-05"
        ))

        # 8. Job Preferences
        db.add(JobPreference(
            user_id=user.id,
            desired_titles=["Senior Backend Engineer", "AI Systems Engineer", "Staff Engineer"],
            desired_locations=["Remote", "San Francisco, CA", "New York, NY", "Austin, TX"],
            remote_types=["REMOTE", "HYBRID"],
            min_base_salary=150000,
            max_base_salary=220000,
            currency="USD",
            target_industries=["Developer Tools", "AI/ML", "Fintech", "Cloud Infrastructure"],
            sponsorship_required=False
        ))

        # 9. Job Sources (with explicit Connector Capability Statuses)
        source_greenhouse = JobSource(
            id=uuid.uuid4(),
            name="Greenhouse Direct API",
            slug="greenhouse",
            base_url="https://api.greenhouse.io/v1",
            connector_type="DIRECT_API",
            capability_status=ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value,
            is_active=True
        )
        source_lever = JobSource(
            id=uuid.uuid4(),
            name="Lever Candidate API",
            slug="lever",
            base_url="https://api.lever.co/v1",
            connector_type="DIRECT_API",
            capability_status=ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value,
            is_active=True
        )
        source_linkedin = JobSource(
            id=uuid.uuid4(),
            name="LinkedIn Talent Solutions API",
            slug="linkedin",
            base_url="https://api.linkedin.com/v2",
            connector_type="PARTNER_FEED",
            capability_status=ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value,
            is_active=True
        )
        source_workday = JobSource(
            id=uuid.uuid4(),
            name="Workday Career Portal",
            slug="workday",
            base_url="https://myworkdayjobs.com",
            connector_type="PORTAL_EXTERNAL",
            capability_status=ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value,
            is_active=True
        )
        db.add_all([source_greenhouse, source_lever, source_linkedin, source_workday])
        await db.flush()

        # 10. Realistic Production Jobs
        mock_ai = MockAIProvider()
        job_defs = [
            {
                "source": source_greenhouse,
                "ext_id": "stripe-backend-042",
                "title": "Senior Backend Engineer - Financial Infrastructure",
                "company": "Stripe",
                "loc": "Remote (US/Canada)",
                "remote": "REMOTE",
                "emp": "FULL_TIME",
                "min_sal": 180000,
                "max_sal": 230000,
                "skills": ["Python", "FastAPI", "PostgreSQL", "Distributed Systems", "Docker", "Redis"],
                "pref_skills": ["Kafka", "Financial Protocols"],
                "exp": "SENIOR",
                "desc": "Stripe is looking for a Senior Backend Engineer to design and scale the next generation of global financial infrastructure. You will build high-throughput transaction processing systems with sub-millisecond reliability using Python, FastAPI, and PostgreSQL."
            },
            {
                "source": source_lever,
                "ext_id": "anthropic-ai-eng-101",
                "title": "AI Systems Engineer - Inference & Tooling",
                "company": "Anthropic",
                "loc": "San Francisco, CA (Hybrid)",
                "remote": "HYBRID",
                "emp": "FULL_TIME",
                "min_sal": 200000,
                "max_sal": 270000,
                "skills": ["Python", "FastAPI", "PostgreSQL", "AI/LLM Architecture", "Docker", "pgvector & Embeddings"],
                "pref_skills": ["PyTorch", "vLLM", "Triton"],
                "exp": "SENIOR",
                "desc": "Join Anthropic's systems engineering team to build scalable inference infrastructure and agentic developer tooling for Claude. We value strong Python backend foundations, async concurrent programming, and deep knowledge of vector search architectures."
            },
            {
                "source": source_linkedin,
                "ext_id": "figma-fullstack-88",
                "title": "Senior Full Stack Engineer - Collaboration Platform",
                "company": "Figma",
                "loc": "Remote (US)",
                "remote": "REMOTE",
                "emp": "FULL_TIME",
                "min_sal": 175000,
                "max_sal": 225000,
                "skills": ["TypeScript", "React / Next.js", "Python", "PostgreSQL", "WebSockets"],
                "pref_skills": ["Wasm", "CRDTs"],
                "exp": "SENIOR",
                "desc": "Figma is seeking a Senior Full Stack Engineer to lead realtime collaboration tooling. You will build responsive React interfaces and high-concurrency backend services."
            },
            {
                "source": source_greenhouse,
                "ext_id": "linear-lead-eng-09",
                "title": "Staff Backend Architect",
                "company": "Linear",
                "loc": "Remote",
                "remote": "REMOTE",
                "emp": "FULL_TIME",
                "min_sal": 190000,
                "max_sal": 240000,
                "skills": ["TypeScript", "Python", "PostgreSQL", "GraphQL", "Redis", "Distributed Systems"],
                "pref_skills": ["Sync Engines"],
                "exp": "LEAD",
                "desc": "Linear is looking for a Staff Backend Architect to design lightning-fast sync engines and resilient relational storage layers."
            },
            {
                "source": source_workday,
                "ext_id": "cloudflare-platform-33",
                "title": "Distributed Systems Engineer",
                "company": "Cloudflare",
                "loc": "Austin, TX (Hybrid)",
                "remote": "HYBRID",
                "emp": "FULL_TIME",
                "min_sal": 165000,
                "max_sal": 210000,
                "skills": ["Python", "Docker", "Distributed Systems", "PostgreSQL"],
                "pref_skills": ["Rust", "eBPF"],
                "exp": "MID_LEVEL",
                "desc": "Help build a better Internet at Cloudflare. You will develop edge routing services, telemetry collectors, and resilient backend pipelines."
            },
            {
                "source": source_lever,
                "ext_id": "retool-eng-77",
                "title": "Senior Software Engineer - Integrations Engine",
                "company": "Retool",
                "loc": "San Francisco, CA (Remote)",
                "remote": "REMOTE",
                "emp": "FULL_TIME",
                "min_sal": 170000,
                "max_sal": 215000,
                "skills": ["Python", "FastAPI", "React / Next.js", "TypeScript", "PostgreSQL"],
                "pref_skills": ["OAuth2", "SAML"],
                "exp": "SENIOR",
                "desc": "Retool makes building internal tools fast and powerful. We are looking for a Senior Engineer to expand our connectors and API engine."
            }
        ]

        created_jobs = []
        for jd in job_defs:
            dedup_hash = JobService.generate_deduplication_hash(jd["company"], jd["title"], jd["ext_id"])
            emb = await mock_ai.generate_embedding(f"{jd['title']} at {jd['company']}. {jd['desc']}")
            job = Job(
                id=uuid.uuid4(),
                job_source_id=jd["source"].id,
                external_id=jd["ext_id"],
                title=jd["title"],
                company_name=jd["company"],
                location=jd["loc"],
                remote_type=jd["remote"],
                employment_type=jd["emp"],
                salary_min=jd["min_sal"],
                salary_max=jd["max_sal"],
                salary_currency="USD",
                description=jd["desc"],
                requirements_summary=jd["desc"][:200] + "...",
                required_skills=jd["skills"],
                preferred_skills=jd["pref_skills"],
                experience_level=jd["exp"],
                apply_url=f"https://jobs.example.com/{jd['ext_id']}",
                deduplication_hash=dedup_hash,
                embedding=emb,
                is_active=True,
                posted_at=datetime.now(timezone.utc) - timedelta(days=2)
            )
            db.add(job)
            created_jobs.append(job)
        await db.flush()

        # 11. Compute Job Matches
        matching_service = MatchingService(db, mock_ai)
        for job in created_jobs:
            await matching_service.compute_or_get_match(user, job)

        # 12. Create Tracked Applications
        stripe_job = created_jobs[0]
        anthropic_job = created_jobs[1]
        figma_job = created_jobs[2]
        linear_job = created_jobs[3]

        app1 = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            job_id=stripe_job.id,
            status=ApplicationStatus.INTERVIEW_SCHEDULED.value,
            applied_date=datetime.now(timezone.utc) - timedelta(days=5),
            submission_method="DIRECT_API",
            notes="Passed recruiter screen. Technical architecture round scheduled for Thursday at 2 PM EST.",
            follow_up_date=datetime.now(timezone.utc) + timedelta(days=2)
        )
        db.add(app1)
        await db.flush()

        db.add(ApplicationEvent(
            application_id=app1.id,
            event_type=ApplicationEventType.CREATED.value,
            new_status="SUBMITTED",
            title="Application Submitted via Greenhouse API",
            description="Submitted master resume and tailored cover letter."
        ))
        db.add(ApplicationEvent(
            application_id=app1.id,
            event_type=ApplicationEventType.INTERVIEW_INVITED.value,
            old_status="SUBMITTED",
            new_status="INTERVIEW_SCHEDULED",
            title="Invited to Technical Architecture Interview",
            description="Recruiter Sarah Jenkins scheduled the 60-minute technical interview."
        ))

        app2 = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            job_id=anthropic_job.id,
            status=ApplicationStatus.OFFER_RECEIVED.value,
            applied_date=datetime.now(timezone.utc) - timedelta(days=14),
            submission_method="DIRECT_API",
            notes="Completed final round presentation. Received formal offer letter ($245,000 base + equity)!",
            follow_up_date=datetime.now(timezone.utc) + timedelta(days=5)
        )
        db.add(app2)
        await db.flush()

        db.add(ApplicationEvent(
            application_id=app2.id,
            event_type=ApplicationEventType.OFFER_RECEIVED.value,
            old_status="INTERVIEW_SCHEDULED",
            new_status="OFFER_RECEIVED",
            title="Offer Letter Received",
            description="Formal offer letter sent via email by Lead Recruiter."
        ))

        app3 = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            job_id=figma_job.id,
            status=ApplicationStatus.UNDER_REVIEW.value,
            applied_date=datetime.now(timezone.utc) - timedelta(days=3),
            submission_method="EXTERNAL_PORTAL",
            notes="Applied through Figma careers page. Profile under review by engineering director."
        )
        db.add(app3)

        app4 = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            job_id=linear_job.id,
            status=ApplicationStatus.DRAFT.value,
            applied_date=None,
            submission_method="MANUAL",
            notes="Resume tailored and ready. Reviewing cover letter highlights."
        )
        db.add(app4)
        await db.flush()

        # 13. Email Account & Recruiter Messages
        email_acct = EmailAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=EmailProvider.GMAIL.value,
            email_address="alex.dev@gmail.com",
            is_active=True,
            last_synced_at=datetime.now(timezone.utc)
        )
        db.add(email_acct)
        await db.flush()

        db.add(EmailMessage(
            id=uuid.uuid4(),
            email_account_id=email_acct.id,
            external_message_id="msg-stripe-001",
            sender_email="sarah.jenkins@stripe.com",
            sender_name="Sarah Jenkins",
            recipient_email="alex.dev@gmail.com",
            subject="Interview Confirmation: Stripe Senior Backend Infrastructure",
            body_text="Hi Alex,\n\nWe were really impressed with your technical background and vector search project! We'd love to invite you for a 60-minute technical architecture interview with our Principal Engineer this Thursday.\n\nPlease confirm if 2:00 PM EST works for you.",
            received_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_recruiter=True,
            classification=EmailClassification.INTERVIEW_INVITATION.value,
            confidence_score=0.98,
            application_id=app1.id
        ))

        db.add(EmailMessage(
            id=uuid.uuid4(),
            email_account_id=email_acct.id,
            external_message_id="msg-anthropic-002",
            sender_email="elena.rostova@anthropic.com",
            sender_name="Elena Rostova",
            recipient_email="alex.dev@gmail.com",
            subject="Anthropic - Offer of Employment (AI Systems Engineer)",
            body_text="Dear Alex,\n\nOn behalf of Anthropic, I am thrilled to extend an offer of employment for the position of Senior AI Systems Engineer. Attached you will find your official compensation package and equity terms.\n\nWe look forward to welcoming you to the team!",
            received_at=datetime.now(timezone.utc) - timedelta(hours=6),
            is_recruiter=True,
            classification=EmailClassification.OFFER.value,
            confidence_score=0.99,
            application_id=app2.id
        ))

        # 14. Recruiter Contacts
        db.add(Recruiter(
            user_id=user.id,
            name="Sarah Jenkins",
            email="sarah.jenkins@stripe.com",
            company_name="Stripe",
            title="Senior Technical Recruiter",
            linkedin_url="https://linkedin.com/in/sarahjenkins-talent",
            notes="Responsive, coordinating technical rounds."
        ))
        db.add(Recruiter(
            user_id=user.id,
            name="Elena Rostova",
            email="elena.rostova@anthropic.com",
            company_name="Anthropic",
            title="Lead Engineering Recruiter",
            linkedin_url="https://linkedin.com/in/elena-rostova-anthropic",
            notes="Primary contact for AI Systems offer negotiations."
        ))

        # 15. Initial Chat Conversation
        chat_conv = ChatConversation(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Job Search & Application Advisor",
            context_type=ChatContextType.GENERAL.value
        )
        db.add(chat_conv)
        await db.flush()

        db.add(ChatMessage(
            conversation_id=chat_conv.id,
            sender_type=ChatSenderType.ASSISTANT.value,
            content="Welcome back, Alex! I've analyzed your candidate profile and active applications.\n\n🎉 **Update**: You have an active offer from Anthropic ($245k base) and an upcoming Technical Architecture Interview with Stripe this Thursday at 2:00 PM EST.\n\nHow would you like to prepare today?",
            structured_payload={"quick_actions": ["Prepare for Stripe Interview", "Compare Compensation & Offers", "Find new >90% Match Roles"]}
        ))

        # 16. Notifications
        db.add(Notification(
            user_id=user.id,
            title="🎉 Offer Received!",
            message="Anthropic has sent a formal employment offer for AI Systems Engineer.",
            notification_type=NotificationType.STATUS_UPDATE.value,
            is_read=False,
            action_url="/applications"
        ))
        db.add(Notification(
            user_id=user.id,
            title="📅 Interview Scheduled",
            message="Stripe Technical Architecture round confirmed for Thursday 2:00 PM EST.",
            notification_type=NotificationType.EMAIL_CLASSIFIED.value,
            is_read=False,
            action_url="/interviews"
        ))

        # 17. System Settings
        db.add(SystemSetting(
            key="ai_match_weights",
            value={"skills": 0.35, "semantic": 0.35, "experience": 0.15, "preference": 0.15},
            description="Configurable scoring weights for job match explainability engine.",
            is_public=True
        ))

        await db.commit()
        print("Database seeded successfully with realistic data!")

if __name__ == "__main__":
    asyncio.run(seed())
