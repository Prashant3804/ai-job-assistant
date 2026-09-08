import uuid
import pytest
from datetime import timedelta
from app.core.security import create_access_token
from app.database.models.user import User
import fitz
import io

def make_test_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Harsh Vardhan\nharsh.candidate@example.com\nSkills: Python, React, Next.js")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.mark.asyncio
async def test_frontend_upload_flow_with_authenticated_token(async_client, async_session):
    """
    Verifies that when a valid token is present in the request:
    1. Authorization: Bearer <token> is properly processed.
    2. Content-Type multipart boundary is recognized.
    3. Resume is extracted and linked to the authenticated user.
    """
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"client_test_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Frontend Candidate",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    pdf_bytes = make_test_pdf_bytes()
    files = {"file": ("frontend_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Frontend Upload Test"}

    # Simulate frontend client request
    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code in [200, 201]
    res_data = res.json()
    assert res_data.get("success") is True
    assert res_data.get("resume_id") is not None
    assert "Harsh Vardhan" in res_data.get("raw_text", "")

@pytest.mark.asyncio
async def test_missing_token_rejected_preventing_unauthenticated_state(async_client):
    """
    Verifies that when Authorization header is missing, the backend returns 401
    and detail 'Authentication token required'.
    """
    pdf_bytes = make_test_pdf_bytes()
    files = {"file": ("unauth_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Unauth Test"}

    res = await async_client.post("/api/v1/resume/upload", data=data, files=files)
    assert res.status_code == 401
    assert "Authentication token required" in res.json().get("detail", "")

@pytest.mark.asyncio
async def test_expired_token_rejected_forcing_session_refresh(async_client, async_session):
    """
    Verifies that an expired JWT is rejected with 401 'Could not validate credentials'.
    """
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"expired_client_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Expired User",
        is_active=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    expired_token = create_access_token(str(user.id), expires_delta=timedelta(minutes=-15))
    headers = {"Authorization": f"Bearer {expired_token}"}
    pdf_bytes = make_test_pdf_bytes()
    files = {"file": ("expired_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Expired Test"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json().get("detail", "")
