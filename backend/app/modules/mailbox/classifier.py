import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.shared.constants import EmailCategory, RecruiterStatus, ApplicationStatus
from app.modules.mailbox.normalizer import NormalizedEmail
from app.modules.ai.service import BaseLLMService, get_ai_service

KNOWN_ATS_DOMAINS = {
    "greenhouse.io",
    "gh.greenhouse.io",
    "lever.co",
    "hire.lever.co",
    "workday.com",
    "workday.net",
    "myworkdayjobs.com",
    "icims.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "bamboohr.com",
    "talentlyft.com",
    "jobvite.com",
    "recruitee.com",
    "jazzhr.com",
    "applytojob.com",
    "recruiting.com",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "aol.com",
    "protonmail.com",
    "mail.com",
}

class EmailClassificationResult(BaseModel):
    is_recruiter: bool = False
    recruiter_status: str = RecruiterStatus.NOT_RECRUITER.value
    is_job_related: bool = False
    classification: str = EmailCategory.NOT_JOB_RELATED.value
    confidence_score: float = 0.0
    classification_reason: Optional[str] = None
    detected_company: Optional[str] = None
    detected_job_title: Optional[str] = None
    suggested_application_status: Optional[str] = None

class AIClassificationSchema(BaseModel):
    is_job_related: bool = Field(description="True if email is related to jobs, interviews, offers, rejections, or recruiter messages")
    is_recruiter: bool = Field(description="True if sender is an internal/agency recruiter or ATS system")
    recruiter_status: str = Field(description="RECRUITER_DIRECT, ATS_SYSTEM, or NOT_RECRUITER")
    classification: str = Field(description="APPLICATION_CONFIRMATION, INTERVIEW_INVITATION, ASSESSMENT_REQUEST, REJECTION, OFFER, GENERAL_INQUIRY, RECRUITER_OUTREACH, or NOT_JOB_RELATED")
    confidence_score: float = Field(ge=0.0, le=1.0)
    classification_reason: str
    detected_company: Optional[str] = None
    detected_job_title: Optional[str] = None
    suggested_application_status: Optional[str] = None

