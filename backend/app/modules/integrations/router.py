from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.modules.integrations.service import ConnectorComplianceService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/integrations", tags=["Connectors & Integration Safety"])

@router.get("/connectors")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    service = ConnectorComplianceService(db)
    connectors = await service.get_all_connectors()
    return APIResponse(message="Connectors retrieved", data=connectors)
