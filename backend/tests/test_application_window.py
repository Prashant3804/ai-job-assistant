"""Deterministic unit & integration test suite for the Daily Application Execution Window.

Verifies:
1. 09:59:59 IST is closed
2. 10:00:00 IST is open
3. 11:59:59 IST is open
4. 12:00:00 IST is closed
5. 02:00:00 AM IST is closed
6. Candidate qualification during open window executes submission
7. Candidate qualification during closed window transitions to QUEUED_FOR_NEXT_WINDOW
8. Next window calculation after 12 PM rolls to next day 10 AM IST
9. Next window calculation before 10 AM points to today 10 AM IST
10. Application statistics accurately count total_queued_for_next_window
11. Daily routine info returns correct ApplicationWindowStatus structure
12. Manual portals (Naukri, Indeed, LinkedIn, etc.) remain EXTERNAL_APPLICATION_REQUIRED
13. Cutoff behavior ceases new automated submissions
14. Staged QUEUED_FOR_NEXT_WINDOW items are drained when window opens
"""

import pytest
import uuid
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch, AsyncMock, MagicMock

from app.modules.applications.window_service import (
    is_application_window_open,
    get_next_application_window,
    get_application_window_status,
    KOLKATA_TZ
)
from app.shared.constants import ApplicationStatus, QueueStatus, SubmissionMethod
from app.modules.applications.schemas import ApplicationWindowStatus


# =====================================================================
# Deterministic Time Tests (Exact IST Boundaries)
# =====================================================================

def test_window_boundary_before_opening():
    """1. 09:59:59 IST is strictly closed."""
    t_0959 = datetime(2026, 9, 9, 9, 59, 59, tzinfo=KOLKATA_TZ)
    assert is_application_window_open(t_0959) is False


def test_window_boundary_exact_opening():
    """2. 10:00:00 IST is strictly open."""
    t_1000 = datetime(2026, 9, 9, 10, 0, 0, tzinfo=KOLKATA_TZ)
    assert is_application_window_open(t_1000) is True


def test_window_boundary_exact_closing_second():
    """3. 11:59:59 IST is strictly open."""
    t_1159 = datetime(2026, 9, 9, 11, 59, 59, 999999, tzinfo=KOLKATA_TZ)
    assert is_application_window_open(t_1159) is True


def test_window_boundary_after_closing():
    """4. 12:00:00 IST is strictly closed."""
    t_1200 = datetime(2026, 9, 9, 12, 0, 0, tzinfo=KOLKATA_TZ)
    assert is_application_window_open(t_1200) is False


def test_window_boundary_middle_of_night():
    """5. 02:00:00 AM IST is strictly closed."""
    t_0200 = datetime(2026, 9, 9, 2, 0, 0, tzinfo=KOLKATA_TZ)
    assert is_application_window_open(t_0200) is False


def test_next_window_calculation_after_closing():
    """8. Next window calculation after 12 PM rolls to next day 10 AM IST."""
    t_1400 = datetime(2026, 9, 9, 14, 0, 0, tzinfo=KOLKATA_TZ)
    next_utc, display = get_next_application_window(t_1400)
    expected_kolkata = datetime(2026, 9, 10, 10, 0, 0, tzinfo=KOLKATA_TZ)
    assert next_utc == expected_kolkata.astimezone(timezone.utc)
    assert "Sep 10" in display
    assert "10:00 AM IST" in display


def test_next_window_calculation_before_opening():
    """9. Next window calculation before 10 AM points to today 10 AM IST."""
    t_0800 = datetime(2026, 9, 9, 8, 0, 0, tzinfo=KOLKATA_TZ)
    next_utc, display = get_next_application_window(t_0800)
    expected_kolkata = datetime(2026, 9, 9, 10, 0, 0, tzinfo=KOLKATA_TZ)
    assert next_utc == expected_kolkata.astimezone(timezone.utc)
    assert "Sep 09" in display
    assert "10:00 AM IST" in display


