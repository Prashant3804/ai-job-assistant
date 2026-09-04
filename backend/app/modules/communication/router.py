import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.shared.constants import (
    DraftIntent,
    DraftStatus,
    RecruiterRelationshipStage,
    InterviewRoundType,
    InterviewStatus,
)
from app.modules.communication.schemas import (
    RecruiterCreate,
    RecruiterUpdate,
    RecruiterResponse,
    DraftGenerationRequest,
    DraftResponse,
    DraftUpdateRequest,
    InterviewSessionCreate,
    InterviewSessionUpdate,
    InterviewSessionResponse,
    InterviewPrepBriefGenerateRequest,
    InterviewPrepBriefResponse,
    FollowUpRecommendation,
)
from app.modules.communication.service import CommunicationService

router = APIRouter(prefix="/communication", tags=["Recruiter AI & Communication Intelligence"])
interviews_router = APIRouter(prefix="/interviews", tags=["Interview Intelligence"])


# ==========================================
# 1. Recruiter CRM Endpoints
# ==========================================

@router.get("/recruiters", response_model=List[RecruiterResponse])
async def list_recruiters(
    stage: Optional[RecruiterRelationshipStage] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked recruiters for the candidate."""
    recruiters = await CommunicationService.list_recruiters(
        db=db, user_id=current_user.id, stage=stage, search=search
    )
    return recruiters


@router.post("/recruiters", response_model=RecruiterResponse, status_code=status.HTTP_201_CREATED)
async def create_recruiter(
    payload: RecruiterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or manually track a new recruiter contact."""
    return await CommunicationService.create_recruiter(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get("/recruiters/{recruiter_id}", response_model=RecruiterResponse)
async def get_recruiter(
    recruiter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recruiter profile and relationship details."""
    recruiter = await CommunicationService.get_recruiter(
        db=db, user_id=current_user.id, recruiter_id=recruiter_id
    )
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return recruiter


@router.put("/recruiters/{recruiter_id}", response_model=RecruiterResponse)
async def update_recruiter(
    recruiter_id: uuid.UUID,
    payload: RecruiterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update recruiter notes, relationship stage, or contact information."""
    recruiter = await CommunicationService.update_recruiter(
        db=db, user_id=current_user.id, recruiter_id=recruiter_id, payload=payload
    )
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return recruiter


@router.delete("/recruiters/{recruiter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recruiter(
    recruiter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete recruiter contact."""
    deleted = await CommunicationService.delete_recruiter(
        db=db, user_id=current_user.id, recruiter_id=recruiter_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Recruiter not found")


# ==========================================
# 2. Contextual AI Response Drafter Endpoints
# ==========================================

@router.post("/drafts/generate", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
async def generate_response_draft(
    payload: DraftGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate contextual AI response draft.
    Enforces Human-in-the-Loop constraint: draft is created with DRAFT status
    and must be explicitly inspected/approved by user.
    """
    return await CommunicationService.create_draft(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get("/drafts", response_model=List[DraftResponse])
async def list_drafts(
    intent: Optional[DraftIntent] = None,
    status: Optional[DraftStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List response drafts for candidate."""
    return await CommunicationService.list_drafts(
        db=db, user_id=current_user.id, intent=intent, status=status
    )


@router.get("/drafts/{draft_id}", response_model=DraftResponse)
async def get_draft(
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get draft content and metadata."""
    draft = await CommunicationService.get_draft(
        db=db, user_id=current_user.id, draft_id=draft_id
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.put("/drafts/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: uuid.UUID,
    payload: DraftUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit draft content, tone, or approval status."""
    draft = await CommunicationService.update_draft(
        db=db, user_id=current_user.id, draft_id=draft_id, payload=payload
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/drafts/{draft_id}/approve", response_model=DraftResponse)
async def approve_draft(
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly approve an AI communication draft."""
    draft = await CommunicationService.approve_draft(
        db=db, user_id=current_user.id, draft_id=draft_id
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a communication draft."""
    deleted = await CommunicationService.delete_draft(
        db=db, user_id=current_user.id, draft_id=draft_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")


# ==========================================
# 3. Interview Sessions & Prep Brief Endpoints
# ==========================================

@router.get("/interviews", response_model=List[InterviewSessionResponse])
@interviews_router.get("", response_model=List[InterviewSessionResponse])
async def list_interviews(
    status: Optional[InterviewStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scheduled interviews."""
    return await CommunicationService.list_interviews(
        db=db, user_id=current_user.id, status=status
    )


@router.post("/interviews", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
@interviews_router.post("", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a scheduled interview session."""
    return await CommunicationService.create_interview(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get("/interviews/{interview_id}", response_model=InterviewSessionResponse)
@interviews_router.get("/{interview_id}", response_model=InterviewSessionResponse)
async def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get interview session details."""
    interview = await CommunicationService.get_interview(
        db=db, user_id=current_user.id, interview_id=interview_id
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@router.put("/interviews/{interview_id}", response_model=InterviewSessionResponse)
@interviews_router.put("/{interview_id}", response_model=InterviewSessionResponse)
async def update_interview(
    interview_id: uuid.UUID,
    payload: InterviewSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update interview session details or status."""
    interview = await CommunicationService.update_interview(
        db=db, user_id=current_user.id, interview_id=interview_id, payload=payload
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@router.delete("/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
@interviews_router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an interview session."""
    deleted = await CommunicationService.delete_interview(
        db=db, user_id=current_user.id, interview_id=interview_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Interview not found")


@router.post("/interviews/prep-brief", response_model=InterviewPrepBriefResponse, status_code=status.HTTP_201_CREATED)
@interviews_router.post("/prep-brief", response_model=InterviewPrepBriefResponse, status_code=status.HTTP_201_CREATED)
async def generate_interview_prep_brief(
    payload: InterviewPrepBriefGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate tailored AI technical & behavioral prep briefing with STAR stories."""
    return await CommunicationService.generate_prep_brief(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get("/interviews/{interview_id}/prep-brief", response_model=InterviewPrepBriefResponse)
@interviews_router.get("/{interview_id}/prep-brief", response_model=InterviewPrepBriefResponse)
async def get_interview_prep_brief(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get existing prep brief for an interview session."""
    brief = await CommunicationService.get_prep_brief(
        db=db, user_id=current_user.id, interview_id=interview_id
    )
    if not brief:
        raise HTTPException(status_code=404, detail="Interview prep brief not found")
    return brief


# ==========================================
# 4. Follow-Up & Ghosting Alerts
# ==========================================

@router.get("/follow-ups", response_model=List[FollowUpRecommendation])
async def get_follow_up_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active follow-up recommendations and ghosting detection warnings."""
    return await CommunicationService.get_follow_up_recommendations(
        db=db, user_id=current_user.id
    )
