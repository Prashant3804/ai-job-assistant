import logging
from typing import Optional, List, Tuple
from app.ai.services.embedding_service import EmbeddingService
from app.modules.matching.schemas import DimensionScore

logger = logging.getLogger("semantic_matcher")

class SemanticMatcher:
    """Semantic vector similarity matcher powered by OmniRoute embeddings."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()

    async def match(
        self,
        candidate_summary_text: str,
        job_description_text: str,
        job_embedding: Optional[List[float]] = None
    ) -> Tuple[float, Optional[str], float]:
        """
        Calculates semantic similarity between candidate profile and job description.
        Returns: (semantic_score_0_to_100, embedding_model_name, confidence)
        """
        if not candidate_summary_text or not job_description_text:
            return 75.0, None, 0.85

        try:
            cand_vec = await self.embedding_service.generate_embedding(candidate_summary_text)
            if not job_embedding:
                job_vec = await self.embedding_service.generate_embedding(job_description_text)
            else:
                job_vec = job_embedding

            sim = self.embedding_service.cosine_similarity(cand_vec, job_vec)
            score = round(sim * 100.0, 1)
            model_name = self.embedding_service.provider.get_model_name()
            return score, model_name, 1.0
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}. Using neutral fallback.")
            return 75.0, None, 0.70
