import pytest
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database.models.application import Application, ApplicationPolicy, AutoApplyDailyRun
from app.database.models.job import Job, JobSource
from app.database.models.match import JobMatch
from app.database.models.user import User, UserProfile
from app.shared.constants import (
    ApplicationStatus,
    SubmissionMethod,
    ConnectorCapabilityStatus,
)
from app.modules.applications.daily_routine import AutoApplyDailyRoutineService


def test_calculate_next_scheduled_run():
    ist = ZoneInfo('Asia/Kolkata')
    
    # 03:00 UTC = 08:30 IST (before 10:00 AM IST)
    before_10 = datetime(2026, 9, 6, 3, 0, tzinfo=timezone.utc)
    next_run, display = AutoApplyDailyRoutineService.calculate_next_scheduled_run(before_10)
    next_run_ist = next_run.astimezone(ist)
    assert next_run_ist.hour == 10
    assert next_run_ist.minute == 0
    assert next_run_ist.day == 6
    assert '10:00 AM IST' in display

    # 05:00 UTC = 10:30 IST (after 10:00 AM IST)
    after_10 = datetime(2026, 9, 6, 5, 0, tzinfo=timezone.utc)
    next_run_tomorrow, display_tomorrow = AutoApplyDailyRoutineService.calculate_next_scheduled_run(after_10)
    next_run_tomorrow_ist = next_run_tomorrow.astimezone(ist)
    assert next_run_tomorrow_ist.hour == 10
    assert next_run_tomorrow_ist.minute == 0
    assert next_run_tomorrow_ist.day == 7
    assert '10:00 AM IST' in display_tomorrow


@pytest.mark.asyncio
async def test_daily_routine_execution_and_metrics(async_session: AsyncSession):
    # 1. Create a test user with profile
    user = User(
        id=uuid.uuid4(),
        email=f'autoapply_test_{uuid.uuid4().hex[:8]}@example.com',
        hashed_password='hashed_pw',
        full_name='Test Daily AutoApply User',
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # User Profile
    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        headline='Senior Backend Engineer',
        summary='Experienced Python engineer',
        target_roles=['Backend Engineer'],
        years_of_experience=6,
    )
    async_session.add(profile)

    # Policy: enabled, min match score 80
    policy = ApplicationPolicy(
        id=uuid.uuid4(),
        user_id=user.id,
        auto_apply_enabled=True,
        minimum_match_score=80.0,
        duplicate_protection=True,
    )
    async_session.add(policy)

    # Job Source: External / Scraping only
    source = JobSource(
        id=uuid.uuid4(),
        name='General Scraped Board',
        slug='scraped-board',
        connector_type='SCRAPER',
        capability_status=ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value,
        is_active=True,
    )
    async_session.add(source)

    # Job 1: High match (92), eligible, external board -> EXTERNAL_APPLICATION_REQUIRED
    job1 = Job(
        id=uuid.uuid4(),
        job_source_id=source.id,
        title='Backend Python Developer',
        company_name='Acme Systems',
        description='Senior role building APIs',
        remote_type='REMOTE',
        deduplication_hash=f'hash_1_{uuid.uuid4().hex[:8]}',
        is_active=True,
    )
    async_session.add(job1)

    # Job 2: Low match (65) -> Skipped
    job2 = Job(
        id=uuid.uuid4(),
        job_source_id=source.id,
        title='Frontend React Developer',
        company_name='Beta Corp',
        description='Frontend role',
        remote_type='REMOTE',
        deduplication_hash=f'hash_2_{uuid.uuid4().hex[:8]}',
        is_active=True,
    )
    async_session.add(job2)

    # Job 3: High match (88), but already applied -> Duplicate skipped
    job3 = Job(
        id=uuid.uuid4(),
        job_source_id=source.id,
        title='Staff Python Engineer',
        company_name='Gamma Ltd',
        description='Staff role',
        remote_type='REMOTE',
        deduplication_hash=f'hash_3_{uuid.uuid4().hex[:8]}',
        is_active=True,
    )
    async_session.add(job3)
    await async_session.flush()

    # Pre-existing application for Job 3
    existing_app = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job3.id,
        status=ApplicationStatus.APPLIED.value,
        submission_method=SubmissionMethod.DIRECT_API.value,
    )
    async_session.add(existing_app)

    # Matches
    m1 = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job1.id,
        overall_score=92.0,
        eligibility_status='ELIGIBLE',
    )
    m2 = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job2.id,
        overall_score=65.0,
        eligibility_status='REVIEW',
    )
    m3 = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job3.id,
        overall_score=88.0,
        eligibility_status='ELIGIBLE',
    )
    async_session.add_all([m1, m2, m3])
    await async_session.commit()

    # 2. Execute Daily Routine
    svc = AutoApplyDailyRoutineService(async_session)
    scheduled_time = datetime(2026, 9, 6, 4, 30, tzinfo=timezone.utc)
    run_record = await svc.execute_daily_routine_for_user(user.id, scheduled_time=scheduled_time)

    # 3. Assert Run Metrics
    assert run_record is not None
    assert run_record.status == 'COMPLETED'
    assert run_record.matching_jobs >= 2  # job1 and job3 have score >= 80
    assert run_record.already_applied_count == 1  # job3
    assert run_record.manual_required_count == 1  # job1 on scraped board
    assert run_record.applied_count == 0  # No fake submissions for scraper!
    assert run_record.failed_count == 0

    # 4. Check Routine Info
    info = await svc.get_routine_info(user.id)
    assert info.status == 'Active'
    assert info.auto_apply_enabled is True
    assert '10:00 AM IST' in info.schedule_time_display
    assert info.last_run is not None
    assert info.last_run.matching_jobs >= 2

    # 5. Check History
    history = await svc.get_history(user.id)
    assert len(history) >= 1
    assert history[0].id == run_record.id


