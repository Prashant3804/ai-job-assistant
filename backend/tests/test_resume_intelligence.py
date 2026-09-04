import io
import pytest
import docx
import fitz
from fastapi import HTTPException
from app.modules.resume.parsers import (
    PDFResumeParser,
    DocxResumeParser,
    PlainTextResumeParser,
    validate_resume_file,
    get_parser_for_file,
)
from app.modules.resume.extraction_service import ResumeExtractionService
from app.modules.resume.schemas import (
    CategorizedSkills,
    PersonalDetails,
    StructuredResumeData,
)
from app.modules.ai.service import MockAIProvider

def create_synthetic_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_synthetic_docx(text_paragraphs: list, table_data: list = None) -> bytes:
    doc = docx.Document()
    for p in text_paragraphs:
        doc.add_paragraph(p)
    if table_data:
        table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
        for r_idx, row in enumerate(table_data):
            for c_idx, val in enumerate(row):
                table.cell(r_idx, c_idx).text = str(val)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 1. PDF Extraction Test
def test_pdf_extraction():
    sample_text = (
        "Alex Mercer\n"
        "alex.mercer@example.com | (555) 019-2834 | San Francisco, CA\n"
        "Senior Backend Engineer with 5+ years building FastAPI and PostgreSQL systems.\n"
        "Skills: Python, FastAPI, PostgreSQL, Docker, Redis\n"
    )
    pdf_bytes = create_synthetic_pdf(sample_text)
    assert pdf_bytes.startswith(b"%PDF")

    parser = PDFResumeParser()
    extracted = parser.extract_text(pdf_bytes)
    assert "Alex Mercer" in extracted
    assert "alex.mercer@example.com" in extracted
    assert "FastAPI" in extracted

# 2. DOCX Extraction Test
def test_docx_extraction():
    paragraphs = [
        "Jane Doe - Lead AI Systems Engineer",
        "Email: jane.doe@ai-systems.org | Location: New York, NY",
        "Experience: Designed LLM orchestration pipeline at Apex Systems.",
    ]
    table = [
        ["Skill Category", "Proficiencies"],
        ["Languages", "Python, TypeScript, SQL"],
        ["Cloud", "AWS, Docker, Kubernetes"],
    ]
    docx_bytes = create_synthetic_docx(paragraphs, table)

    parser = DocxResumeParser()
    extracted = parser.extract_text(docx_bytes)
    assert "Jane Doe" in extracted
    assert "jane.doe@ai-systems.org" in extracted
    assert "Languages" in extracted
    assert "TypeScript" in extracted

# 3. Malformed Resume Test
def test_malformed_resume():
    # Empty file
    with pytest.raises(HTTPException) as exc_empty:
        validate_resume_file("resume.pdf", b"")
    assert exc_empty.value.status_code == 400

    # Corrupt PDF (missing %PDF header)
    with pytest.raises(HTTPException) as exc_corrupt:
        validate_resume_file("corrupt.pdf", b"This is not a real PDF document.")
    assert "Missing %PDF signature" in exc_corrupt.value.detail

    # Oversized file (> 10MB)
    huge_bytes = b"%PDF" + b"0" * (11 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc_large:
        validate_resume_file("huge.pdf", huge_bytes, max_size_mb=10)
    assert exc_large.value.status_code == 413

# 4. Missing Sections Test (Zero Hallucination)
@pytest.mark.asyncio
async def test_missing_sections():
    ai = MockAIProvider()
    service = ResumeExtractionService(ai)

    # Minimal resume with NO education, NO projects, NO certifications
    minimal_text = (
        "John Developer\n"
        "john.dev@example.com\n"
        "Software Engineer with experience in Python and PostgreSQL.\n"
    )

    data = await service.extract_and_structure_resume(minimal_text)
    assert data.personal.email == "john.dev@example.com"
    # Verify no hallucinated certifications or fake companies
    assert isinstance(data.certifications, list)
    assert isinstance(data.skills.programming_languages, list)

# 5. Duplicate Skills Deduplication Test
def test_duplicate_skills_deduplication():
    raw_skills = CategorizedSkills(
        programming_languages=["Python", "python", "PYTHON", "TypeScript", "typescript", "Go"],
        frameworks=["FastAPI", "fastapi", "React", "React", "Next.js"],
        databases=["PostgreSQL", "postgresql", "PostgreSQL", "Redis"],
        cloud=["Docker", "docker", "AWS"],
        tools=["Git", "git", "Docker"], # "Docker" already in cloud
        soft_skills=["Leadership", "leadership", "System Design"]
    )

    deduped = ResumeExtractionService.deduplicate_skills(raw_skills)

    assert deduped.programming_languages == ["Python", "TypeScript", "Go"]
    assert deduped.frameworks == ["FastAPI", "React", "Next.js"]
    assert deduped.databases == ["PostgreSQL", "Redis"]
    assert deduped.cloud == ["Docker", "AWS"]
    assert "Docker" not in deduped.tools # Deduplicated across categories
    assert deduped.soft_skills == ["Leadership", "System Design"]

# 6. Invalid AI Output Fallback Test
@pytest.mark.asyncio
async def test_invalid_ai_output_fallback():
    class BrokenAIProvider(MockAIProvider):
        async def generate_structured(self, prompt, system_prompt, response_model):
            raise RuntimeError("LLM rate limit or invalid json payload returned.")

    service = ResumeExtractionService(BrokenAIProvider())

    sample_resume = (
        "Sarah Connor\n"
        "sarah.connor@sky-tech.io | (415) 555-0199\n"
        "https://linkedin.com/in/sarahconnor | https://github.com/sarahconnor\n"
        "Senior Infrastructure Engineer specialized in Python, FastAPI, Docker, and PostgreSQL in San Francisco.\n"
    )

    # Must not throw - must fallback to heuristic extraction
    structured = await service.extract_and_structure_resume(sample_resume)
    assert structured is not None
    assert structured.personal.email == "sarah.connor@sky-tech.io"
    assert structured.personal.phone == "(415) 555-0199"
    assert "https://linkedin.com/in/sarahconnor" in str(structured.personal.linkedin_url)
    assert "Python" in structured.skills.programming_languages
    assert "FastAPI" in structured.skills.frameworks
    assert "PostgreSQL" in structured.skills.databases
