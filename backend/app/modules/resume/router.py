import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User, UserProfile
from app.database.models.resume import Resume, ResumeVersion
from app.modules.auth.service import get_current_user
from app.modules.resume.extraction_service import ResumeExtractionService
from app.modules.resume.profile_service import CandidateProfileService
from app.modules.resume.schemas import (
    StructuredResumeData,
    SaveProfileRequest,
    CreateResumeVersionRequest,
    ResumeVersionResponse,
)
from app.shared.schemas import ResumeRead, UserProfileRead, UserProfileUpdate, APIResponse

router = APIRouter(prefix="/resume", tags=["Resume Intelligence"])

@router.post("/upload", response_model=Dict if False else dict, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_resume(
    title: str = Form("Master Resume"),
    raw_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    extractor = ResumeExtractionService()
    profile_service = CandidateProfileService(db)

    extracted_text = raw_text
    file_format = "TEXT"
    file_url = None

    if file:
        file_bytes = await file.read()
        filename = file.filename or "resume.pdf"
        target_path, secure_filename = extractor.save_uploaded_file(filename, file_bytes)
        file_url = f"/uploads/resumes/{secure_filename}"
        file_format = os.path.splitext(filename)[1].replace(".", "").upper()
        extracted_text = extractor.extract_raw_text(filename, file_bytes)

    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document or resume text was provided."
        )

    # Run AI structured extraction
    structured_data = await extractor.extract_and_structure_resume(extracted_text)

    # Save Resume record to DB
    resume = Resume(
        user_id=current_user.id,
        title=title,
        is_primary=True,
        raw_text=extracted_text,
        file_url=file_url,
        file_format=file_format,
        parsed_data=structured_data.model_dump(mode="json")
    )
    db.add(resume)
    await db.flush()

    # Automatically synchronize initial profile
    save_payload = SaveProfileRequest(
        resume_id=resume.id,
        personal=structured_data.personal,
        education=structured_data.education,
        skills=structured_data.skills,
        experience=structured_data.experience,
        projects=structured_data.projects,
        certifications=structured_data.certifications
    )
    await profile_service.save_approved_profile(current_user.id, save_payload)

    # Create initial v1 snapshot
    await profile_service.create_resume_version(
        user_id=current_user.id,
        payload=CreateResumeVersionRequest(
            resume_id=resume.id,
            version_title="Initial Ingestion (v1)",
            structured_data=structured_data
        )
    )

    return {
        "success": True,
        "message": "Resume successfully uploaded and parsed.",
        "resume_id": str(resume.id),
        "structured_data": structured_data.model_dump(mode="json"),
        "raw_text": extracted_text,
    }

@router.post("/reanalyze/{resume_id}", response_model=dict)
async def reanalyze_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    extractor = ResumeExtractionService()
    structured_data = await extractor.extract_and_structure_resume(resume.raw_text or "")
    
    resume.parsed_data = structured_data.model_dump(mode="json")
    await db.commit()

    return {
        "success": True,
        "message": "Resume re-analyzed successfully.",
        "structured_data": structured_data.model_dump(mode="json"),
    }

@router.post("/save-profile", response_model=UserProfileRead)
async def save_approved_profile(
    payload: SaveProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateProfileService(db)
    profile = await service.save_approved_profile(current_user.id, payload)
    return UserProfileRead.model_validate(profile, from_attributes=True)

@router.post("/versions", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_resume_version(
    payload: CreateResumeVersionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateProfileService(db)
    version = await service.create_resume_version(current_user.id, payload)
    return ResumeVersionResponse.model_validate(version, from_attributes=True)

@router.get("/versions/{resume_id}", response_model=List[ResumeVersionResponse])
async def list_resume_versions(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateProfileService(db)
    versions = await service.get_resume_versions(resume_id, current_user.id)
    return [ResumeVersionResponse.model_validate(v, from_attributes=True) for v in versions]

@router.get("/profile", response_model=UserProfileRead)
async def get_current_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    stmt = (
        select(UserProfile)
        .options(
            selectinload(UserProfile.skills),
            selectinload(UserProfile.educations),
            selectinload(UserProfile.experiences),
            selectinload(UserProfile.projects),
        )
        .where(UserProfile.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfileRead.model_validate(profile, from_attributes=True)

@router.put("/profile", response_model=UserProfileRead)
async def update_current_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CandidateProfileService(db)
    profile = await service.update_candidate_profile(current_user.id, payload)
    return UserProfileRead.model_validate(profile, from_attributes=True)


@router.get("", response_model=List[ResumeRead])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    stmt = select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())
    res = await db.execute(stmt)
    return [ResumeRead.model_validate(r, from_attributes=True) for r in res.scalars().all()]

@router.get("/{resume_id}")
async def get_resume_detail(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id": str(resume.id),
        "title": resume.title,
        "is_primary": resume.is_primary,
        "file_url": resume.file_url,
        "file_format": resume.file_format,
        "raw_text": resume.raw_text,
        "parsed_data": resume.parsed_data,
        "created_at": resume.created_at.isoformat(),
        "updated_at": resume.updated_at.isoformat()
    }
