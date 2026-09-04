import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.shared.constants import DraftIntent, DraftTone
from app.ai.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


def sanitize_prompt_text(text: Optional[str]) -> str:
    """Sanitize user/email input to mitigate prompt injection."""
    if not text:
        return ""
    # Strip dangerous instruction keywords and normalize
    cleaned = re.sub(r"(ignore\s+all\s+previous\s+instructions|system\s+prompt|role:\s*system)", "[FILTERED]", text, flags=re.IGNORECASE)
    return cleaned.strip()


class ResponseDraftingEngine:
    """
    Contextual AI Response Drafting Engine for Recruiter Communication.
    Supports 8 intents and 5 tones with strict Human-in-the-Loop constraints.
    """

    @classmethod
    async def generate_draft(
        cls,
        candidate_name: str,
        recruiter_name: Optional[str] = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        intent: DraftIntent = DraftIntent.GENERAL,
        tone: DraftTone = DraftTone.PROFESSIONAL,
        candidate_availability: Optional[List[str]] = None,
        incoming_email_snippet: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        salary_expectation: Optional[str] = None,
        offer_details: Optional[str] = None,
        candidate_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        rec_name = recruiter_name or "Hiring Team"
        comp = company_name or "your team"
        role = job_title or "the open position"
        availability = candidate_availability if candidate_availability is not None else []
        skills_str = ", ".join(candidate_skills[:5]) if candidate_skills else "relevant industry skills"

        # Attempt AI generation via OmniRoute
        try:
            ai_service = get_ai_service()
            system_prompt = (
                "You are an expert career and executive communication coach. "
                "Generate a highly professional, contextual email response for a job candidate to send to a recruiter. "
                "Respond ONLY with a valid JSON object in the exact schema:\n"
                "{\n"
                '  "subject": "<Email Subject Line>",\n'
                '  "body_text": "<Full email body text>",\n'
                '  "key_points_addressed": ["<Point 1>", "<Point 2>"]\n'
                "}\n"
                "Do not include markdown codeblocks or extra text outside JSON."
            )

            prompt = (
                f"Candidate Name: {candidate_name}\n"
                f"Recruiter Name: {sanitize_prompt_text(rec_name)}\n"
                f"Company: {sanitize_prompt_text(comp)}\n"
                f"Job Title: {sanitize_prompt_text(role)}\n"
                f"Communication Intent: {intent.value}\n"
                f"Desired Tone: {tone.value}\n"
                f"Availability Slots: {json.dumps(availability) if availability else 'Candidate is flexible or requesting recruiter times'}\n"
                f"Candidate Skills: {skills_str}\n"
                f"Salary Expectation: {sanitize_prompt_text(salary_expectation)}\n"
                f"Offer Details: {sanitize_prompt_text(offer_details)}\n"
                f"Incoming Email Context: {sanitize_prompt_text(incoming_email_snippet)}\n"
                f"Special Instructions: {sanitize_prompt_text(custom_instructions)}\n"
            )

            raw_response = await ai_service.complete_prompt(system_prompt=system_prompt, prompt=prompt)
            # Parse response
            cleaned_json = raw_response.strip()
            if cleaned_json.startswith("```json"):
                cleaned_json = cleaned_json[7:]
            if cleaned_json.startswith("```"):
                cleaned_json = cleaned_json[3:]
            if cleaned_json.endswith("```"):
                cleaned_json = cleaned_json[:-3]
            cleaned_json = cleaned_json.strip()

            parsed = json.loads(cleaned_json)
            if "subject" in parsed and "body_text" in parsed:
                return {
                    "subject": parsed["subject"],
                    "body_text": parsed["body_text"],
                    "key_points_addressed": parsed.get("key_points_addressed", [intent.value]),
                    "candidate_availability_used": availability if intent == DraftIntent.SCHEDULE_INTERVIEW else [],
                }
        except Exception as exc:
            logger.warning(f"OmniRoute AI drafting failed ({exc}), falling back to deterministic template.")

        # Deterministic Template Fallback
        return cls._generate_template_draft(
            candidate_name=candidate_name,
            recruiter_name=rec_name,
            company_name=comp,
            job_title=role,
            intent=intent,
            tone=tone,
            availability=availability,
            salary_expectation=salary_expectation,
            offer_details=offer_details,
        )

    @classmethod
    def _generate_template_draft(
        cls,
        candidate_name: str,
        recruiter_name: str,
        company_name: str,
        job_title: str,
        intent: DraftIntent,
        tone: DraftTone,
        availability: List[str],
        salary_expectation: Optional[str] = None,
        offer_details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """High quality deterministic templates for all 8 intents & 5 tones."""
        salutation = f"Hi {recruiter_name}," if recruiter_name and recruiter_name != "Hiring Team" else "Hello Hiring Team,"
        if availability:
            slots_text = "\n".join([f"- {slot}" for slot in availability])
        else:
            slots_text = "- Flexible this week with 24 hours advance notice. Please suggest a few time slots that work best for your schedule."

        if intent == DraftIntent.SCHEDULE_INTERVIEW:
            subject = f"Re: Interview Availability — {candidate_name} for {job_title} at {company_name}"
            if tone == DraftTone.CONCISE:
                body = (
                    f"{salutation}\n\n"
                    f"Thank you for the update. Here is my upcoming availability for our interview:\n\n"
                    f"{slots_text}\n\n"
                    f"Please let me know which time works best. Looking forward to speaking.\n\n"
                    f"Best,\n{candidate_name}"
                )
            elif tone == DraftTone.ENTHUSIASTIC:
                body = (
                    f"{salutation}\n\n"
                    f"Thank you so much for reaching out! I'm thrilled about the opportunity to discuss the {job_title} role with the team at {company_name}.\n\n"
                    f"I would be delighted to speak during any of the following times:\n\n"
                    f"{slots_text}\n\n"
                    f"If none of these suit your schedule, please feel free to suggest an alternative. Looking forward to our conversation!\n\n"
                    f"Warm regards,\n{candidate_name}"
                )
            elif tone == DraftTone.CONFIDENT:
                body = (
                    f"{salutation}\n\n"
                    f"Thank you for reaching out regarding the {job_title} position. I am eager to share how my experience and skill set can directly drive impact for {company_name}.\n\n"
                    f"I have reserved the following times for our conversation:\n\n"
                    f"{slots_text}\n\n"
                    f"Please send over a calendar invite for the slot that fits your schedule best.\n\n"
                    f"Sincerely,\n{candidate_name}"
                )
            else:
                body = (
                    f"{salutation}\n\n"
                    f"Thank you for reaching out regarding the {job_title} role at {company_name}. I am very interested in this opportunity and look forward to connecting.\n\n"
                    f"I am available for our interview at the following times:\n\n"
                    f"{slots_text}\n\n"
                    f"Please let me know if one of these times works for you, or if you prefer an alternative.\n\n"
                    f"Best regards,\n{candidate_name}"
                )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Confirmed availability", "Provided multiple time slots", "Expressed interest in role"],
                "candidate_availability_used": availability,
            }

        elif intent == DraftIntent.THANK_YOU:
            subject = f"Thank You — {job_title} at {company_name} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"Thank you for taking the time to speak with me today about the {job_title} role at {company_name}. "
                f"I really enjoyed our discussion regarding the team's current priorities and vision.\n\n"
                f"Our conversation reinforced my strong enthusiasm for joining {company_name}. I am confident that my background will allow me to make meaningful contributions to your goals.\n\n"
                f"Please let me know if you need any additional information from my side. Looking forward to hearing about the next steps.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Expressed gratitude for interview", "Referenced discussion", "Reiterated strong fit and next steps"],
                "candidate_availability_used": [],
            }

        elif intent == DraftIntent.NEGOTIATE_OFFER:
            subject = f"Offer Discussion — {job_title} at {company_name} — {candidate_name}"
            target_comp = salary_expectation or "the total compensation package"
            body = (
                f"{salutation}\n\n"
                f"Thank you very much for extending the offer for the {job_title} position at {company_name}. "
                f"I am genuinely excited about the opportunity to collaborate with the team.\n\n"
                f"Having reviewed the offer details, I would like to discuss {target_comp}. "
                f"Based on my relevant experience and market benchmarks for this role, I would be thrilled to formally accept if we can align on compensation.\n\n"
                f"Could we schedule a brief call this week to discuss? Thank you again for your consideration.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Acknowledged offer with gratitude", "Proposed compensation discussion", "Maintained positive and constructive tone"],
                "candidate_availability_used": [],
            }

        elif intent == DraftIntent.FOLLOW_UP:
            subject = f"Following Up — {job_title} at {company_name} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"I hope you are having a productive week. I am following up on my application for the {job_title} position at {company_name}.\n\n"
                f"I remain very interested in the opportunity and would love to check if there are any updates regarding the hiring timeline or next steps.\n\n"
                f"Thank you for your time and continued consideration.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Polite follow-up on status", "Reaffirmed ongoing interest", "Inquired about timeline"],
                "candidate_availability_used": [],
            }

        elif intent == DraftIntent.ACCEPT_OFFER:
            subject = f"Offer Acceptance — {job_title} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"I am delighted to formally accept your offer for the {job_title} position at {company_name}!\n\n"
                f"I am eager to join the team and look forward to contributing to our shared success. "
                f"Please let me know the upcoming onboarding steps, documentation required, and confirmation of my start date.\n\n"
                f"Thank you again for this wonderful opportunity.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Formally accepted job offer", "Requested onboarding instructions", "Confirmed start date inquiry"],
                "candidate_availability_used": [],
            }

        elif intent == DraftIntent.DECLINE_OFFER:
            subject = f"Regarding Offer — {job_title} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"Thank you very much for offering me the {job_title} position at {company_name}. I truly appreciate the time and insight you and the team shared throughout the interview process.\n\n"
                f"After careful consideration, I have decided to pursue another opportunity that closely aligns with my immediate career path. This was a difficult decision given my high regard for {company_name}.\n\n"
                f"I hope we can stay in touch, and I wish you and the team continued success.\n\n"
                f"Warm regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Politely declined offer", "Expressed appreciation for the team", "Kept relationship warm for future"],
                "candidate_availability_used": [],
            }

        elif intent == DraftIntent.COLD_REPLY:
            subject = f"Re: Opportunity at {company_name} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"Thank you for reaching out regarding the {job_title} opportunity at {company_name}. "
                f"I have reviewed the role and would be very interested in learning more about the team's upcoming initiatives.\n\n"
                f"I have attached my background and am happy to connect for a brief introductory call. Here is my current availability:\n\n"
                f"{slots_text}\n\n"
                f"Looking forward to hearing from you.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["Acknowledged recruiter outreach", "Expressed interest in role", "Provided availability for intro call"],
                "candidate_availability_used": availability,
            }

        else: # GENERAL
            subject = f"Re: {job_title} — {candidate_name}"
            body = (
                f"{salutation}\n\n"
                f"Thank you for your message regarding {job_title} at {company_name}.\n\n"
                f"I appreciate you keeping me informed. Please let me know if you need any additional information or documentation from my end.\n\n"
                f"Best regards,\n{candidate_name}"
            )
            return {
                "subject": subject,
                "body_text": body,
                "key_points_addressed": ["General professional acknowledgment"],
                "candidate_availability_used": [],
            }
