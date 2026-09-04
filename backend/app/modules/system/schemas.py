from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.shared.constants import PlatformCapability, ConnectorStatus, AuthorizationType

class PublicHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    ai_provider: str
    compliance_mode: str

class ReadinessResponse(BaseModel):
    status: str
    database: str
    queue: str
    connectors: str
    timestamp: datetime

class DetailedHealthResponse(BaseModel):
    status: str
    environment: str
    database: Dict[str, Any]
    queue: Dict[str, Any]
    workers: Dict[str, Any]
    connectors: List[Dict[str, Any]]
    ai_provider: Dict[str, Any]
    timestamp: datetime

class AuditEventResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    actor: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True

class WorkerMetricsResponse(BaseModel):
    active_workers_count: int
    total_workers: List[Dict[str, Any]]
    queue_depth: Dict[str, int]
    dead_letter_count: int
    recovery_events_count: int

class ConnectorInfoResponse(BaseModel):
    slug: str
    name: str
    supported_capabilities: List[str]
    status: str
    authorization_type: str
    api_version: str
    terms_reference: str
    rate_limit_policy: str
    is_auto_apply_supported: bool
    is_external_application_required: bool
    notes: str