@pytest.mark.asyncio
async def test_daily_routine_toggle_and_trigger_api(async_client: httpx.AsyncClient, test_user: User, async_session: AsyncSession):
    # Setup profile and policy
    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=test_user.id,
        headline='Fullstack Engineer',
        summary='Experienced Fullstack Engineer',
        target_roles=['Software Engineer'],
        years_of_experience=5,
    )
    async_session.add(profile)
    policy = ApplicationPolicy(
        id=uuid.uuid4(),
        user_id=test_user.id,
        auto_apply_enabled=True,
        minimum_match_score=75.0,
    )
    async_session.add(policy)
    await async_session.commit()

    from app.core.security import create_access_token
    token = create_access_token(test_user.id)
    headers = {'Authorization': f'Bearer {token}'}

    # 1. GET daily routine info
    resp = await async_client.get('/api/v1/auto-apply/daily-routine', headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert '10:00 AM IST' in data['schedule_time_display']
    assert data['status'] == 'Active'
    assert data['auto_apply_enabled'] is True

    # 2. Toggle OFF
    toggle_resp = await async_client.post('/api/v1/auto-apply/daily-routine/toggle?enabled=false', headers=headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()['auto_apply_enabled'] is False
    assert toggle_resp.json()['status'] == 'Disabled'

    # 3. Toggle ON
    toggle_on = await async_client.post('/api/v1/auto-apply/daily-routine/toggle?enabled=true', headers=headers)
    assert toggle_on.status_code == 200
    assert toggle_on.json()['auto_apply_enabled'] is True
    assert toggle_on.json()['status'] == 'Active'

    # 4. Trigger routine now
    trigger_resp = await async_client.post('/api/v1/auto-apply/daily-routine/trigger-now', headers=headers)
    assert trigger_resp.status_code == 200
    run_data = trigger_resp.json()
    assert run_data['status'] == 'COMPLETED'
    assert 'matching_jobs' in run_data


@pytest.mark.asyncio
async def test_worker_daily_routine_scheduling_detection(async_session: AsyncSession, test_user: User):
    from worker import ProductionWorker
    worker = ProductionWorker()

    # When hour < 10, should not trigger
    early_ist = datetime(2026, 9, 6, 8, 30, tzinfo=ZoneInfo('Asia/Kolkata'))
    await worker._check_and_trigger_daily_routine(async_session, now_kolkata=early_ist)
    assert getattr(worker, '_last_daily_routine_date', None) is None

    # When hour >= 10, triggers and sets _last_daily_routine_date
    late_ist = datetime(2026, 9, 6, 10, 15, tzinfo=ZoneInfo('Asia/Kolkata'))
    await worker._check_and_trigger_daily_routine(async_session, now_kolkata=late_ist)
    assert getattr(worker, '_last_daily_routine_date', None) == '2026-09-06'

    # Same day subsequent check does not trigger again (idempotent)
    await worker._check_and_trigger_daily_routine(async_session, now_kolkata=late_ist)
    assert getattr(worker, '_last_daily_routine_date', None) == '2026-09-06'

