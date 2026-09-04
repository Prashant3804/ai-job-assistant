import uuid
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.job import JobSource
from app.shared.constants import ConnectorCapabilityStatus
from app.core.exceptions import UnauthorizedIntegrationError

class ConnectorComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_connectors(self) -> List[Dict[str, Any]]:
        stmt = select(JobSource)
        res = await self.db.execute(stmt)
        sources = res.scalars().all()
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "slug": s.slug,
                "capability_status": s.capability_status,
                "is_active": s.is_active,
                "compliance_notes": self._get_compliance_notes(s.capability_status),
                "base_url": s.base_url
            }
            for s in sources
        ]

    def _get_compliance_notes(self, status: str) -> str:
        if status == ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value:
            return "Authorized Direct API integration active. Automated submission permitted."
        elif status == ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value:
            return "Official job feeds & API discovery enabled. Direct applications must be submitted via authorized candidate link."
        elif status == ConnectorCapabilityStatus.EXTERNAL_APPLICATION_REQUIRED.value:
            return "Requires manual candidate submission on employer portal. No automated bots permitted."
        else:
            return "Unsupported integration."

    async def validate_application_submission_safety(self, job_source_id: uuid.UUID) -> bool:
        stmt = select(JobSource).where(JobSource.id == job_source_id)
        res = await self.db.execute(stmt)
        source = res.scalar_one_or_none()
        if not source:
            raise UnauthorizedIntegrationError("Job source not found or unregistered.")

        if source.capability_status != ConnectorCapabilityStatus.SUPPORTED_AUTO_APPLY.value:
            raise UnauthorizedIntegrationError(
                f"Automation violation: Source '{source.name}' has capability status '{source.capability_status}'. "
                "Automated application submission is restricted to prevent anti-bot and Terms of Service violations."
            )
        return True
