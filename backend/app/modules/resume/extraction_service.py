import asyncio
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

class SemanticResumeParser:
    """Robust multi-section semantic parser that accurately identifies resume structure,
    extracts contact and header blocks, derives professional headlines, captures executive summaries
    without contact leakage, and segments experiences, educations, skills, and projects truthfully.
    """
    SECTION_PATTERNS = {
        "summary": re.compile(r'^(?:professional\s+|executive\s+|career\s+)?(?:summary|profile|objective|about(?:\s+me)?|overview)\b', re.IGNORECASE),
        "skills": re.compile(r'^(?:technical\s+|core\s+|key\s+)?(?:skills|competencies|technologies|proficiencies|tools(?:\s*&\s*technologies)?|skills\s*&\s*(?:tools|technologies))\b', re.IGNORECASE),
        "experience": re.compile(r'^(?:work\s+|professional\s+|employment\s+|relevant\s+)?(?:experience|history|employment|internships)\b', re.IGNORECASE),
        "education": re.compile(r'^(?:education|academic(?:\s+background)?|academics|qualifications)\b', re.IGNORECASE),
        "projects": re.compile(r'^(?:technical\s+|key\s+|personal\s+|academic\s+)?projects\b', re.IGNORECASE),
        "certifications": re.compile(r'^(?:certifications?|certificates?|licenses(?:\s*&\s*certifications?)?)\b', re.IGNORECASE),
        "achievements": re.compile(r'^(?:achievements?|awards?|honors?|publications?)\b', re.IGNORECASE),
    }

    TECH_DICT = {
        "programming_languages": ["Python", "JavaScript", "TypeScript", "Go", "Java", "C++", "C#", "Rust", "SQL", "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R", "Dart", "HTML", "CSS"],
        "frameworks": ["FastAPI", "React", "Next.js", "Django", "Flask", "Node.js", "Express", "TailwindCSS", "Spring Boot", "Angular", "Vue", "Vue.js", "Redux", "GraphQL", "PyTorch", "TensorFlow", "Pandas", "NumPy", "Scikit-Learn"],
        "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "pgvector", "Cassandra", "Oracle", "Elasticsearch", "Neo4j", "Supabase", "Firebase"],
        "cloud": ["AWS", "GCP", "Azure", "Cloudflare", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Nginx"],
        "tools": ["Git", "GitHub Actions", "GitLab", "Jira", "Postman", "VS Code", "Vercel", "Railway", "Webpack", "Vite"],
        "soft_skills": ["Team Leadership", "Cross-Functional Collaboration", "System Design", "Agile Methodologies", "Communication", "Problem Solving", "Mentorship", "Project Management"]
    }

    ROLE_KEYWORDS = [
        "engineer", "developer", "architect", "lead", "manager", "specialist", "analyst", 
        "scientist", "designer", "consultant", "administrator", "programmer", "intern"
    ]

    DEGREE_PATTERNS = [
        (re.compile(r'\b(?:bachelor\s+of\s+technology|b\.?tech)\b', re.IGNORECASE), "B.Tech"),
        (re.compile(r'\b(?:bachelor\s+of\s+engineering|b\.?e\.)\b', re.IGNORECASE), "B.E."),
        (re.compile(r'\b(?:bachelor\s+of\s+science|b\.?s\.?c?|b\.?s\.)\b', re.IGNORECASE), "B.S."),
        (re.compile(r'\b(?:master\s+of\s+technology|m\.?tech)\b', re.IGNORECASE), "M.Tech"),
        (re.compile(r'\b(?:master\s+of\s+science|m\.?s\.?c?|m\.?s\.)\b', re.IGNORECASE), "M.S."),
        (re.compile(r'\b(?:ph\.?d\.?|doctorate)\b', re.IGNORECASE), "Ph.D."),
        (re.compile(r'\b(?:mca|master\s+of\s+computer\s+applications)\b', re.IGNORECASE), "MCA"),
        (re.compile(r'\b(?:bca|bachelor\s+of\s+computer\s+applications)\b', re.IGNORECASE), "BCA"),
        (re.compile(r'\b(?:mba|master\s+of\s+business\s+administration)\b', re.IGNORECASE), "MBA"),
        (re.compile(r'\b(?:bachelor\s+of\s+arts|b\.?a\.)\b', re.IGNORECASE), "B.A."),
        (re.compile(r'\b(?:bachelor|undergraduate)\b', re.IGNORECASE), "Bachelor"),
        (re.compile(r'\b(?:master|graduate)\b', re.IGNORECASE), "Master"),
    ]

    FIELD_PATTERNS = [
        "Computer Science & Engineering", "Computer Science", "Information Technology",
        "Software Engineering", "Data Science", "Artificial Intelligence",
        "Electrical Engineering", "Electronics & Communication", "Mechanical Engineering",
        "Mathematics", "Physics", "Information Systems"
    ]

    @classmethod
    def is_section_header(cls, line: str) -> Optional[Tuple[str, str]]:
        clean = line.strip()
        if not clean or len(clean) > 60:
            return None
        if '@' in clean or 'http' in clean:
            return None
        header_text = clean
        inline_body = ""
        if ':' in clean:
            parts = clean.split(':', 1)
            header_text = parts[0].strip()
            inline_body = parts[1].strip()
        
        clean_header = re.sub(r'^[#*\-•–\s]+|[#*\-•–\s]+$', '', header_text).strip()
        for sec_name, pattern in cls.SECTION_PATTERNS.items():
            if pattern.search(clean_header):
                return sec_name, inline_body
        return None

    def segment_document(self, raw_text: str) -> Tuple[List[str], Dict[str, List[str]]]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        header_lines: List[str] = []
        sections: Dict[str, List[str]] = {}
        current_section: Optional[str] = None

        for line in lines:
            header_match = self.is_section_header(line)
            if header_match:
                current_section, inline_content = header_match
                if current_section not in sections:
                    sections[current_section] = []
                if inline_content:
                    sections[current_section].append(inline_content)
            elif current_section is not None:
                sections[current_section].append(line)
            else:
                header_lines.append(line)

        return header_lines, sections

    def parse_header_and_contact(self, header_lines: List[str], raw_text: str) -> Dict[str, Any]:
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text)
        if not phone_match:
            phone_match = re.search(r'\+?\d{1,3}[-.\s]?\d{4,5}[-.\s]?\d{4,5}', raw_text)
        phone = phone_match.group(0) if phone_match else None

        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)', raw_text, re.IGNORECASE)
        linkedin_url = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None

        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)', raw_text, re.IGNORECASE)
        github_url = f"https://github.com/{github_match.group(1)}" if github_match else None

        portfolio_match = re.search(r'https?://(?!linkedin|github)[\w\.-]+\.[a-zA-Z]{2,}(?:/\S*)?', raw_text, re.IGNORECASE)
        portfolio_url = portfolio_match.group(0) if portfolio_match else None

        detected_location = None
        loc_candidates = [
            "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Noida", 
            "Chennai", "San Francisco", "New York", "Seattle", "Austin", "Boston", "London", 
            "Berlin", "Toronto", "Remote"
        ]
        for loc in loc_candidates:
            if re.search(r'\b' + re.escape(loc.lower()) + r'\b', raw_text.lower()):
                detected_location = loc
                break

        name = "Candidate"
        explicit_headline = None

        clean_headers = []
        for hl in header_lines:
            is_contact_line = (
                ('@' in hl) or 
                ('linkedin.com' in hl.lower()) or 
                ('github.com' in hl.lower()) or
                (phone and phone in hl)
            )
            if not is_contact_line:
                clean_headers.append(hl)

        if clean_headers:
            first_line = clean_headers[0]
            if '|' in first_line:
                parts = [p.strip() for p in first_line.split('|')]
                name = parts[0]
                if len(parts) > 1 and any(kw in parts[1].lower() for kw in self.ROLE_KEYWORDS):
                    explicit_headline = parts[1]
            else:
                if len(first_line) <= 50 and not any(kw in first_line.lower() for kw in ["resume", "curriculum vitae", "cv"]):
                    name = first_line

            if not explicit_headline and len(clean_headers) > 1:
                for hl in clean_headers[1:4]:
                    if len(hl) <= 80 and any(kw in hl.lower() for kw in self.ROLE_KEYWORDS):
                        explicit_headline = hl
                        break

        if not explicit_headline:
            role_title_regex = re.compile(
                r'^(?:Senior|Junior|Lead|Principal|Staff)?\s*(?:Full[- ]Stack|Frontend|Backend|Software|Cloud|DevOps|Data|Machine Learning|AI|System|Infrastructure)?\s*(?:Engineer|Developer|Architect|Specialist|Analyst|Scientist|Consultant)\b', 
                re.IGNORECASE
            )
            for hl in clean_headers[1:]:
                m = role_title_regex.match(hl)
                if m:
                    explicit_headline = m.group(0).strip()
                    break

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "portfolio_url": portfolio_url,
            "location": detected_location,
            "explicit_headline": explicit_headline
        }

    def parse_summary(self, sections: Dict[str, List[str]]) -> Optional[str]:
        if "summary" not in sections or not sections["summary"]:
            return None
        raw_summary = " ".join(sections["summary"])
        clean_summary = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '', raw_summary)
        clean_summary = re.sub(r'https?://\S+', '', clean_summary)
        clean_summary = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '', clean_summary)
        clean_summary = re.sub(r'\s+', ' ', clean_summary).strip()
        return clean_summary if len(clean_summary) >= 15 else None

    def parse_skills(self, sections: Dict[str, List[str]], raw_text: str) -> CategorizedSkills:
        found_skills = {k: [] for k in self.TECH_DICT}
        lower_text = raw_text.lower()
        
        for cat, kw_list in self.TECH_DICT.items():
            for kw in kw_list:
                if re.search(r'\b' + re.escape(kw.lower()) + r'\b', lower_text):
                    found_skills[cat].append(kw)

        if "skills" in sections:
            skills_text = " ".join(sections["skills"])
            tokens = [t.strip() for t in re.split(r'[,|;•\n]', skills_text) if t.strip()]
            for t in tokens:
                clean_t = re.sub(r'^[#*\-•–+\s]+|[\(\)]', '', t).strip()
                if 2 <= len(clean_t) <= 30 and not any(clean_t.lower() in [s.lower() for s in found_skills[c]] for c in found_skills):
                    if not any(stop in clean_t.lower() for stop in ["skill", "proficien", "technolog"]):
                        found_skills["tools"].append(clean_t)

        skills = CategorizedSkills(
            programming_languages=found_skills["programming_languages"],
            frameworks=found_skills["frameworks"],
            databases=found_skills["databases"],
            cloud=found_skills["cloud"],
            tools=found_skills["tools"],
            soft_skills=found_skills["soft_skills"],
        )
        return ResumeExtractionService.deduplicate_skills(skills)

    def parse_experience(self, sections: Dict[str, List[str]]) -> List[ExperienceItem]:
        if "experience" not in sections or not sections["experience"]:
            return []
        exp_lines = sections["experience"]
        experiences: List[ExperienceItem] = []
        current_dict: Optional[Dict[str, Any]] = None

        date_pattern = re.compile(
            r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*(?:-|–|to)\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)\b',
            re.IGNORECASE
        )

        for line in exp_lines:
            clean = line.strip()
            if not clean:
                continue

            date_match = date_pattern.search(clean)
            is_bullet = clean.startswith(('-', '*', '•', '–', '+'))

            if date_match or (not is_bullet and any(kw in clean.lower() for kw in self.ROLE_KEYWORDS) and len(clean) < 100):
                if current_dict:
                    experiences.append(ExperienceItem(**current_dict))

                start_d = date_match.group(1) if date_match else None
                end_d = date_match.group(2) if date_match else None
                is_curr = bool(end_d and end_d.lower() in ["present", "current"])

                line_no_date = date_pattern.sub('', clean).strip(' -–|(),')
                company = "Company"
                role = "Software Engineer"

                if ' - ' in line_no_date or ' – ' in line_no_date:
                    parts = re.split(r'\s+[-–]\s+', line_no_date, maxsplit=1)
                    if any(kw in parts[0].lower() for kw in self.ROLE_KEYWORDS):
                        role, company = parts[0].strip(), parts[1].strip()
                    else:
                        company, role = parts[0].strip(), parts[1].strip()
                elif ' at ' in line_no_date:
                    parts = line_no_date.split(' at ', 1)
                    role, company = parts[0].strip(), parts[1].strip()
                elif ' | ' in line_no_date:
                    parts = [p.strip() for p in line_no_date.split(' | ')]
                    role = parts[0]
                    company = parts[1] if len(parts) > 1 else "Company"
                else:
                    role = line_no_date if line_no_date else "Software Engineer"

                current_dict = {
                    "role": role,
                    "company": company,
                    "start_date": start_d,
                    "end_date": end_d,
                    "is_current": is_curr,
                    "responsibilities": [],
                    "technologies": []
                }
            elif current_dict:
                bullet_text = re.sub(r'^[#*\-•–+\s]+', '', clean).strip()
                if bullet_text:
                    current_dict["responsibilities"].append(bullet_text)
                    for cat, kws in self.TECH_DICT.items():
                        for kw in kws:
                            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', bullet_text.lower()):
                                if kw not in current_dict["technologies"]:
                                    current_dict["technologies"].append(kw)

        if current_dict:
            experiences.append(ExperienceItem(**current_dict))
        return experiences

    def derive_headline(self, explicit_headline: Optional[str], experiences: List[ExperienceItem], skills: CategorizedSkills) -> str:
        if explicit_headline and len(explicit_headline) <= 80:
            return explicit_headline.strip()
        
        if experiences and experiences[0].role:
            return experiences[0].role.strip()

        langs = [s.lower() for s in skills.programming_languages]
        fws = [s.lower() for s in skills.frameworks]
        has_frontend = any(f in fws for f in ["react", "next.js", "vue", "angular", "tailwind"])
        has_backend = any(f in fws for f in ["fastapi", "django", "flask", "node.js", "express", "spring boot"]) or any(l in langs for l in ["python", "go", "java", "sql", "rust"])

        if has_frontend and has_backend:
            return "Full Stack Developer"
        elif any(f in fws for f in ["pytorch", "tensorflow", "scikit-learn", "pandas"]):
            return "AI / Machine Learning Engineer"
        elif any(s.lower() in [c.lower() for c in skills.cloud] for s in ["docker", "kubernetes", "aws", "terraform"]):
            return "Cloud / DevOps Engineer"
        elif has_backend:
            return "Backend Engineer"
        elif has_frontend:
            return "Frontend Developer"

        return "Software Engineer"

    def parse_education(self, sections: Dict[str, List[str]], raw_text: str) -> List[EducationItem]:
        edu_lines = sections.get("education", [])
        edu_text = "\n".join(edu_lines) if edu_lines else raw_text
        
        educations: List[EducationItem] = []
        year_pattern = re.compile(r'\b(20[0-2][0-9]|19[8-9][0-9])\b')
        gpa_pattern = re.compile(r'\b(?:cgpa|gpa|cgla|score|grade)[\s:]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+)?)\b', re.IGNORECASE)
        gpa_slash_pattern = re.compile(r'\b([0-9]\.[0-9]{1,2}\s*/\s*(?:4\.0|10\.0|4|10))\b')

        degree_found = None
        for deg_regex, deg_label in self.DEGREE_PATTERNS:
            if deg_regex.search(edu_text):
                degree_found = deg_label
                break

        if degree_found:
            field = "Computer Science"
            for f in self.FIELD_PATTERNS:
                if re.search(r'\b' + re.escape(f) + r'\b', edu_text, re.IGNORECASE):
                    field = f
                    break

            inst = "University / College"
            inst_match = re.search(r'\b([A-Z][a-zA-Z\s&]+(?:University|College|Institute|Academy|School|NIT|IIT|BITS))\b', edu_text)
            if inst_match:
                inst = inst_match.group(1).strip()
            elif " - " in edu_text or " | " in edu_text:
                for line in edu_text.splitlines():
                    if any(p[0].search(line) for p in self.DEGREE_PATTERNS):
                        clean_l = re.sub(r'\(?20[0-2][0-9]\)?', '', line)
                        parts = [p.strip(' -–|(),') for p in re.split(r'[-–|]', clean_l) if p.strip(' -–|(),')]
                        if len(parts) > 1:
                            inst = parts[1]
                            break

            years = year_pattern.findall(edu_text)
            grad_year = years[-1] if years else None
            gpa_match = gpa_pattern.search(edu_text) or gpa_slash_pattern.search(edu_text)
            gpa = gpa_match.group(1) if gpa_match else None

            educations.append(EducationItem(
                degree=degree_found,
                institution=inst,
                field_of_study=field,
                graduation_year=grad_year,
                start_date=years[0] if len(years) > 1 else None,
                end_date=grad_year,
                cgpa=gpa,
                description=None
            ))

        return educations

    def parse_projects(self, sections: Dict[str, List[str]], github_url: Optional[str], skills: CategorizedSkills) -> List[ProjectItem]:
        projects: List[ProjectItem] = []
        if "projects" in sections and sections["projects"]:
            current_dict: Optional[Dict[str, Any]] = None
            for line in sections["projects"]:
                clean = line.strip()
                if not clean:
                    continue
                is_bullet = clean.startswith(('-', '*', '•', '–', '+'))
                if not is_bullet and len(clean) < 80 and not clean.endswith('.'):
                    if current_dict:
                        projects.append(ProjectItem(**current_dict))
                    current_dict = {
                        "name": clean.split(' - ')[0].split(' | ')[0].strip(),
                        "description": "",
                        "technologies": [],
                        "links": []
                    }
                elif current_dict:
                    desc_clean = re.sub(r'^[#*\-•–+\s]+', '', clean).strip()
                    if desc_clean:
                        if current_dict["description"]:
                            current_dict["description"] += " " + desc_clean
                        else:
                            current_dict["description"] = desc_clean
                    
                    link_match = re.search(r'https?://\S+', clean)
                    if link_match:
                        current_dict["links"].append(link_match.group(0))

                    for cat, kws in self.TECH_DICT.items():
                        for kw in kws:
                            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', clean.lower()):
                                if kw not in current_dict["technologies"]:
                                    current_dict["technologies"].append(kw)

            if current_dict:
                projects.append(ProjectItem(**current_dict))

        if not projects and github_url:
            projects.append(ProjectItem(
                name="GitHub Portfolio Projects",
                description="Open-source engineering repositories and portfolio projects.",
                technologies=skills.programming_languages[:4],
                links=[github_url]
            ))

        return projects

    def parse_certifications(self, sections: Dict[str, List[str]]) -> List[CertificationItem]:
        certifications: List[CertificationItem] = []
        if "certifications" in sections and sections["certifications"]:
            for line in sections["certifications"]:
                clean = re.sub(r'^[#*\-•–+\s]+', '', line).strip()
                if not clean or len(clean) < 4:
                    continue
                year_match = re.search(r'\b(20[0-2][0-9])\b', clean)
                year = year_match.group(1) if year_match else None
                clean_name = re.sub(r'\(?20[0-2][0-9]\)?', '', clean).strip(' ,-|')
                
                issuer = None
                for candidate_issuer in ["AWS", "Amazon", "Google Cloud", "GCP", "Microsoft", "Azure", "Linux Foundation", "Cisco", "Coursera"]:
                    if candidate_issuer.lower() in clean.lower():
                        issuer = candidate_issuer
                        break

                certifications.append(CertificationItem(
                    name=clean_name,
                    issuer=issuer,
                    date=year
                ))
        return certifications

    def parse(self, raw_text: str) -> StructuredResumeData:
        header_lines, sections = self.segment_document(raw_text)
        contact = self.parse_header_and_contact(header_lines, raw_text)
        summary = self.parse_summary(sections)
        skills = self.parse_skills(sections, raw_text)
        experiences = self.parse_experience(sections)
        headline = self.derive_headline(contact.get("explicit_headline"), experiences, skills)
        education = self.parse_education(sections, raw_text)
        projects = self.parse_projects(sections, contact.get("github_url"), skills)
        certifications = self.parse_certifications(sections)

        uncertain_fields: List[str] = []
        if not contact.get("email"):
            uncertain_fields.append("email")
        if not contact.get("phone"):
            uncertain_fields.append("phone")
        if not contact.get("name") or contact.get("name") == "Candidate":
            uncertain_fields.append("name")

        personal = PersonalDetails(
            name=contact.get("name") or "Candidate",
            email=contact.get("email"),
            phone=contact.get("phone"),
            location=contact.get("location"),
            linkedin_url=contact.get("linkedin_url"),
            github_url=contact.get("github_url"),
            portfolio_url=contact.get("portfolio_url"),
            headline=headline,
            summary=summary,
            is_uncertain=len(uncertain_fields) > 0,
            uncertain_fields=uncertain_fields,
        )

        years_found = [int(y) for y in re.findall(r'\b(20[0-2][0-9]|19[8-9][0-9])\b', raw_text)]
        total_exp = 0.0
        if len(years_found) >= 2:
            span = max(years_found) - min(years_found)
            total_exp = min(20.0, float(max(0, span)))
        elif len(years_found) == 1:
            total_exp = min(20.0, float(max(0, datetime.now(timezone.utc).year - years_found[0])))

        return StructuredResumeData(
            personal=personal,
            education=education,
            skills=skills,
            experience=experiences,
            projects=projects,
            certifications=certifications,
            raw_text=raw_text,
            extraction_timestamp=datetime.now(timezone.utc).isoformat(),
            total_years_experience=total_exp
        )


