"""Live Job Discovery Subsystem for AI Job Assistant."""
from app.modules.jobs.discovery.base import BaseDiscoveryProvider
from app.modules.jobs.discovery.greenhouse import GreenhouseDiscoveryProvider
from app.modules.jobs.discovery.lever import LeverDiscoveryProvider
from app.modules.jobs.discovery.public_feeds import (
    RemotiveDiscoveryProvider,
    ArbeitnowDiscoveryProvider,
    JobicyDiscoveryProvider
)
from app.modules.jobs.discovery.aggregators import (
    JSearchAggregatorProvider,
    SerpApiAggregatorProvider
)
from app.modules.jobs.discovery.orchestrator import (
    JobDiscoveryOrchestrator,
    get_discovery_orchestrator
)

__all__ = [
    "BaseDiscoveryProvider",
    "GreenhouseDiscoveryProvider",
    "LeverDiscoveryProvider",
    "RemotiveDiscoveryProvider",
    "ArbeitnowDiscoveryProvider",
    "JobicyDiscoveryProvider",
    "JSearchAggregatorProvider",
    "SerpApiAggregatorProvider",
    "JobDiscoveryOrchestrator",
    "get_discovery_orchestrator",
]
