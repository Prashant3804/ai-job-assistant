from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict
from app.modules.mailbox.providers.base import BaseMailboxProvider
from app.modules.mailbox.normalizer import NormalizedEmail
from app.modules.mailbox.security import sanitize_html

class MockMailboxProvider(BaseMailboxProvider):
    def __init__(self, account_email: str = "candidate@example.com"):
        self.account_email = account_email
        self._messages = self._generate_mock_dataset()

    def _generate_mock_dataset(self) -> Dict[str, NormalizedEmail]:
        now = datetime.now(timezone.utc)
        
        messages = [
            NormalizedEmail(
                external_message_id="mock_msg_001_stripe_ack",
                external_thread_id="mock_thread_stripe_001",
                sender_email="no-reply@greenhouse.io",
                sender_name="Stripe Recruiting",
                recipient_email=self.account_email,
                subject="Thank you for applying to Stripe - Senior Backend Engineer",
                snippet="Thank you for your application to the Senior Backend Engineer role at Stripe. Our team is reviewing your profile...",
                body_text="Hi Candidate,\n\nThank you for applying for the Senior Backend Engineer position at Stripe. We have received your application and our team is currently reviewing your background and experience.\n\nBest regards,\nStripe Recruiting Team",
                body_html="<p>Hi Candidate,</p><p>Thank you for applying for the <strong>Senior Backend Engineer</strong> position at <strong>Stripe</strong>. We have received your application and our team is currently reviewing your background and experience.</p><p>Best regards,<br>Stripe Recruiting Team</p>",
                received_at=now - timedelta(days=5),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "Stripe Recruiting <no-reply@greenhouse.io>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_002_stripe_interview",
                external_thread_id="mock_thread_stripe_001",
                sender_email="recruiting@stripe.com",
                sender_name="Sarah Jenkins",
                recipient_email=self.account_email,
                subject="Invitation to Interview: Stripe - Senior Backend Engineer Technical Screen",
                snippet="We were impressed by your background and would love to schedule a 45-minute technical screen with our engineering team...",
                body_text="Hi Candidate,\n\nWe were very impressed by your profile and would love to invite you for a 45-minute technical screen for the Senior Backend Engineer role at Stripe. Please use the Calendly link below to select a time that suits you: https://calendly.com/stripe-sarah/interview\n\nLooking forward to speaking with you!\n\nSarah Jenkins\nSenior Technical Recruiter | Stripe",
                body_html="<p>Hi Candidate,</p><p>We were very impressed by your profile and would love to invite you for a <strong>45-minute technical screen</strong> for the <strong>Senior Backend Engineer</strong> role at <strong>Stripe</strong>.</p><p>Please use this link to schedule: <a href='https://calendly.com/stripe-sarah/interview'>Schedule Interview</a></p><p>Sarah Jenkins<br>Senior Technical Recruiter | Stripe</p>",
                received_at=now - timedelta(days=3),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "Sarah Jenkins <recruiting@stripe.com>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_003_netflix_oa",
                external_thread_id="mock_thread_netflix_001",
                sender_email="assessments@workday.net",
                sender_name="Netflix Talent Operations",
                recipient_email=self.account_email,
                subject="Action Required: Online Coding Assessment for Senior Python Engineer - Netflix",
                snippet="Please complete your online assessment for Netflix within 5 days on HackerRank...",
                body_text="Dear Candidate,\n\nAs the next step in the interview process for the Senior Python Engineer position at Netflix, please complete this 90-minute coding assessment on HackerRank.\n\nLink: https://hackerrank.com/netflix-eval-98234\nDeadline: 5 business days.\n\nBest,\nNetflix Talent Operations",
                body_html="<p>Dear Candidate,</p><p>Please complete this 90-minute online coding assessment for <strong>Netflix</strong>: <a href='https://hackerrank.com/netflix-eval-98234'>Start Assessment</a></p>",
                received_at=now - timedelta(days=2),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "Netflix Talent Operations <assessments@workday.net>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_004_datadog_reject",
                external_thread_id="mock_thread_datadog_001",
                sender_email="careers@datadog.com",
                sender_name="DataDog Talent Acquisition",
                recipient_email=self.account_email,
                subject="Update on your application for Full Stack Engineer at DataDog",
                snippet="Thank you for taking the time to apply. After careful review, we will not be moving forward at this time...",
                body_text="Hi Candidate,\n\nThank you for your interest in DataDog and for taking the time to apply for the Full Stack Engineer role. After careful review, we have decided not to move forward with your candidacy for this specific position.\n\nWe wish you the best in your job search.\n\nDataDog Recruiting Team",
                body_html="<p>Hi Candidate,</p><p>Thank you for your interest in <strong>DataDog</strong>. Unfortunately we will not be moving forward with your application for Full Stack Engineer at this time.</p>",
                received_at=now - timedelta(days=1),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "DataDog Talent Acquisition <careers@datadog.com>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_005_stripe_offer",
                external_thread_id="mock_thread_stripe_001",
                sender_email="recruiting@stripe.com",
                sender_name="Sarah Jenkins",
                recipient_email=self.account_email,
                subject="Offer of Employment - Senior Backend Engineer at Stripe!",
                snippet="Congratulations! We are thrilled to extend a formal offer of employment for the Senior Backend Engineer role at Stripe...",
                body_text="Hi Candidate,\n\nCongratulations! We are delighted to extend a formal offer of employment for the Senior Backend Engineer position at Stripe. Please find attached your official offer letter package and compensation details.\n\nWelcome to the team!\n\nSarah Jenkins\nSenior Technical Recruiter | Stripe",
                body_html="<p>Hi Candidate,</p><p><strong>Congratulations!</strong> We are thrilled to extend a formal offer of employment for the <strong>Senior Backend Engineer</strong> position at <strong>Stripe</strong>.</p><p>Please review the attached formal offer letter.</p>",
                received_at=now - timedelta(hours=6),
                has_attachments=True,
                attachments=[{"filename": "Stripe_Offer_Letter_Package.pdf", "mime_type": "application/pdf", "size": 182400}],
                raw_headers={"from": "Sarah Jenkins <recruiting@stripe.com>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_006_google_inquiry",
                external_thread_id="mock_thread_google_001",
                sender_email="alex.m@google.com",
                sender_name="Alex Miller",
                recipient_email=self.account_email,
                subject="Exciting opportunity at Google Cloud - Staff Software Engineer",
                snippet="I came across your profile and was really impressed by your background in distributed systems...",
                body_text="Hi Candidate,\n\nI am a tech recruiter with Google Cloud. I came across your GitHub and background in Python and distributed systems. We are expanding our core infrastructure team and would love to connect for 15 minutes.\n\nAre you available for a quick chat this week?\n\nAlex Miller\nStaff Talent Partner | Google",
                body_html="<p>Hi Candidate,</p><p>I came across your profile and would love to connect regarding a <strong>Staff Software Engineer</strong> opening at <strong>Google</strong>.</p><p>Alex Miller<br>Google Cloud Talent Team</p>",
                received_at=now - timedelta(hours=2),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "Alex Miller <alex.m@google.com>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_007_newsletter",
                external_thread_id="mock_thread_github_001",
                sender_email="notifications@github.com",
                sender_name="GitHub",
                recipient_email=self.account_email,
                subject="GitHub Daily Trending Repositories",
                snippet="Here are the top trending open-source repositories today...",
                body_text="Explore top trending Python and TypeScript repositories today on GitHub.",
                body_html="<p>Explore top trending open-source projects on GitHub.</p>",
                received_at=now - timedelta(days=4),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "GitHub <notifications@github.com>"},
            ),
            NormalizedEmail(
                external_message_id="mock_msg_008_xss_sanitization",
                external_thread_id="mock_thread_xss_001",
                sender_email="alerts@securitytest.com",
                sender_name="Security Tester",
                recipient_email=self.account_email,
                subject="Security Verification Notice",
                snippet="Test XSS filtering with malicious payload...",
                body_text="Testing XSS protection.",
                body_html=sanitize_html("<div>Safe content<script>alert('xss')</script><img src=x onerror=alert(1)></div>"),
                received_at=now - timedelta(hours=1),
                has_attachments=False,
                attachments=[],
                raw_headers={"from": "Security Tester <alerts@securitytest.com>"},
            ),
        ]
        return {m.external_message_id: m for m in messages}

    async def fetch_messages(
        self,
        cursor: Optional[str] = None,
        max_results: int = 50,
        since: Optional[datetime] = None
    ) -> Tuple[List[NormalizedEmail], Optional[str]]:
        all_msgs = list(self._messages.values())
        if since:
            since_utc = since if since.tzinfo is not None else since.replace(tzinfo=timezone.utc)
            all_msgs = [
                m for m in all_msgs
                if (m.received_at if m.received_at.tzinfo is not None else m.received_at.replace(tzinfo=timezone.utc)) >= since_utc
            ]
        
        all_msgs.sort(key=lambda x: x.received_at, reverse=True)
        return all_msgs[:max_results], None

    async def fetch_message_by_id(self, external_message_id: str) -> Optional[NormalizedEmail]:
        return self._messages.get(external_message_id)

    async def fetch_thread_messages(self, external_thread_id: str) -> List[NormalizedEmail]:
        matched = [m for m in self._messages.values() if m.external_thread_id == external_thread_id]
        matched.sort(key=lambda x: x.received_at, reverse=False)
        return matched
