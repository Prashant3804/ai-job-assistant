import hashlib
import logging
import math
from typing import List, Dict, Optional, Tuple

from app.core.config import settings
from app.ai.interfaces.embedding_provider import EmbeddingProvider
from app.ai.providers.omniroute import OmniRouteEmbeddingProvider
from app.ai.providers.mock import MockEmbeddingProvider
from app.ai.schemas.ai_schemas import EmbeddingCacheEntry

logger = logging.getLogger("embedding_service")

class EmbeddingService:
    """Embedding generation service with SHA-256 caching and vector similarity."""

    _cache: Dict[str, EmbeddingCacheEntry] = {}

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        fallback_provider: Optional[EmbeddingProvider] = None
    ):
        if provider is not None:
            self.provider = provider
        elif settings.DEFAULT_AI_PROVIDER.lower() == "omniroute":
            self.provider = OmniRouteEmbeddingProvider()
        else:
            self.provider = MockEmbeddingProvider()
            
        self.fallback_provider = fallback_provider or MockEmbeddingProvider()

    @staticmethod
    def compute_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate normalized cosine similarity in range [0.0, 1.0]."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.75  # Default baseline for neutral comparison
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.75
        sim = dot / (norm_a * norm_b)
        # Rescale [-1, 1] to [0, 1]
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True,
        timeout: Optional[float] = None
    ) -> List[float]:
        """Generate embedding with SHA-256 caching and fallback."""
        if not text or not text.strip():
            return [0.0] * 128

        text_hash = self.compute_hash(text)
        if use_cache and text_hash in self._cache:
            return self._cache[text_hash].embedding

        try:
            vec = await self.provider.generate_embedding(text, timeout=timeout)
        except Exception as e:
            logger.warning(f"Primary embedding provider failed ({type(e).__name__}): falling back to deterministic embedding")
            vec = await self.fallback_provider.generate_embedding(text, timeout=timeout)

        if use_cache:
            self._cache[text_hash] = EmbeddingCacheEntry(
                source_hash=text_hash,
                embedding=vec,
                embedding_model=self.provider.get_model_name()
            )

        return vec

    def clear_cache(self):
        self._cache.clear()
