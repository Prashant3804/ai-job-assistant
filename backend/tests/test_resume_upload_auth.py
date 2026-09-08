import io
import uuid
import pytest
from datetime import timedelta
from app.core.security import create_access_token
from app.database.models.user import User
from app.database.models.resume import Resume
from sqlalchemy import select

def make_test_pdf() -> io.BytesIO:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Jane Doe\njane.doe@example.com | +1 555 123 4567\nSenior Engineer\nSkills: Python, FastAPI, React")
    pdf_bytes = doc.tobytes()
    doc.close()
    return io.BytesIO(pdf_bytes)

@pytest.mark.asyncio
async def test_a_valid_authenticated_resume_upload(async_client, async_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"valid_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Jane Doe",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_file = make_test_pdf()
    files = {"file": ("resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Jane Resume"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code in [200, 201]
    res_data = res.json()
    assert res_data.get("success") is True
    assert res_data.get("resume_id") is not None
    assert "Python" in res_data.get("raw_text", "")

@pytest.mark.asyncio
async def test_b_missing_authorization_header(async_client):
    pdf_file = make_test_pdf()
    files = {"file": ("resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Unauthenticated Resume"}

    res = await async_client.post("/api/v1/resume/upload", data=data, files=files)
    assert res.status_code == 401
    assert "Authentication token required" in res.json().get("detail", "")

@pytest.mark.asyncio
async def test_c_invalid_token(async_client):
    pdf_file = make_test_pdf()
    files = {"file": ("resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Invalid Token Resume"}
    headers = {"Authorization": "Bearer invalid.garbage.token"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json().get("detail", "")

@pytest.mark.asyncio
async def test_d_expired_token(async_client, async_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"expired_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Expired Candidate",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    expired_token = create_access_token(str(user.id), expires_delta=timedelta(minutes=-30))
    headers = {"Authorization": f"Bearer {expired_token}"}

    pdf_file = make_test_pdf()
    files = {"file": ("resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Expired Token Resume"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json().get("detail", "")

@pytest.mark.asyncio
async def test_e_authenticated_multipart_upload_extraction_begins(async_client, async_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"extract_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Alex Extraction",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_file = make_test_pdf()
    files = {"file": ("developer_resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Software Engineer CV"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code in [200, 201]
    res_data = res.json()
    assert "structured_data" in res_data
    assert res_data["structured_data"] is not None

@pytest.mark.asyncio
async def test_f_resume_record_belongs_to_authenticated_user(async_client, async_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"owner_{user_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="Resume Owner",
        is_active=True,
        is_verified=True,
        role="CANDIDATE"
    )
    async_session.add(user)
    await async_session.commit()

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_file = make_test_pdf()
    files = {"file": ("owner_resume.pdf", pdf_file, "application/pdf")}
    data = {"title": "Owned Resume"}

    res = await async_client.post("/api/v1/resume/upload", headers=headers, data=data, files=files)
    assert res.status_code in [200, 201]
    resume_id = uuid.UUID(res.json()["resume_id"])

    stmt = select(Resume).where(Resume.id == resume_id)
    db_res = await async_session.execute(stmt)
    db_resume = db_res.scalar_one_or_none()
    assert db_resume is not None
    assert db_resume.user_id == user.id

@pytest.mark.asyncio
async def test_g_one_user_cannot_access_another_users_resume(async_client, async_session):
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    user1 = User(
        id=user1_id,
        email=f"u1_{user1_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="User One",
        is_active=True,
        role="CANDIDATE"
    )
    user2 = User(
        id=user2_id,
        email=f"u2_{user2_id.hex[:8]}@example.com",
        hashed_password="hashed_pw",
        full_name="User Two",
        is_active=True,
        role="CANDIDATE"
    )
    async_session.add_all([user1, user2])
    await async_session.commit()

    token1 = create_access_token(str(user1.id))
    pdf_file = make_test_pdf()
    files = {"file": ("user1.pdf", pdf_file, "application/pdf")}
    res_up = await async_client.post(
        "/api/v1/resume/upload",
        headers={"Authorization": f"Bearer {token1}"},
        data={"title": "User1 Resume"},
        files=files
    )
    resume1_id = res_up.json()["resume_id"]

    token2 = create_access_token(str(user2.id))
    headers2 = {"Authorization": f"Bearer {token2}"}
    res_get = await async_client.get(f"/api/v1/resume/{resume1_id}", headers=headers2)
    assert res_get.status_code == 404
    assert res_get.json().get("detail") == "Resume not found"
