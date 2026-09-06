import pytest
from app.database.models.application import ApplicationPolicy
from app.database.models.job import Job
from app.modules.applications.policy import ApplicationPolicyEngine
from app.shared.constants import PolicyDecision

def test_daily_policy_defaults_to_210_and_30():
    policy = ApplicationPolicy()
    assert policy.daily_application_limit == 210
    assert policy.per_source_daily_limit == 30

def test_policy_engine_source_limit_enforced():
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=50.0,
        daily_application_limit=210,
        per_source_daily_limit=30
    )
    job = Job(company_name='TestCorp', title='Engineer', location='Remote')
    
    # Within source limit
    approved, decision, _ = ApplicationPolicyEngine.evaluate(
        policy=policy,
        job=job,
        daily_applications_count=20,
        source_daily_applications_count=29
    )
    assert approved

    # Exceeding source limit
    approved, decision, _ = ApplicationPolicyEngine.evaluate(
        policy=policy,
        job=job,
        daily_applications_count=20,
        source_daily_applications_count=30
    )
    assert not approved
    assert decision == PolicyDecision.SKIP_DAILY_LIMIT

def test_policy_engine_global_limit_enforced():
    policy = ApplicationPolicy(
        auto_apply_enabled=True,
        minimum_match_score=50.0,
        daily_application_limit=210,
        per_source_daily_limit=30
    )
    job = Job(company_name='TestCorp', title='Engineer', location='Remote')
    
    # Exceeding global limit of 210
    approved, decision, _ = ApplicationPolicyEngine.evaluate(
        policy=policy,
        job=job,
        daily_applications_count=210,
        source_daily_applications_count=10
    )
    assert not approved
    assert decision == PolicyDecision.SKIP_DAILY_LIMIT