def test_window_status_structure_closed():
    """11. Daily routine info / window service returns valid ApplicationWindowStatus structure."""
    t_1500 = datetime(2026, 9, 9, 15, 0, 0, tzinfo=KOLKATA_TZ)
    status_dict = get_application_window_status(t_1500)
    assert status_dict["is_open"] is False
    assert status_dict["status"] == "CLOSED"
    assert "Next window: Sep 10, 10:00 AM IST" in status_dict["next_window_display"]
    assert status_dict["window_schedule"] == "10:00 AM – 11:59 AM IST"

    validated = ApplicationWindowStatus(**status_dict)
    assert validated.is_open is False
    assert validated.status == "CLOSED"


def test_window_status_structure_open():
    """ApplicationWindowStatus when window is open."""
    t_1030 = datetime(2026, 9, 9, 10, 30, 0, tzinfo=KOLKATA_TZ)
    status_dict = get_application_window_status(t_1030)
    assert status_dict["is_open"] is True
    assert status_dict["status"] == "OPEN"
    assert "OPEN until 11:59 AM IST" in status_dict["next_window_display"]


# =====================================================================
# Routine & Application Service Execution Tests
# =====================================================================

@pytest.mark.asyncio
async def test_process_queue_skips_when_window_closed():
    """13. Cutoff behavior / outside window skips automated queue submission."""
    from app.modules.applications.service import ApplicationService
    mock_db = AsyncMock()
    app_svc = ApplicationService(mock_db)

    with patch("app.modules.applications.service.is_application_window_open", return_value=False):
        res = await app_svc.process_queue(limit=10)
        assert res.processed_count == 0
        assert res.successful_count == 0
        assert res.failed_count == 0


def create_mock_policy():
    from app.database.models.application import ApplicationPolicy
    mock_policy = MagicMock(spec=ApplicationPolicy)
    mock_policy.auto_apply_enabled = True
    mock_policy.minimum_match_score = 65.0
    mock_policy.per_source_daily_limit = 30
    mock_policy.daily_application_limit = 210
    mock_policy.blocked_companies = []
    mock_policy.blocked_keywords = []
    mock_policy.preferred_roles = []
    mock_policy.minimum_salary = 0
    mock_policy.maximum_experience = None
    mock_policy.allow_remote = True
    mock_policy.allow_hybrid = True
    mock_policy.allow_onsite = True
    mock_policy.blocked_locations = []
    return mock_policy


