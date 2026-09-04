import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User, UserProfile, JobPreference
from app.modules.auth.service import AuthService, get_current_user
from app.shared.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserRead,
    JobPreferenceUpdate,
    JobPreferenceRead,
    APIResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.register_user(payload)
    return UserRead.model_validate(user, from_attributes=True)

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.authenticate_user(payload)

@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user, from_attributes=True)

@router.put("/preferences", response_model=JobPreferenceRead)
async def update_preferences(
    payload: JobPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pref = current_user.job_preferences
    if not pref:
        pref = JobPreference(user_id=current_user.id)
        db.add(pref)

    pref.desired_titles = payload.desired_titles
    pref.desired_locations = payload.desired_locations
    pref.remote_types = payload.remote_types
    pref.min_base_salary = payload.min_base_salary
    pref.max_base_salary = payload.max_base_salary
    pref.currency = payload.currency
    pref.target_industries = payload.target_industries
    pref.sponsorship_required = payload.sponsorship_required

    await db.commit()
    await db.refresh(pref)
    return JobPreferenceRead.model_validate(pref, from_attributes=True)
