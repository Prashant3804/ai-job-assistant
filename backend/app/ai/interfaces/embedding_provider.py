from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @abstractmethod
    async def generate_embedding(self, text: str, timeout: Optional[float] = None) -> List[float]:
        """Generate vector embedding for the provided input text."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the active embedding model."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check embedding provider health status safely."""
        pass