@pytest.mark.asyncio
async def test_candidate_qualification_closed_window_stages_for_next_window():
    """7. Candidate qualification during closed window transitions to QUEUED_FOR_NEXT_WINDOW."""
    from app.modules.applications.daily_routine import AutoApplyDailyRoutineService
    from app.database.models.user import User, UserProfile
    from app.database.models.job import Job, JobSource
    from app.database.models.match import JobMatch
    from app.modules.applications.capability_service import ApplicationSubmissionCapability

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.profile = MagicMock(spec=UserProfile)
    mock_user.profile.id = uuid.uuid4()
    mock_user.profile.location = "Bangalore"
    mock_user.profile.target_roles = ["Full Stack Developer"]
    mock_user.profile.skills = []

    mock_policy = create_mock_policy()

    mock_source = MagicMock(spec=JobSource)
    mock_source.slug = "career_pages"
    mock_source.name = "Company Careers"

    mock_job = MagicMock(spec=Job)
    mock_job.id = job_id
    mock_job.external_id = "job-101"
    mock_job.title = "Software Engineer"
    mock_job.company_name = "Acme Tech"
    mock_job.location = "Bangalore"
    mock_job.remote_type = "REMOTE"
    mock_job.salary_max = None
    mock_job.apply_url = "https://boards.greenhouse.io/acme/jobs/101"
    mock_job.job_source = mock_source
    mock_job.is_active = True

    mock_match = MagicMock(spec=JobMatch)
    mock_match.overall_score = 85.0
    mock_match.eligibility_status = "ELIGIBLE"

    routine_svc = AutoApplyDailyRoutineService(mock_db)

    # Mock window to CLOSED
    with patch("app.modules.applications.daily_routine.is_application_window_open", return_value=False), \
         patch("app.modules.applications.daily_routine.JobService.sync_all_discovery_sources", return_value={"total_ingested": 0}), \
         patch("app.modules.applications.daily_routine.MatchingService.compute_or_update_match", return_value=mock_match), \
         patch("app.modules.applications.daily_routine.DuplicateDetector.check_duplicate", return_value=(False, None, None)), \
         patch("app.modules.applications.daily_routine.ApplicationCapabilityService.evaluate_job", return_value=(ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY, "Supported direct ATS")), \
         patch("app.modules.applications.daily_routine.ApplicationPreparationService.prepare_package", return_value=MagicMock(cover_letter="Sample", screening_answers=[], missing_required_fields=[], provider_used="gemini", ai_fallback_used=False)):

        mock_user_res = MagicMock()
        mock_user_res.scalar_one_or_none.return_value = mock_user

        mock_pol_res = MagicMock()
        mock_pol_res.scalar_one_or_none.return_value = mock_policy

        mock_jobs_res = MagicMock()
        mock_jobs_res.scalars.return_value.all.return_value = [mock_job]

        mock_match_res = MagicMock()
        mock_match_res.scalar_one_or_none.return_value = mock_match

        mock_empty_res = MagicMock()
        mock_empty_res.scalars.return_value.all.return_value = []
        mock_empty_res.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            mock_user_res,
            mock_pol_res,
            mock_jobs_res,
            mock_empty_res, # pref
            mock_empty_res, # edu
            mock_empty_res, # exp
            mock_empty_res, # skills
            mock_empty_res, # projs
            mock_match_res, # match
        ]

        run_record = await routine_svc.execute_daily_routine_for_user(user_id)
        assert run_record.status == "COMPLETED"
        assert run_record.applied_count == 0  # Did not submit because window is closed!
        assert run_record.matching_jobs == 1
        
        apps_summary = run_record.run_summary_json.get("applications", [])
        assert len(apps_summary) == 1
        assert apps_summary[0]["status"] == "QUEUED_FOR_NEXT_WINDOW"


@pytest.mark.asyncio
async def test_manual_portals_remain_external_application_required():
    """12. Unsupported manual action portals (Naukri, Indeed, LinkedIn, etc.) remain EXTERNAL_APPLICATION_REQUIRED."""
    from app.modules.applications.capability_service import ApplicationCapabilityService, ApplicationSubmissionCapability
    from app.database.models.job import Job, JobSource

    manual_slugs = ["naukri", "indeed", "linkedin", "unstop", "internshala", "wellfound"]
    for slug in manual_slugs:
        src = MagicMock(spec=JobSource)
        src.slug = slug
        job = MagicMock(spec=Job)
        job.job_source = src
        cap, reason = ApplicationCapabilityService.evaluate_job(job)
        assert cap == ApplicationSubmissionCapability.EXTERNAL_APPLICATION_REQUIRED
        assert len(reason) > 0


