from typing import Dict, Optional
from app.modules.matching.constants import (
    DEFAULT_WEIGHTS,
    DEFAULT_THRESHOLDS,
    RecommendationStatus,
)
from app.modules.matching.schemas import DimensionScore

class WeightedScoringCalculator:
    """Calculates deterministic weighted score and maps to recommendation tiers."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        self.validate_weights()

    def validate_weights(self):
        total = sum(self.weights.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Matching weights must sum exactly to 100.0 (current sum: {total})")

    def calculate_overall_score(self, dimensions: Dict[str, DimensionScore]) -> float:
        overall = sum(dim.contribution for dim in dimensions.values())
        return round(max(0.0, min(100.0, overall)), 1)

    def determine_recommendation(self, overall_score: float) -> RecommendationStatus:
        if overall_score >= self.thresholds.get("strong", 90.0):
            return RecommendationStatus.STRONG_MATCH
        elif overall_score >= self.thresholds.get("good", 80.0):
            return RecommendationStatus.GOOD_MATCH
        elif overall_score >= self.thresholds.get("possible", 70.0):
            return RecommendationStatus.POSSIBLE_MATCH
        elif overall_score >= self.thresholds.get("weak", 60.0):
            return RecommendationStatus.WEAK_MATCH
        else:
            return RecommendationStatus.NOT_RECOMMENDED