class EmailClassifier:
    def __init__(self, ai_service: Optional[BaseLLMService] = None):
        self.ai = ai_service or get_ai_service()

    def classify_deterministic(self, email: NormalizedEmail) -> Optional[EmailClassificationResult]:
        """Runs fast, deterministic heuristic checks on email subject, sender, and body."""
        subject = email.subject.lower()
        sender_email = email.sender_email.lower()
        sender_name = (email.sender_name or "").lower()
        body = (email.body_text or "").lower()
        combined = f"{subject} {body}"

        sender_domain = sender_email.split("@")[-1] if "@" in sender_email else ""
        is_ats = any(sender_domain.endswith(ats) for ats in KNOWN_ATS_DOMAINS)

        # 1. Offer
        if any(k in subject for k in ["offer of employment", "offer letter", "formal offer", "job offer"]) or (
            "congratulations" in combined and "offer" in combined and ("extend" in combined or "package" in combined)
        ):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.ATS_SYSTEM.value if is_ats else RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.OFFER.value,
                confidence_score=0.98,
                classification_reason="High-confidence offer keywords identified in subject/body",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=ApplicationStatus.OFFER.value,
            )

        # 2. Assessment Request
        if any(k in combined for k in ["hackerrank", "codility", "codesignal", "byteboard", "online assessment", "coding assessment", "take-home test", "technical test", "oa request"]):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.ATS_SYSTEM.value if is_ats else RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.ASSESSMENT_REQUEST.value,
                confidence_score=0.95,
                classification_reason="Technical coding assessment keywords identified",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=ApplicationStatus.ONLINE_ASSESSMENT.value,
            )

        # 3. Interview Invitation
        if (
            any(k in subject for k in ["invitation to interview", "interview:", "schedule an interview", "technical screen", "phone screen", "hiring manager chat"])
            or any(k in combined for k in ["schedule a 45-minute", "schedule a 30-minute", "calendly.com", "calendar invitation", "schedule your interview", "invite you for an interview"])
        ):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.ATS_SYSTEM.value if is_ats else RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.INTERVIEW_INVITATION.value,
                confidence_score=0.95,
                classification_reason="Interview scheduling keywords or scheduling links detected",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=ApplicationStatus.INTERVIEWING.value,
            )

        # 4. Rejection
        if any(k in combined for k in [
            "not to move forward",
            "not moving forward",
            "pursuing other candidates",
            "decided not to proceed",
            "unfortunately, we have chosen",
            "will not be moving forward",
            "decided to pursue other applicants",
        ]):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.ATS_SYSTEM.value if is_ats else RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.REJECTION.value,
                confidence_score=0.95,
                classification_reason="Application rejection language detected",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=ApplicationStatus.REJECTED.value,
            )

        # 5. Application Confirmation
        if (
            any(k in subject for k in ["thank you for applying", "application received", "received your application", "we have received your application"])
            or (is_ats and "thank you for your interest" in combined)
        ):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.ATS_SYSTEM.value if is_ats else RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.APPLICATION_CONFIRMATION.value,
                confidence_score=0.92,
                classification_reason="ATS receipt or application acknowledgement detected",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=ApplicationStatus.APPLIED.value,
            )

        # 6. Recruiter Direct Outreach
        recruiter_titles = ["recruiter", "talent acquisition", "sourcer", "talent partner", "headhunter", "talent lead"]
        if (
            any(t in sender_name for t in recruiter_titles)
            or any(t in body for t in recruiter_titles)
            or any(k in combined for k in ["came across your profile", "exciting opportunity", "found your profile", "opening on our team", "love to connect for 15 minutes"])
        ):
            company = self._extract_company(email, sender_domain, is_ats)
            title = self._extract_job_title(email)
            return EmailClassificationResult(
                is_recruiter=True,
                recruiter_status=RecruiterStatus.RECRUITER_DIRECT.value,
                is_job_related=True,
                classification=EmailCategory.RECRUITER_OUTREACH.value,
                confidence_score=0.88,
                classification_reason="Recruiter direct outreach signals detected in signature/text",
                detected_company=company,
                detected_job_title=title,
                suggested_application_status=None,
            )

        # 7. Definite Non-Job Email
        non_job_domains = ["github.com", "newsletter", "marketing", "amazon.com", "uber.com", "doordash.com", "stripe.com/billing"]
        if any(d in sender_domain for d in ["github.com", "amazon.com", "uber.com", "netflix.com/billing"]) and not is_ats:
            if not any(w in combined for w in ["interview", "candidate", "application", "hiring", "resume"]):
                return EmailClassificationResult(
                    is_recruiter=False,
                    recruiter_status=RecruiterStatus.NOT_RECRUITER.value,
                    is_job_related=False,
                    classification=EmailCategory.NOT_JOB_RELATED.value,
                    confidence_score=0.95,
                    classification_reason="Standard transactional or newsletter email",
                )

        return None

    def _extract_company(self, email: NormalizedEmail, sender_domain: str, is_ats: bool) -> Optional[str]:
        # 1. From subject patterns
        sub = email.subject
        patterns = [
            r"(?:applying\s+to|at|with|for)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)",
            r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s*-\s*(?:Senior|Software|Backend|Frontend|Full|Lead|Staff)",
        ]
        for p in patterns:
            match = re.search(p, sub)
            if match:
                cand = match.group(1).strip()
                if cand.lower() not in ["the", "an", "a", "your", "our", "action", "update", "invitation", "thank"]:
                    return cand

        # 2. From sender name
        if email.sender_name:
            if "Stripe" in email.sender_name:
                return "Stripe"
            if "Netflix" in email.sender_name:
                return "Netflix"
            if "Google" in email.sender_name:
                return "Google"
            if "DataDog" in email.sender_name or "Datadog" in email.sender_name:
                return "DataDog"

        # 3. From domain if company domain
        if sender_domain and sender_domain not in KNOWN_ATS_DOMAINS and sender_domain not in FREE_EMAIL_DOMAINS:
            company_slug = sender_domain.split(".")[0]
            if len(company_slug) > 2:
                return company_slug.capitalize()

        return None

    def _extract_job_title(self, email: NormalizedEmail) -> Optional[str]:
        combined = f"{email.subject} {email.body_text or ''}"
        titles = [
            "Senior Backend Engineer",
            "Senior Python Engineer",
            "Staff Software Engineer",
            "Full Stack Engineer",
            "Software Engineer",
            "Frontend Engineer",
            "DevOps Engineer",
            "Backend Developer",
        ]
        for t in titles:
            if t.lower() in combined.lower():
                return t
        return None

    async def classify(self, email: NormalizedEmail) -> EmailClassificationResult:
        """Runs deterministic heuristics first, falling back to OmniRoute AI Service if ambiguous."""
        deterministic = self.classify_deterministic(email)
        if deterministic and deterministic.confidence_score >= 0.85:
            return deterministic

        # AI Fallback for nuanced/unstructured emails
        prompt = (
            f"Sender: {email.sender_name} <{email.sender_email}>\n"
            f"Subject: {email.subject}\n"
            f"Snippet: {email.snippet}\n\n"
            f"Body:\n{email.body_text[:2000]}"
        )
        system_prompt = (
            "You are an expert AI Job Search & Recruiter Email Classifier. Analyze the given email message. "
            "Determine if it is job-related, whether the sender is a recruiter or ATS, classify the category strictly into: "
            "[APPLICATION_CONFIRMATION, INTERVIEW_INVITATION, ASSESSMENT_REQUEST, REJECTION, OFFER, GENERAL_INQUIRY, RECRUITER_OUTREACH, NOT_JOB_RELATED], "
            "provide a confidence score (0.0 - 1.0), reasoning, detected company name, detected job title, and suggested application status."
        )

        try:
            ai_res = await self.ai.generate_structured(prompt, system_prompt, AIClassificationSchema)
            return EmailClassificationResult(
                is_recruiter=ai_res.is_recruiter,
                recruiter_status=ai_res.recruiter_status,
                is_job_related=ai_res.is_job_related,
                classification=ai_res.classification,
                confidence_score=ai_res.confidence_score,
                classification_reason=ai_res.classification_reason,
                detected_company=ai_res.detected_company,
                detected_job_title=ai_res.detected_job_title,
                suggested_application_status=ai_res.suggested_application_status,
            )
        except Exception:
            # Safe default fallback
            return deterministic or EmailClassificationResult(
                is_recruiter=False,
                recruiter_status=RecruiterStatus.NOT_RECRUITER.value,
                is_job_related=False,
                classification=EmailCategory.NOT_JOB_RELATED.value,
                confidence_score=0.5,
                classification_reason="Fallback default classification",
            )
