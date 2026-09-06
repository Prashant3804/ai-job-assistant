import pytest
from app.modules.resume.service import ResumeService

SAMPLE_RESUME = '''
Prashant Kumar
Email: prashant.eng@example.com
Phone: +91 98765 43210
Location: Bengaluru, Karnataka, India

Summary: Passionate Full-Stack Developer experienced with Python, FastAPI, React, microservices, and PostgreSQL.

Skills: Python, JavaScript, TypeScript, SQL, FastAPI, React, PostgreSQL\
...
'''

@pytest.mark.asyncio
async def test_dynamic_resume_parsing_extracts_actual_content(async_session):
    service = ResumeService(async_session)
    parsed = await service.extract_structured_resume(SAMPLE_RESUME)
    assert parsed is not None
    skills = [s['name'].lower() for s in parsed.get('skills', [])]
    assert any(k in skills for k in ['python', 'fastapi', 'postgresql', 'react', 'typescript'])
