from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.modules.analytics.service import AnalyticsService
from app.shared.schemas import DashboardAnalytics

router = APIRouter(prefix="/analytics", tags=["Dashboard & Analytics"])

@router.get("/dashboard", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyticsService(db)
    return await service.get_dashboard_data(current_user)