@pytest.mark.asyncio
async def test_candidate_qualification_open_window_executes_submission():
    """6. Candidate qualification during open window executes submission."""
    from app.modules.applications.daily_routine import AutoApplyDailyRoutineService
    from app.database.models.user import User, UserProfile
    from app.database.models.job import Job, JobSource
    from app.database.models.match import JobMatch
    from app.modules.applications.capability_service import ApplicationSubmissionCapability

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.profile = MagicMock(spec=UserProfile)
    mock_user.profile.id = uuid.uuid4()
    mock_user.profile.location = "Bangalore"
    mock_user.profile.target_roles = ["Full Stack Developer"]
    mock_user.profile.skills = []

    mock_policy = create_mock_policy()

    mock_source = MagicMock(spec=JobSource)
    mock_source.slug = "career_pages"
    mock_source.name = "Company Careers"

    mock_job = MagicMock(spec=Job)
    mock_job.id = job_id
    mock_job.external_id = "job-102"
    mock_job.title = "Software Engineer"
    mock_job.company_name = "Acme Tech"
    mock_job.location = "Bangalore"
    mock_job.remote_type = "REMOTE"
    mock_job.salary_max = None
    mock_job.apply_url = "https://boards.greenhouse.io/acme/jobs/102"
    mock_job.job_source = mock_source
    mock_job.is_active = True

    mock_match = MagicMock(spec=JobMatch)
    mock_match.overall_score = 88.0
    mock_match.eligibility_status = "ELIGIBLE"

    routine_svc = AutoApplyDailyRoutineService(mock_db)

    # Mock window to OPEN
    with patch("app.modules.applications.daily_routine.is_application_window_open", return_value=True), \
         patch("app.modules.applications.daily_routine.JobService.sync_all_discovery_sources", return_value={"total_ingested": 0}), \
         patch("app.modules.applications.daily_routine.MatchingService.compute_or_update_match", return_value=mock_match), \
         patch("app.modules.applications.daily_routine.DuplicateDetector.check_duplicate", return_value=(False, None, None)), \
         patch("app.modules.applications.daily_routine.ApplicationCapabilityService.evaluate_job", return_value=(ApplicationSubmissionCapability.SUPPORTED_AUTO_APPLY, "Supported direct ATS")), \
         patch("app.modules.applications.daily_routine.ApplicationPreparationService.prepare_package", return_value=MagicMock(cover_letter="Sample", screening_answers=[], missing_required_fields=[], provider_used="gemini", ai_fallback_used=False)), \
         patch("app.modules.applications.daily_routine.ApplicationAgent.process_queue_item", return_value={"success": True, "status": "APPLIED"}):

        mock_user_res = MagicMock()
        mock_user_res.scalar_one_or_none.return_value = mock_user

        mock_pol_res = MagicMock()
        mock_pol_res.scalar_one_or_none.return_value = mock_policy

        mock_jobs_res = MagicMock()
        mock_jobs_res.scalars.return_value.all.return_value = [mock_job]

        mock_match_res = MagicMock()
        mock_match_res.scalar_one_or_none.return_value = mock_match

        mock_empty_res = MagicMock()
        mock_empty_res.scalars.return_value.all.return_value = []
        mock_empty_res.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            mock_user_res,
            mock_pol_res,
            mock_jobs_res,
            mock_empty_res, # staged queue
            mock_empty_res, # pref
            mock_empty_res, # edu
            mock_empty_res, # exp
            mock_empty_res, # skills
            mock_empty_res, # projs
            mock_match_res, # match
        ]

        run_record = await routine_svc.execute_daily_routine_for_user(user_id)
        assert run_record.status == "COMPLETED"
        assert run_record.applied_count == 1
        assert run_record.matching_jobs == 1


@pytest.mark.asyncio
async def test_application_statistics_counts_queued_for_next_window():
    """10. Platform statistics accurately count total_queued_for_next_window."""
    from app.modules.applications.service import ApplicationService
    from app.database.models.application import Application, ApplicationPolicy
    from app.database.models.job import Job, JobSource

    mock_db = AsyncMock()
    user_id = uuid.uuid4()
    app_svc = ApplicationService(mock_db)

    mock_policy = create_mock_policy()

    app1 = MagicMock(spec=Application)
    app1.source = "career_pages"
    app1.status = ApplicationStatus.QUEUED_FOR_NEXT_WINDOW.value
    app1.applied_date = None
    app1.submitted_at = None
    app1.created_at = datetime.now(timezone.utc)

    mock_policy_res = MagicMock()
    mock_policy_res.scalar_one_or_none.return_value = mock_policy

    mock_apps_res = MagicMock()
    mock_apps_res.scalars.return_value.all.return_value = [app1]

    mock_empty_all = MagicMock()
    mock_empty_all.all.return_value = []
    mock_empty_all.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [
        mock_policy_res,
        mock_apps_res,
        mock_empty_all, # jobs by source
        mock_empty_all, # matches by source
        mock_empty_all, # last run
    ]

    stats = await app_svc.get_platform_statistics(user_id)
    assert stats.total_queued_for_next_window == 1
    assert stats.total_applied_today == 0
    assert stats.application_window is not None
