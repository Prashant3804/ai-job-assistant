from enum import Enum
from typing import Dict
from app.core.config import settings

class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    LIKELY_ELIGIBLE = "LIKELY_ELIGIBLE"
    REVIEW = "REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class RecommendationStatus(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"

SCORING_VERSION = "v4.0.0"

# Default scoring weights (sum must equal 100.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "skills": settings.MATCH_SKILLS_WEIGHT,        # 35.0
    "experience": settings.MATCH_EXPERIENCE_WEIGHT,# 20.0
    "education": settings.MATCH_EDUCATION_WEIGHT,  # 15.0
    "location": settings.MATCH_LOCATION_WEIGHT,    # 10.0
    "role": settings.MATCH_ROLE_WEIGHT,            # 10.0
    "salary": settings.MATCH_SALARY_WEIGHT,        # 10.0
}

# Recommendation score thresholds
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "strong": settings.MATCH_STRONG_THRESHOLD,     # >= 90.0
    "good": settings.MATCH_GOOD_THRESHOLD,         # >= 80.0
    "possible": settings.MATCH_POSSIBLE_THRESHOLD, # >= 70.0
    "weak": settings.MATCH_WEAK_THRESHOLD,         # >= 60.0
}

# Skill canonical aliases dictionary
SKILL_ALIASES: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "postgres": "postgresql",
    "pgsql": "postgresql",
    "py": "python",
    "py3": "python",
    "golang": "go",
    "k8s": "kubernetes",
    "docker": "docker",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "mongo": "mongodb",
    "nextjs": "next.js",
    "next": "next.js",
    "fastapi": "fastapi",
    "tailwind": "tailwindcss",
    "graphql": "graphql",
    "rest": "rest api",
    "restful": "rest api",
    "ai/ml": "machine learning",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ci/cd": "cicd",
    "ci-cd": "cicd",
}
