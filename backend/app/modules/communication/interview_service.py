import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.shared.constants import InterviewRoundType
from app.ai.services.ai_service import get_ai_service
from app.modules.communication.drafter import sanitize_prompt_text

logger = logging.getLogger(__name__)

MEETING_URL_PATTERNS = [
    (r"https:\/\/[a-zA-Z0-9_\-\.]*zoom\.us\/[jw]\/[a-zA-Z0-9_\-\.\?\=\&]+", "Zoom"),
    (r"https:\/\/meet\.google\.com\/[a-z]{3}-[a-z]{4}-[a-z]{3}", "Google Meet"),
    (r"https:\/\/teams\.microsoft\.com\/l\/meetup-join\/[a-zA-Z0-9_\-\.\%\/\?\=\&]+", "Microsoft Teams"),
    (r"https:\/\/[a-zA-Z0-9_\-\.]*webex\.com\/[a-zA-Z0-9_\-\.\?\=\&]+", "Webex"),
]


class InterviewIntelligenceService:
    """
    Service for parsing interview invitations, extracting meeting links,
    and generating comprehensive AI Interview Preparation Briefs with STAR stories.
    """

    @classmethod
    def extract_interview_metadata_from_email(cls, subject: str, body: str) -> Dict[str, Any]:
        """Extract meeting URL, platform, and round type heuristic from email content."""
        combined_text = f"{subject}\n{body}"
        
        meeting_url = None
        meeting_platform = None
        for pattern, platform in MEETING_URL_PATTERNS:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                meeting_url = match.group(0)
                meeting_platform = platform
                break

        # Round type detection
        lower_text = combined_text.lower()
        if "system design" in lower_text or "architecture" in lower_text:
            round_type = InterviewRoundType.SYSTEM_DESIGN
        elif "behavioral" in lower_text or "culture fit" in lower_text or "values" in lower_text:
            round_type = InterviewRoundType.BEHAVIORAL
        elif "hiring manager" in lower_text or "director" in lower_text or "vp " in lower_text:
            round_type = InterviewRoundType.HIRING_MANAGER
        elif "coding" in lower_text or "hackerrank" in lower_text or "leetcode" in lower_text or "online assessment" in lower_text:
            round_type = InterviewRoundType.CODING_OA
        elif "panel" in lower_text or "virtual onsite" in lower_text or "onsite loop" in lower_text:
            round_type = InterviewRoundType.PANEL
        elif "final round" in lower_text or "executive" in lower_text:
            round_type = InterviewRoundType.FINAL
        else:
            round_type = InterviewRoundType.TECHNICAL_SCREEN

        return {
            "meeting_url": meeting_url,
            "meeting_platform": meeting_platform,
            "round_type": round_type,
        }

    @classmethod
    async def generate_interview_prep_brief(
        cls,
        candidate_name: str,
        company_name: str,
        job_title: str,
        job_description: Optional[str] = None,
        round_type: InterviewRoundType = InterviewRoundType.TECHNICAL_SCREEN,
        candidate_skills: Optional[List[str]] = None,
        candidate_experiences: Optional[List[Dict[str, Any]]] = None,
        candidate_projects: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI-powered interview cheat sheet with company intel, role focus,
        expected questions, tailored STAR stories, and strategic reverse questions.
        """
        skills_str = ", ".join(candidate_skills[:10]) if candidate_skills else "Software Engineering, Python, Distributed Systems"
        exp_summary = ""
        if candidate_experiences:
            exp_summary = "; ".join([f"{e.get('title', 'Role')} at {e.get('company', 'Company')}" for e in candidate_experiences[:3]])
        proj_summary = ""
        if candidate_projects:
            proj_summary = "; ".join([f"{p.get('name', 'Project')}: {p.get('description', '')[:100]}" for p in candidate_projects[:3]])

        # Try OmniRoute AI
        try:
            ai_service = get_ai_service()
            system_prompt = (
                "You are an elite Silicon Valley interview coach preparing a top-tier candidate for an interview. "
                "Output ONLY a valid JSON object in the exact schema:\n"
                "{\n"
                '  "company_overview": "<Brief company mission & market context>",\n'
                '  "role_summary": "<Key responsibilities and expectations for this role>",\n'
                '  "technical_focus_areas": ["<Topic 1>", "<Topic 2>", "<Topic 3>", "<Topic 4>"],\n'
                '  "expected_questions": [\n'
                '    {"question": "<Question 1>", "category": "Technical", "suggested_talking_points": ["<Point A>", "<Point B>"]},\n'
                '    {"question": "<Question 2>", "category": "Behavioral", "suggested_talking_points": ["<Point A>", "<Point B>"]}\n'
                "  ],\n"
                '  "star_stories": [\n'
                '    {\n'
                '      "title": "<Story Title>",\n'
                '      "situation": "<Context/Problem>",\n'
                '      "task": "<Candidate objective>",\n'
                '      "action": "<Specific technologies and leadership actions taken>",\n'
                '      "result": "<Quantified impact and metrics>",\n'
                '      "relevant_skills": ["<Skill 1>", "<Skill 2>"]\n'
                "    }\n"
                "  ],\n"
                '  "reverse_questions_to_ask": ["<High impact question 1>", "<High impact question 2>", "<High impact question 3>"],\n'
                '  "cheat_sheet_markdown": "<Full formatted markdown cheat sheet>"\n'
                "}\n"
                "Do not output markdown code blocks or text outside JSON."
            )

            prompt = (
                f"Candidate: {candidate_name}\n"
                f"Company: {sanitize_prompt_text(company_name)}\n"
                f"Job Title: {sanitize_prompt_text(job_title)}\n"
                f"Interview Round: {round_type.value}\n"
                f"Job Description: {sanitize_prompt_text(job_description or 'Standard software engineering position')}\n"
                f"Candidate Skills: {skills_str}\n"
                f"Candidate Experiences: {sanitize_prompt_text(exp_summary)}\n"
                f"Candidate Projects: {sanitize_prompt_text(proj_summary)}\n"
            )

            raw_res = await ai_service.complete_prompt(system_prompt=system_prompt, prompt=prompt)
            cleaned = raw_res.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if "company_overview" in parsed and "star_stories" in parsed:
                return parsed
        except Exception as exc:
            logger.warning(f"OmniRoute interview prep brief generation failed ({exc}), using deterministic generator.")

        return cls._generate_fallback_prep_brief(
            candidate_name=candidate_name,
            company_name=company_name,
            job_title=job_title,
            round_type=round_type,
            candidate_skills=candidate_skills or ["Python", "FastAPI", "React", "PostgreSQL", "System Design"],
            candidate_projects=candidate_projects,
        )

    @classmethod
    def _generate_fallback_prep_brief(
        cls,
        candidate_name: str,
        company_name: str,
        job_title: str,
        round_type: InterviewRoundType,
        candidate_skills: List[str],
        candidate_projects: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """High quality deterministic fallback for interview prep brief."""
        primary_skill = candidate_skills[0] if candidate_skills else "Python"
        secondary_skill = candidate_skills[1] if len(candidate_skills) > 1 else "Cloud Architecture"

        company_overview = f"{company_name} is a high-growth technology organization delivering innovative software products. The engineering organization emphasizes clean architecture, scalability, and collaborative engineering excellence."
        role_summary = f"As a {job_title} at {company_name}, you will design, build, and maintain core services, drive architectural decisions, and collaborate cross-functionally to ship reliable features."

        focus_areas = [
            f"Core proficiency in {primary_skill} and backend system fundamentals",
            f"Scalability, caching strategies, and database optimization with {secondary_skill}",
            "API design best practices (REST/GraphQL, idempotency, error handling)",
            "System reliability, testing methodologies, and CI/CD pipelines",
        ]

        expected_questions = [
            {
                "question": f"Walk me through a challenging architectural decision you made using {primary_skill}.",
                "category": "Technical Architecture",
                "suggested_talking_points": [
                    "Explain the trade-offs considered (latency vs cost vs complexity)",
                    "Highlight data modeling decisions and load considerations",
                    "Quantify the business impact and operational stability",
                ],
            },
            {
                "question": "Describe a time you had a technical disagreement with a team member. How did you resolve it?",
                "category": "Behavioral / Collaboration",
                "suggested_talking_points": [
                    "Focus on objective data and benchmark testing over personal preference",
                    "Emphasize empathetic communication and shared team goals",
                    "Share the positive outcome and lessons learned",
                ],
            },
            {
                "question": f"How do you approach debugging a high-latency issue in a production service?",
                "category": "System Design & Troubleshooting",
                "suggested_talking_points": [
                    "Explain observability strategy (metrics, tracing, profiling)",
                    "Isolate database bottlenecks vs network vs compute",
                    "Describe rollback/mitigation before deep root-cause fix",
                ],
            },
        ]

        proj_name = candidate_projects[0].get("name", "Scalable Microservice") if candidate_projects and len(candidate_projects) > 0 else "High-Throughput Processing Engine"
        star_stories = [
            {
                "title": f"Production Architecture Optimization ({proj_name})",
                "situation": f"The existing pipeline was experiencing high latency and bottlenecks under peak traffic.",
                "task": f"Architect and implement a modernized backend solution to reduce response times and support 10x traffic growth.",
                "action": f"Redesigned the data ingestion layer using asynchronous processing, optimized SQL indexes, and implemented multi-tier caching.",
                "result": "Reduced average p99 latency by 65% and supported seamless scaling with zero downtime.",
                "relevant_skills": [primary_skill, "Performance Tuning", "System Architecture"],
            },
            {
                "title": "Cross-Functional Feature Delivery",
                "situation": "Tight deadline for delivering a critical customer-facing feature across distributed services.",
                "task": "Lead technical design, align requirements with product stakeholders, and deliver robust APIs on schedule.",
                "action": "Defined clean API contracts upfront, set up automated integration test suites, and unblocked cross-functional dependencies.",
                "result": "Delivered feature 1 week ahead of deadline with 99.9% test coverage and zero critical production bugs.",
                "relevant_skills": ["Leadership", "API Design", "Agile Execution"],
            },
        ]

        reverse_questions = [
            f"What does a successful first 90 days look like for this {job_title} role at {company_name}?",
            "What are the biggest technical debt or scaling bottlenecks the team is currently addressing?",
            "How does the engineering team balance shipping new features with system health and refactoring?",
            "How would you describe the team's engineering culture around mentorship and technical decision making?",
        ]

        markdown = (
            f"# 🎯 Interview Preparation Brief: {job_title} at {company_name}\n\n"
            f"**Round Type**: `{round_type.value}` | **Candidate**: `{candidate_name}`\n\n"
            f"## 🏢 Company & Role Overview\n"
            f"{company_overview}\n\n"
            f"{role_summary}\n\n"
            f"## 🔑 Key Technical Focus Areas\n"
            + "\n".join([f"- **{f}**" for f in focus_areas])
            + f"\n\n## ❓ Anticipated Questions & Strategy\n"
            + "\n".join([f"### 1. {q['question']}\n*Category: {q['category']}*\n" + "\n".join([f"- {tp}" for tp in q['suggested_talking_points']]) for q in expected_questions])
            + f"\n\n## 🌟 Tailored STAR Stories\n"
            + "\n".join([
                f"### {s['title']}\n"
                f"- **Situation**: {s['situation']}\n"
                f"- **Task**: {s['task']}\n"
                f"- **Action**: {s['action']}\n"
                f"- **Result**: {s['result']}\n"
                f"- *Skills*: {', '.join(s['relevant_skills'])}\n"
                for s in star_stories
            ])
            + f"\n\n## 🙋 Questions to Ask the Interviewer\n"
            + "\n".join([f"- {rq}" for rq in reverse_questions])
        )

        return {
            "company_overview": company_overview,
            "role_summary": role_summary,
            "technical_focus_areas": focus_areas,
            "expected_questions": expected_questions,
            "star_stories": star_stories,
            "reverse_questions_to_ask": reverse_questions,
            "cheat_sheet_markdown": markdown,
        }
