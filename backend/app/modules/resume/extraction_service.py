import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set, Tuple
from app.core.config import settings
from app.modules.ai.service import BaseLLMService, get_ai_service
from app.modules.resume.parsers import get_parser_for_file, validate_resume_file
from app.modules.resume.schemas import (
    StructuredResumeData,
    PersonalDetails,
    EducationItem,
    CategorizedSkills,
    ExperienceItem,
    ProjectItem,
    CertificationItem,
)

UPLOAD_DIR = os.path.abspath(settings.STORAGE_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ResumeExtractionService:
    def __init__(self, ai_service: Optional[BaseLLMService] = None):
        self.ai = ai_service or get_ai_service()

    def save_uploaded_file(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """Saves file to secure upload directory with UUID prefix to prevent collisions and path traversal."""
        validate_resume_file(filename, file_bytes)
        ext = os.path.splitext(filename)[1].lower()
        secure_name = f"{uuid.uuid4()}{ext}"
        target_path = os.path.join(UPLOAD_DIR, secure_name)
        
        with open(target_path, "wb") as f:
            f.write(file_bytes)
            
        return target_path, secure_name

    def extract_raw_text(self, filename: str, file_bytes: bytes) -> str:
        """Extracts text from binary or text file using appropriate parser."""
        validate_resume_file(filename, file_bytes)
        parser = get_parser_for_file(filename)
        return parser.extract_text(file_bytes)

    @staticmethod
    def deduplicate_skills(skills: CategorizedSkills) -> CategorizedSkills:
        """Removes duplicate skills in case-insensitive fashion within and across categories."""
        seen: Set[str] = set()

        def filter_list(items: List[str]) -> List[str]:
            res = []
            for item in items:
                clean = item.strip()
                if not clean:
                    continue
                lower = clean.lower()
                if lower not in seen:
                    seen.add(lower)
                    res.append(clean)
            return res

        return CategorizedSkills(
            programming_languages=filter_list(skills.programming_languages),
            frameworks=filter_list(skills.frameworks),
            databases=filter_list(skills.databases),
            cloud=filter_list(skills.cloud),
            tools=filter_list(skills.tools),
            soft_skills=filter_list(skills.soft_skills),
        )

    def heuristic_fallback_parse(self, raw_text: str) -> StructuredResumeData:
        """Deterministic heuristic fallback parser when LLM structured output is unavailable or fails."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # 1. Personal extraction
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text)
        phone = phone_match.group(0) if phone_match else None

        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', raw_text, re.IGNORECASE)
        linkedin_url = f"https://{linkedin_match.group(0)}" if linkedin_match else None

        github_match = re.search(r'github\.com/[\w-]+', raw_text, re.IGNORECASE)
        github_url = f"https://{github_match.group(0)}" if github_match else None

        name = lines[0] if lines else "Candidate"
        if len(name) > 60 or "@" in name or "http" in name:
            name = "Candidate"

        uncertain_fields = []
        if not email:
            uncertain_fields.append("email")
        if not phone:
            uncertain_fields.append("phone")

        headline = lines[1] if len(lines) > 1 and len(lines[1]) <= 60 else "Candidate Profile"
        summary = lines[1] if len(lines) > 1 and len(lines[1]) > 30 else None

        # Detect candidate location from known tech hubs if present in raw text
        detected_location = None
        loc_candidates = ["Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Noida", "Chennai", "San Francisco", "New York", "London", "Remote"]
        for loc in loc_candidates:
            if re.search(r'\b' + re.escape(loc.lower()) + r'\b', raw_text.lower()):
                detected_location = loc
                break

        personal = PersonalDetails(
            name=name,
            email=email,
            phone=phone,
            location=detected_location,
            linkedin_url=linkedin_url,
            github_url=github_url,
            headline=headline,
            summary=summary,
            is_uncertain=True,
            uncertain_fields=uncertain_fields + ["parsed_via_heuristic_fallback"],
        )

        # 2. Skills extraction via known dictionary match (strictly present in raw_text)
        tech_dict = {
            "programming_languages": ["Python", "JavaScript", "TypeScript", "Go", "Java", "C++", "C#", "Rust", "SQL", "PHP", "Ruby"],
            "frameworks": ["FastAPI", "React", "Next.js", "Django", "Node.js", "Express", "TailwindCSS", "Spring Boot", "Angular", "Vue"],
            "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "pgvector", "Cassandra", "Oracle"],
            "cloud": ["AWS", "GCP", "Azure", "Cloudflare", "Docker", "Kubernetes", "Terraform"],
            "tools": ["Git", "GitHub Actions", "Docker", "Jira", "Postman", "Linux", "VS Code"],
            "soft_skills": ["Team Leadership", "Cross-Functional Collaboration", "System Design", "Agile Methodologies", "Communication"]
        }

        found_skills = {k: [] for k in tech_dict}
        lower_text = raw_text.lower()
        for cat, kw_list in tech_dict.items():
            for kw in kw_list:
                if re.search(r'\b' + re.escape(kw.lower()) + r'\b', lower_text):
                    found_skills[cat].append(kw)

        skills = CategorizedSkills(
            programming_languages=found_skills["programming_languages"],
            frameworks=found_skills["frameworks"],
            databases=found_skills["databases"],
            cloud=found_skills["cloud"],
            tools=found_skills["tools"],
            soft_skills=found_skills["soft_skills"],
        )
        skills = self.deduplicate_skills(skills)

        # 3. Education extraction - only if explicit degree text is present
        education: List[EducationItem] = []
        deg_match = re.search(r'\b(bachelor|master|phd|b\.s\.|m\.s\.|b\.tech|m\.tech|bca|mca)\b', lower_text)
        if deg_match:
            # Extract graduation year if a 4-digit year near 2000-2030 is found
            year_match = re.search(r'\b(20[0-2][0-9])\b', raw_text)
            education.append(EducationItem(
                degree=deg_match.group(0).upper(),
                institution="Institution / University",
                field_of_study="Technical Studies",
                graduation_year=year_match.group(0) if year_match else None,
                cgpa=None,
            ))

        # 4. Experience extraction - do not invent fake companies or roles
        experience: List[ExperienceItem] = []

        # 5. Projects - truthful extraction only
        projects: List[ProjectItem] = []
        if github_url:
            projects.append(ProjectItem(
                name="GitHub Portfolio Projects",
                description="Projects referenced on candidate GitHub profile.",
                technologies=skills.programming_languages[:3],
                links=[github_url]
            ))

        # Estimate years of experience from year ranges found in text
        years_found = [int(y) for y in re.findall(r'\b(20[0-2][0-9])\b', raw_text)]
        total_exp = 0.0
        if len(years_found) >= 2:
            span = max(years_found) - min(years_found)
            total_exp = min(15.0, float(max(0, span)))

        return StructuredResumeData(
            personal=personal,
            education=education,
            skills=skills,
            experience=experience,
            projects=projects,
            certifications=[],
            raw_text=raw_text,
            extraction_timestamp=datetime.now(timezone.utc).isoformat(),
            total_years_experience=total_exp
        )

    async def extract_and_structure_resume(self, raw_text: str) -> StructuredResumeData:
        """Parses raw text using AI service and validates output with strict zero hallucination rules."""
        if not raw_text or len(raw_text.strip()) < 10:
            raise ValueError("Resume text is empty or too short for analysis.")

        system_prompt = (
            "You are an AI Resume Intelligence Extraction Engine.\n"
            "STRICT RULES:\n"
            "1. NEVER invent, assume, or hallucinate information that is not explicitly in the text.\n"
            "2. If a section (e.g. Certifications, Projects, CGPA) is missing, leave the array empty or field as null.\n"
            "3. If any extracted date, phone number, or credential is ambiguous or uncertain, set 'is_uncertain: true'.\n"
            "4. Categorize all extracted skills into: programming_languages, frameworks, databases, cloud, tools, and soft_skills.\n"
            "5. Return strictly valid JSON matching the StructuredResumeData schema."
        )

        prompt = f"Extract structured candidate data from the following resume text:\n\n{raw_text[:8000]}"

        try:
            structured = await self.ai.generate_structured(prompt, system_prompt, StructuredResumeData)
            # Post-process: deduplicate skills
            if structured.skills:
                structured.skills = self.deduplicate_skills(structured.skills)
            structured.raw_text = raw_text
            structured.extraction_timestamp = datetime.now(timezone.utc).isoformat()
            return structured
        except Exception:
            # Gracefully recover using deterministic fallback parser
            fallback = self.heuristic_fallback_parse(raw_text)
            return fallback
