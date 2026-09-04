import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.session import get_db
from app.database.models.user import User, UserProfile, JobPreference
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.core.exceptions import InvalidCredentialsError, DuplicateEntityError
from app.shared.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, payload: UserRegisterRequest) -> User:
        stmt = select(User).where(User.email == payload.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise DuplicateEntityError(f"User with email '{payload.email}' already exists.")

        user = User(
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name,
            is_active=True,
            is_verified=False,
            role="CANDIDATE"
        )
        self.db.add(user)
        await self.db.flush()

        # Create empty profile and default job preferences
        profile = UserProfile(
            user_id=user.id,
            headline="Full Stack Software Engineer",
            summary="Passionate engineer building scalable AI-driven web systems.",
            location="San Francisco, CA",
            remote_preference="REMOTE",
            years_of_experience=4.0,
            target_roles=["Senior Backend Engineer", "Full Stack Engineer", "Python Engineer"]
        )
        preferences = JobPreference(
            user_id=user.id,
            desired_titles=["Senior Backend Engineer", "Full Stack Engineer"],
            desired_locations=["Remote", "San Francisco, CA", "New York, NY"],
            remote_types=["REMOTE", "HYBRID"],
            min_base_salary=140000,
            max_base_salary=200000,
            currency="USD",
            target_industries=["Software", "Fintech", "AI/ML"]
        )
        self.db.add(profile)
        self.db.add(preferences)
        await self.db.commit()

        return await self.get_user_by_id(user.id)

    async def authenticate_user(self, payload: UserLoginRequest) -> TokenResponse:
        user = await self.get_user_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is deactivated.")

        access_token = create_access_token(subject=str(user.id))
        user_read = UserRead.model_validate(user, from_attributes=True)
        return TokenResponse(access_token=access_token, user=user_read)

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.profile).selectinload(UserProfile.skills),
                selectinload(User.profile).selectinload(UserProfile.educations),
                selectinload(User.profile).selectinload(UserProfile.experiences),
                selectinload(User.profile).selectinload(UserProfile.projects),
                selectinload(User.job_preferences),
            )
            .where(User.id == user_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.profile).selectinload(UserProfile.skills),
                selectinload(User.profile).selectinload(UserProfile.educations),
                selectinload(User.profile).selectinload(UserProfile.experiences),
                selectinload(User.profile).selectinload(UserProfile.projects),
                selectinload(User.job_preferences),
            )
            .where(User.email == email)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not token:
        # For development/demo mode without token, fetch the default user or seed user if exists
        stmt = (
            select(User)
            .options(
                selectinload(User.profile).selectinload(UserProfile.skills),
                selectinload(User.profile).selectinload(UserProfile.educations),
                selectinload(User.profile).selectinload(UserProfile.experiences),
                selectinload(User.profile).selectinload(UserProfile.projects),
                selectinload(User.job_preferences),
            )
            .limit(1)
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = decode_token(token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