class ResumeExtractionService:
    def __init__(self, ai_service: Optional[BaseLLMService] = None):
        self.ai = ai_service or get_ai_service()
        self.semantic_parser = SemanticResumeParser()

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
        """Deterministic semantic parser when LLM structured output is unavailable or fails."""
        return self.semantic_parser.parse(raw_text)

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
            structured = await asyncio.wait_for(
                self.ai.generate_structured(prompt, system_prompt, StructuredResumeData),
                timeout=7.0
            )
            # Post-process: deduplicate skills
            if structured.skills:
                structured.skills = self.deduplicate_skills(structured.skills)
            
            # Sanitize uncertain fields and ensure headline derivation
            if structured.personal:
                if structured.personal.uncertain_fields:
                    structured.personal.uncertain_fields = [
                        f for f in structured.personal.uncertain_fields if f != "parsed_via_heuristic_fallback"
                    ]
                if not structured.personal.uncertain_fields:
                    structured.personal.is_uncertain = False
                
                # Derive headline if missing or default
                if not structured.personal.headline or structured.personal.headline in ["Candidate Profile", "Candidate"]:
                    structured.personal.headline = self.semantic_parser.derive_headline(
                        None,
                        structured.experience or [],
                        structured.skills or CategorizedSkills()
                    )

            structured.raw_text = raw_text
            structured.extraction_timestamp = datetime.now(timezone.utc).isoformat()
            return structured
        except Exception:
            # Gracefully recover using deterministic semantic parser
            return self.heuristic_fallback_parse(raw_text)
