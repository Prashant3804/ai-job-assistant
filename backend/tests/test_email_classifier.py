import pytest
from app.modules.email.service import EmailIntelligenceService
from app.shared.schemas import EmailClassifyRequest
from app.modules.ai.service import MockAIProvider

@pytest.mark.asyncio
async def test_email_interview_invitation_classification():
    ai = MockAIProvider()
    service = EmailIntelligenceService(None, ai_service=ai)

    req = EmailClassifyRequest(
        sender_email="recruiter@acme.com",
        sender_name="Jane Recruiter",
        subject="Interview Invitation: Next Round Technical Call",
        body_text="Hi Alex, We'd like to schedule your next technical interview this Thursday at 2pm."
    )
    result = await service.classify_message_content(req)
    assert result.is_recruiter is True
    assert result.classification == "INTERVIEW_INVITATION"
    assert result.confidence_score >= 0.90
    assert result.suggested_status_update == "INTERVIEW_SCHEDULED"

@pytest.mark.asyncio
async def test_email_offer_classification():
    ai = MockAIProvider()
    service = EmailIntelligenceService(None, ai_service=ai)

    req = EmailClassifyRequest(
        sender_email="talent@innovate.com",
        sender_name="Talent Lead",
        subject="Official Offer Letter: Senior Engineer",
        body_text="Dear Candidate, We are pleased to offer you the position of Senior Engineer."
    )
    result = await service.classify_message_content(req)
    assert result.is_recruiter is True
    assert result.classification == "OFFER"
    assert result.suggested_status_update == "OFFER_RECEIVED"

@pytest.mark.asyncio
async def test_email_rejection_classification():
    ai = MockAIProvider()
    service = EmailIntelligenceService(None, ai_service=ai)

    req = EmailClassifyRequest(
        sender_email="no-reply@careers.com",
        sender_name="Talent Acquisition",
        subject="Update on your application",
        body_text="Unfortunately we have decided to move forward with other candidates at this time."
    )
    result = await service.classify_message_content(req)
    assert result.is_recruiter is True
    assert result.classification == "REJECTION"
    assert result.suggested_status_update == "REJECTED"
