from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.modules.connectors.registry import connector_registry

class ConnectorHealthStatus:
    def __init__(self, slug: str, name: str):
        self.slug = slug
        self.name = name
        self.status = "HEALTHY"
        self.latency_ms = 45.0
        self.success_count = 100
        self.failure_count = 0
        self.rate_limit_events = 0
        self.last_success_at: Optional[datetime] = datetime.now(timezone.utc)
        self.last_failure_at: Optional[datetime] = None
        self.last_error_message: Optional[str] = None

    @property
    def error_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return round((self.failure_count / total) * 100.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "error_rate_percent": self.error_rate,
            "rate_limit_events": self.rate_limit_events,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "last_error_message": self.last_error_message
        }

class ConnectorHealthService:
    """Monitors connectivity, latency, and error rates for all registered platform connectors."""

    def __init__(self):
        self._health_map: Dict[str, ConnectorHealthStatus] = {}
        self._initialize()

    def _initialize(self):
        for conn in connector_registry.list_connectors():
            self._health_map[conn.slug.lower()] = ConnectorHealthStatus(conn.slug, conn.name)

    def record_success(self, slug: str, latency_ms: float = 40.0):
        key = slug.lower()
        if key not in self._health_map:
            self._health_map[key] = ConnectorHealthStatus(slug, slug.title())
        item = self._health_map[key]
        item.success_count += 1
        item.latency_ms = (item.latency_ms * 0.8) + (latency_ms * 0.2)
        item.last_success_at = datetime.now(timezone.utc)
        if item.error_rate < 5.0 and item.status != "AUTH_REQUIRED":
            item.status = "HEALTHY"

    def record_failure(self, slug: str, error_code: str, error_message: str):
        key = slug.lower()
        if key not in self._health_map:
            self._health_map[key] = ConnectorHealthStatus(slug, slug.title())
        item = self._health_map[key]
        item.failure_count += 1
        item.last_failure_at = datetime.now(timezone.utc)
        item.last_error_message = error_message
        if "RATE_LIMIT" in error_code.upper():
            item.rate_limit_events += 1
            item.status = "RATE_LIMITED"
        elif "AUTH" in error_code.upper():
            item.status = "AUTH_REQUIRED"
        elif item.error_rate > 20.0:
            item.status = "DEGRADED"

    def get_connector_health(self, slug: str) -> Optional[Dict[str, Any]]:
        item = self._health_map.get(slug.lower())
        return item.to_dict() if item else None

    def get_all_health(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._health_map.values()]

# Global Singleton
connector_health_service = ConnectorHealthService()
