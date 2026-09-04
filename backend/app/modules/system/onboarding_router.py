import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.user import User, UserProfile, JobPreference
from app.database.models.resume import Resume
from app.database.models.application import ApplicationPolicy
from app.database.models.email import MailboxConnection
from app.modules.auth.service import get_current_user
from app.core.config import settings
from app.shared.schemas import (
    OnboardingStateResponse,
    OnboardingStepRequest,
    APIResponse,
)

router = APIRouter(prefix="/onboarding", tags=["User Onboarding Workflow"])

@router.get("/state", response_model=OnboardingStateResponse)
async def get_onboarding_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Profile Check
    stmt_prof = select(UserProfile).where(UserProfile.user_id == current_user.id)
    prof_res = await db.execute(stmt_prof)
    profile = prof_res.scalar_one_or_none()

    current_step = profile.onboarding_step if profile else 1
    is_completed = profile.onboarding_completed if profile else False
    profile_configured = bool(profile and (profile.headline or profile.skills))

    # 2. Resume Check
    stmt_res = select(Resume).where(Resume.user_id == current_user.id)
    res_res = await db.execute(stmt_res)
    resume_uploaded = bool(res_res.scalar_one_or_none())

    # 3. Preferences Check
    stmt_pref = select(JobPreference).where(JobPreference.user_id == current_user.id)
    pref_res = await db.execute(stmt_pref)
    pref = pref_res.scalar_one_or_none()
    preferences_configured = bool(pref and (pref.desired_titles or pref.desired_locations))

    # 4. Policy Check
    stmt_pol = select(ApplicationPolicy).where(ApplicationPolicy.user_id == current_user.id)
    pol_res = await db.execute(stmt_pol)
    policy = pol_res.scalar_one_or_none()
    policy_configured = bool(policy)

    # 5. Mailbox Check
    stmt_mb = select(MailboxConnection).where(MailboxConnection.user_id == current_user.id)
    mb_res = await db.execute(stmt_mb)
    mailbox_connected = bool(mb_res.scalar_one_or_none())

    # 6. AI Config Check
    ai_configured = bool(settings.DEFAULT_AI_PROVIDER.lower() in ["omniroute", "openai", "gemini", "mock"])

    return OnboardingStateResponse(
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        current_step=current_step,
        is_completed=is_completed,
        profile_configured=profile_configured,
        resume_uploaded=resume_uploaded,
        preferences_configured=preferences_configured,
        policy_configured=policy_configured,
        mailbox_connected=mailbox_connected,
        ai_configured=ai_configured,
    )

@router.post("/step", response_model=OnboardingStateResponse)
async def update_onboarding_step(
    payload: OnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id, onboarding_step=payload.step)
        db.add(profile)
    else:
        profile.onboarding_step = max(1, min(10, payload.step))

    await db.commit()
    await db.refresh(profile)
    return await get_onboarding_state(current_user=current_user, db=db)

@router.post("/complete", response_model=OnboardingStateResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id, onboarding_step=10, onboarding_completed=True)
        db.add(profile)
    else:
        profile.onboarding_step = 10
        profile.onboarding_completed = True

    await db.commit()
    await db.refresh(profile)
    return await get_onboarding_state(current_user=current_user, db=db)
