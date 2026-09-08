import pytest
from app.modules.resume.extraction_service import ResumeExtractionService, SemanticResumeParser
from app.modules.resume.schemas import StructuredResumeData

def test_semantic_parser_with_full_resume():
    raw_resume = """Prashant Kumar
Senior Full Stack Engineer
prashant.dev@example.com | +91 98765 43210 | Bengaluru, India
https://linkedin.com/in/prashantkumar | https://github.com/prashantkumar

PROFESSIONAL SUMMARY
Dynamic and results-driven Senior Full Stack Engineer with 6+ years of experience designing high-throughput microservices and cloud infrastructure using Python, FastAPI, React, and PostgreSQL. Proven track record of scaling distributed systems to millions of requests.

TECHNICAL SKILLS
Programming Languages: Python, JavaScript, TypeScript, Go, SQL
Frameworks: FastAPI, React, Next.js, Django, Node.js, TailwindCSS
Databases: PostgreSQL, Redis, MongoDB:
Cloud & DevOps: AWS, Docker, Kubernetes, CI/CD
tools: Git, GitHub Actions, Postman, Linux

WORK EXPERIENCE
Senior Backend Engineer - Apex Cloud Systems (Jan 2022 - Present)
- Architected asynchronous event-driven services in FastAPI and PostgreSQL.
- Optimized query execution plans reducing P99 latency by 45%.
- Mentored junior engineers and led weekly architecture design reviews.

Software Engineer - Innovate Labs (Jun 2019 - Dec 2021)
- Built interactive frontend applications with React, Next.js, and TypeScript.
- Integrated automated testing pipelines with Docker and GitHub Actions.

EDUCATION
Bachelor of Technology in Computer Science - NIT Trichy (2015 - 2019)
CGLA: 8.7/10

PROJECTS
AI Job Assistant Platform
- Autonomous job application and intelligence studio with semantic matching.
- Technologies: Python, FastAPI, PostgreSQL, Next.js
- Link: https://github.com/prashantkumar/ai-job-assistant

CERTIFICATIONS
AWS Certified Solutions Architect - Associate (2023)
"""
    service = ResumeExtractionService()
    parsed: StructuredResumeData = service.heuristic_fallback_parse(raw_resume)

    # 1. Personal Details
    assert parsed.personal.name == 'Prashant Kumar'
    assert parsed.personal.email == 'prashant.dev@example.com'
    assert parsed.personal.phone == '+91 98765 43210'
    assert parsed.personal.location == 'Bengaluru'
    assert 'prashantkumar' in str(parsed.personal.linkedin_url)
    assert 'prashantkumar' in str(parsed.personal.github_url)

    # 2. Headline & Summary - NO FALLBACK DEFAULTS, NO CONTACT LEAKAGE
    assert parsed.personal.headline == 'Senior Full Stack Engineer'
    assert parsed.personal.headline != 'Candidate Profile'
    assert parsed.personal.summary is not None
    assert 'Dynamic and results-driven' in parsed.personal.summary
    assert 'prashant.dev@example.com' not in parsed.personal.summary
    assert '+91' not in parsed.personal.summary
    assert 'http' not in parsed.personal.summary

    # 3. Uncertain Fields - Clean, no heuristic fallback banner
    assert 'parsed_via_heuristic_fallback' not in parsed.personal.uncertain_fields
    assert parsed.personal.uncertain_fields == []
    assert parsed.personal.is_uncertain is False

    # 4. Skills Categorization & Deduplication
    assert 'Python' in parsed.skills.programming_languages
    assert 'FastAPI' in parsed.skills.frameworks
    assert 'PostgreSQL' in parsed.skills.databases
    assert 'AWS' in parsed.skills.cloud

    # 5. Experience Extraction
    assert len(parsed.experience) >= 2
    assert parsed.experience[0].company == 'Apex Cloud Systems'
    assert parsed.experience[0].role == 'Senior Backend Engineer'
    assert parsed.experience[0].is_current is True
    assert len(parsed.experience[0].responsibilities) >= 2


    # 6. Education Extraction
    assert len(parsed.education) >= 1
    assert parsed.education[0].degree == 'B.Tech'
    assert 'Trichy' in parsed.education[0].institution or 'NIT' in parsed.education[0].institution
    assert parsed.education[0].graduation_year == '2019'
    assert parsed.education[0].cgpa == '8.7/10'

    # 7. Projects & Certifications
    assert len(parsed.projects) >= 1
    assert 'AI' in parsed.projects[0].name
    assert len(parsed.certifications) >= 1
    assert 'AWS' in parsed.certifications[0].name

def test_resume_without_summary_section():
    raw_resume = """John Doe
john.doe@example.com | +1 (415) 555-0199 | San Francisco, CA
https://linkedin.com/in/johndoe

EXPERIENCE
Staff Data Platform Engineer - DataFlow Corp (2020 - Present)
- Built streaming ingest pipelines in Python and PostgreSQLListen.

SKILLS
Python, SQL, PostgreSQL, Docker, AWS
"""
    service = ResumeExtractionService()
    parsed = service.heuristic_fallback_parse(raw_resume)

    # Summary must be None - NEVER the contact line!
    assert parsed.personal.summary is None
    # Headline derived from experience - NEVER Candidate Profile
    assert parsed.personal.headline == 'Staff Data Platform Engineer'
    assert parsed.personal.headline != 'Candidate Profile'
    assert 'parsed_via_heuristic_fallback' not in parsed.personal.uncertain_fields
    assert parsed.personal.is_uncertain is False

def test_resume_missing_contact_reports_truthful_uncertainty():
    raw_resume = """Anonymous Candidate
Passionate Backend Engineer with Python and Docker experience.
"""
    service = ResumeExtractionService()
    parsed = service.heuristic_fallback_parse(raw_resume)

    # Must flag missing email and phone, but NEVER parsed_via_heuristic_fallback
    assert 'email' in parsed.personal.uncertain_fields
    assert 'phone' in parsed.personal.uncertain_fields
    assert 'parsed_via_heuristic_fallback' not in parsed.personal.uncertain_fields
    assert parsed.personal.is_uncertain is True
