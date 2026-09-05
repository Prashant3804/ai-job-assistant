import re
from typing import Tuple, Optional, List
from app.database.models.application import ApplicationPolicy
from app.database.models.job import Job
from app.database.models.match import JobMatch
from app.shared.constants import PolicyDecision

class ApplicationPolicyEngine:
    """Evaluates whether a discovered and matched job satisfies candidate auto-apply criteria."""

    @staticmethod
    def evaluate(
        policy: Optional[ApplicationPolicy],
        job: Job,
        match: Optional[JobMatch] = None,
        daily_applications_count: int = 0,
        source_daily_applications_count: int = 0
    ) -> Tuple[bool, PolicyDecision, str]:
        # 1. Default Policy Guard
        if not policy or not policy.auto_apply_enabled:
            return False, PolicyDecision.SKIP_LOW_MATCH, "Auto-apply is not enabled in candidate settings."

        # 2. Daily Global Limit Check (if configured; None = unlimited)
        if policy.daily_application_limit is not None and daily_applications_count >= policy.daily_application_limit:
            return False, PolicyDecision.SKIP_DAILY_LIMIT, f"Daily application limit ({policy.daily_application_limit}) reached for today."

        # 3. Per-Source Daily Limit Check (if configured; None = unlimited)
        if policy.per_source_daily_limit is not None and source_daily_applications_count >= policy.per_source_daily_limit:
            source_name = job.job_source.name if (hasattr(job, 'job_source') and job.job_source) else getattr(job, 'source', "Platform")
            return False, PolicyDecision.SKIP_DAILY_LIMIT, f"Daily limit for source '{source_name}' ({policy.per_source_daily_limit}) reached for today."

        # 4. Eligibility Check (Independent of Numerical Score)
        if match and match.eligibility_status == "NOT_ELIGIBLE":
            return False, PolicyDecision.SKIP_INELIGIBLE, "Candidate does not meet baseline eligibility criteria for this role."

        # 5. Match Score Threshold Check
        if match is not None:
            if match.overall_score < policy.minimum_match_score:
                return False, PolicyDecision.SKIP_LOW_MATCH, f"Match score {match.overall_score:.1f}% is below required policy threshold {policy.minimum_match_score:.1f}%."

        company_clean = (job.company_name or "").lower().strip()
        title_clean = (job.title or "").lower().strip()
        desc_clean = (job.description or "").lower()
        location_clean = (job.location or "").lower().strip()

        # 6. Blocked Companies Check
        for blocked_company in policy.blocked_companies or []:
            if blocked_company.strip() and blocked_company.strip().lower() in company_clean:
                return False, PolicyDecision.SKIP_BLOCKED_COMPANY, f"Company '{job.company_name}' is in your blocked companies list."

        # 7. Blocked Keywords Check
        for blocked_kw in policy.blocked_keywords or []:
            kw_clean = blocked_kw.strip().lower()
            if kw_clean:
                pattern = rf"\b{re.escape(kw_clean)}\b"
                if re.search(pattern, title_clean) or re.search(pattern, desc_clean):
                    return False, PolicyDecision.SKIP_BLOCKED_KEYWORD, f"Job contains blocked keyword '{blocked_kw}'."

        # 8. Blocked Roles Check
        for blocked_role in policy.blocked_roles or []:
            br_clean = blocked_role.strip().lower()
            if br_clean and br_clean in title_clean:
                return False, PolicyDecision.SKIP_LOW_MATCH, f"Role '{job.title}' matches blocked role '{blocked_role}'."

        # 9. Preferred Roles Check (if configured)
        if policy.preferred_roles and len(policy.preferred_roles) > 0:
            matches_pref_role = False
            for pref_role in policy.preferred_roles:
                pr_clean = pref_role.strip().lower()
                if pr_clean and (pr_clean in title_clean or any(word in title_clean for word in pr_clean.split())):
                    matches_pref_role = True
                    break
            if not matches_pref_role:
                return False, PolicyDecision.SKIP_LOW_MATCH, "Job title does not match candidate preferred roles."

        # 10. Minimum Salary Check
        if policy.minimum_salary and policy.minimum_salary > 0:
            if job.salary_max and job.salary_max < policy.minimum_salary:
                return False, PolicyDecision.SKIP_SALARY, f"Job maximum salary ({job.salary_max}) is below required minimum ({policy.minimum_salary})."

        # 11. Maximum Experience Check
        if policy.maximum_experience is not None and policy.maximum_experience > 0:
            job_exp = getattr(job, "min_years_experience", None)
            if job_exp is not None and job_exp > policy.maximum_experience:
                return False, PolicyDecision.SKIP_EXPERIENCE, f"Job requires {job_exp} years, exceeding your target maximum of {policy.maximum_experience} years."

        # 12. Remote / Work Arrangement Preferences
        rem = (job.remote_type or "ONSITE").upper()
        if rem == "REMOTE" and not policy.allow_remote:
            return False, PolicyDecision.SKIP_LOCATION, "Remote roles are disabled in auto-apply policy."
        if rem == "HYBRID" and not policy.allow_hybrid:
            return False, PolicyDecision.SKIP_LOCATION, "Hybrid roles are disabled in auto-apply policy."
        if rem == "ONSITE" and not policy.allow_onsite:
            return False, PolicyDecision.SKIP_LOCATION, "Onsite roles are disabled in auto-apply policy."

        # 13. Location Filtering
        for blocked_loc in policy.blocked_locations or []:
            bl_clean = blocked_loc.strip().lower()
            if bl_clean and bl_clean in location_clean:
                return False, PolicyDecision.SKIP_LOCATION, f"Location '{job.location}' is in blocked locations list."

        if policy.preferred_locations and len(policy.preferred_locations) > 0 and rem != "REMOTE":
            matches_pref_loc = False
            for pref_loc in policy.preferred_locations:
                pl_clean = pref_loc.strip().lower()
                if pl_clean and pl_clean in location_clean:
                    matches_pref_loc = True
                    break
            if not matches_pref_loc:
                return False, PolicyDecision.SKIP_LOCATION, f"Location '{job.location}' is not in candidate preferred locations list."

        # 14. Allowed Employment Types
        if policy.allowed_employment_types and len(policy.allowed_employment_types) > 0:
            emp = (job.employment_type or "FULL_TIME").upper()
            allowed = [t.upper() for t in policy.allowed_employment_types]
            if emp not in allowed:
                return False, PolicyDecision.SKIP_LOW_MATCH, f"Employment type '{job.employment_type}' is not in allowed employment types."

        # 15. All criteria met
        return True, PolicyDecision.AUTO_APPLY, "Job meets all configured policy criteria for automated application."
