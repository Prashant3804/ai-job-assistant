import re
from typing import Dict, Any, List, Optional, Tuple
from app.database.models.user import User, UserProfile, Education, Experience, CandidateSkill, Project, JobPreference

class ApplicationDataMapper:
    """Maps verified candidate profile data into standard ATS/Application form answers."""

    @staticmethod
    def map_application_data(
        user: User,
        profile: Optional[UserProfile] = None,
        preferences: Optional[JobPreference] = None,
        educations: Optional[List[Education]] = None,
        experiences: Optional[List[Experience]] = None,
        skills: Optional[List[CandidateSkill]] = None,
        projects: Optional[List[Project]] = None,
        application_questions: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
        """
        Returns:
            - standard_candidate_payload: Dict of standard verified profile fields.
            - mapped_answers: List of question-answer dictionaries.
            - missing_fields: List of required question keys that could not be mapped from verified profile.
        """
        # 1. Base Verified Payload
        phone_val = getattr(user, 'phone_number', None) or (profile.phone if profile and hasattr(profile, 'phone') else None)
        loc_val = profile.location if profile else None
        headline_val = profile.headline if profile else None
        yoe_val = profile.years_of_experience if profile else 0.0

        latest_edu = educations[0] if educations and len(educations) > 0 else None
        latest_exp = experiences[0] if experiences and len(experiences) > 0 else None
        skill_names = [s.name for s in (skills or [])]

        candidate_payload: Dict[str, Any] = {
            "name": user.full_name or "",
            "email": user.email,
            "phone": phone_val or "",
            "location": loc_val or "",
            "headline": headline_val or "",
            "years_of_experience": yoe_val,
            "linkedin_url": profile.linkedin_url if profile and profile.linkedin_url else "",
            "github_url": profile.github_url if profile and profile.github_url else "",
            "portfolio_url": profile.portfolio_url if profile and profile.portfolio_url else "",
            "highest_degree": latest_edu.degree if latest_edu else "",
            "institution": latest_edu.institution if latest_edu else "",
            "field_of_study": latest_edu.field_of_study if latest_edu else "",
            "graduation_year": latest_edu.end_date if latest_edu else "",
            "current_company": latest_exp.company_name if latest_exp else "",
            "current_title": latest_exp.title if latest_exp else "",
            "skills": skill_names,
            "expected_salary": getattr(preferences, 'min_base_salary', getattr(preferences, 'min_salary', None)) if preferences else None,
            "preferred_currency": getattr(preferences, 'currency', getattr(preferences, 'salary_currency', "USD")) if preferences else "USD",
            "work_authorization": getattr(preferences, 'work_authorization', True) if preferences else True,
            "requires_sponsorship": getattr(preferences, 'sponsorship_required', getattr(preferences, 'requires_sponsorship', False)) if preferences else False,
        }

        mapped_answers: List[Dict[str, Any]] = []
        missing_fields: List[str] = []

        if not application_questions:
            return candidate_payload, mapped_answers, missing_fields

        for q in application_questions:
            q_key = q.get("key", "").lower().strip()
            q_text = q.get("question", "")
            is_required = q.get("required", False)
            is_sensitive = q.get("is_sensitive", False)

            ans_text: Optional[str] = None
            source_tag = "PROFILE_VERIFIED"

            # Strict Question Mapping Patterns
            if re.search(r"\b(full\s*name|candidate\s*name|your\s*name)\b", q_text, re.I):
                ans_text = candidate_payload["name"]
            elif re.search(r"\b(email|email\s*address)\b", q_text, re.I):
                ans_text = candidate_payload["email"]
            elif re.search(r"\b(phone|mobile|contact\s*number)\b", q_text, re.I):
                ans_text = candidate_payload["phone"]
            elif re.search(r"\b(city|location|current\s*location|address)\b", q_text, re.I):
                ans_text = candidate_payload["location"]
            elif re.search(r"\b(linkedin|linkedin\s*url|linkedin\s*profile)\b", q_text, re.I):
                ans_text = candidate_payload["linkedin_url"]
            elif re.search(r"\b(github|github\s*url|github\s*profile)\b", q_text, re.I):
                ans_text = candidate_payload["github_url"]
            elif re.search(r"\b(portfolio|website|personal\s*site)\b", q_text, re.I):
                ans_text = candidate_payload["portfolio_url"]
            elif re.search(r"\b(years\s*of\s*experience|total\s*experience)\b", q_text, re.I):
                ans_text = str(candidate_payload["years_of_experience"])
            elif re.search(r"\b(degree|highest\s*education|qualification)\b", q_text, re.I):
                ans_text = candidate_payload["highest_degree"]
            elif re.search(r"\b(university|college|institution)\b", q_text, re.I):
                ans_text = candidate_payload["institution"]
            elif re.search(r"\b(graduation\s*year|year\s*of\s*passing)\b", q_text, re.I):
                ans_text = candidate_payload["graduation_year"]
            elif re.search(r"\b(expected\s*salary|desired\s*compensation|salary\s*expectation)\b", q_text, re.I):
                if candidate_payload["expected_salary"]:
                    ans_text = f"{candidate_payload['expected_salary']} {candidate_payload['preferred_currency']}"
            elif re.search(r"\b(authorized\s*to\s*work|work\s*authorization|legal\s*right\s*to\s*work)\b", q_text, re.I):
                is_sensitive = True
                if candidate_payload["work_authorization"] is not None:
                    ans_text = "Yes" if candidate_payload["work_authorization"] else "No"
            elif re.search(r"\b(sponsorship|require\s*sponsorship|visa\s*sponsorship)\b", q_text, re.I):
                is_sensitive = True
                if candidate_payload["requires_sponsorship"] is not None:
                    ans_text = "Yes" if candidate_payload["requires_sponsorship"] else "No"

            if ans_text:
                mapped_answers.append({
                    "question_key": q_key or q_text[:50],
                    "question_text": q_text,
                    "answer_text": ans_text,
                    "is_sensitive": is_sensitive,
                    "confidence_source": source_tag
                })
            else:
                if is_required:
                    missing_fields.append(q_key or q_text)

        return candidate_payload, mapped_answers, missing_fields
